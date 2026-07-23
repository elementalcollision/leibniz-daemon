"""Lean REPL backend (ADR 0011) — import-caching for throughput.

A long-lived leanprover-community/repl process (in the container) keeps Mathlib
imports loaded across checks: an import-set is sent ONCE to create a REPL
*environment*, and every later check reuses that env instead of reloading Mathlib —
eliminating the ~1s-per-check Mathlib reload of the CLI backend.

Implements the `LeanBackend` Protocol (`compile_statement`, `check_proof`,
`closed_by_decision_procedure`). The REPL is a single stdin/stdout stream, so its
I/O is serialized under a lock; the consensus ensemble still runs its (slow) LLM
proposals concurrently — only the (now fast) kernel checks serialize. If the REPL
process is unavailable it degrades to conservative results (False/None), and the
assembly falls back to the CLI backend. It does NOT write kernel_verified —
`LeanVerifier.discharge` remains the sole writer.
"""
from __future__ import annotations

import atexit
import json
import subprocess
import threading
import weakref
from dataclasses import dataclass, field
from typing import Optional

from leibniz.propositio import Expressio

REPL_IMAGE = "leibniz-lean-repl:v4.31.0"
# Kept in sync with lean_cli.DEFAULT_TRIVIAL_TACTICS (ADR 0025 added ring/nlinarith so
# ring-decidable polynomial identities are quarantined as TRIVIAL, not promulgated).
DEFAULT_TRIVIAL_TACTICS = ("decide", "simp", "omega", "trivial", "aesop", "ring", "nlinarith")


def _join_proof(theorem_src: str, proof_src: str, preamble: str = "") -> str:
    head = theorem_src.rstrip()
    cut = head.find(":=")
    if cut != -1:
        head = head[:cut].rstrip()
    proof = proof_src.strip()
    body = f"{head} := {proof}" if proof else f"{head} := by sorry"
    # ADR 0062: prepend operator-authored top-level declarations (defs/set_options) so a legible
    # multi-definition theorem discharges as ONE source. Empty for the discovery path (byte-identical).
    return f"{preamble.rstrip()}\n{body}" if preamble.strip() else body


# Live backends that have actually started a container (weakrefs — the registry must never keep a
# backend alive). The daemon builds one backend per decision procedure and tears none of them down;
# their containers hold THIS process's stdin pipes, so they cannot exit until the process does. A
# batch runner (the heartbeat) calls `close_all()` when its cycles are done — the 2026-07-23 soak
# showed the post-beat container count growing with the procedure count (1→2→3), every one a
# false leak alarm that self-resolved at process exit.
_LIVE: list = []


def close_all() -> int:
    """Close every live REPL backend in this process (terminating their containers). Idempotent —
    `close()` is a no-op on an already-closed backend. Returns the number actually closed."""
    n = 0
    for ref in _LIVE:
        be = ref()
        if be is not None and be._proc is not None:
            be.close()
            n += 1
    _LIVE.clear()
    return n


@dataclass
class LeanReplBackend:
    image: str = REPL_IMAGE
    timeout_s: int = 180
    trivial_tactics: tuple[str, ...] = DEFAULT_TRIVIAL_TACTICS
    _proc: Optional[subprocess.Popen] = field(default=None, repr=False)
    _envs: dict[tuple, int] = field(default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # --- process + protocol ---------------------------------------------------
    def _start(self) -> Optional[subprocess.Popen]:
        if self._proc is not None:
            return self._proc
        try:
            self._proc = subprocess.Popen(
                ["docker", "run", "-i", "--rm", self.image],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, bufsize=1,
            )
            atexit.register(self.close)
            _LIVE.append(weakref.ref(self))          # registry for close_all (batch teardown)
        except FileNotFoundError:
            self._proc = None
        return self._proc

    def _send(self, payload: dict) -> Optional[dict]:
        proc = self._start()
        if proc is None or proc.stdin is None or proc.stdout is None:
            return None
        # Bound the exchange by `timeout_s`. A blocking `readline()` on a wedged REPL would
        # otherwise hold `self._lock` forever and stall the WHOLE ensemble/run (no per-check
        # timeout existed before). We run the write+read in a worker so the caller can give up:
        # SIGALRM is unusable here (checks run in ThreadPoolExecutor worker threads, not main).
        holder: dict = {}

        def _exchange() -> None:
            try:
                proc.stdin.write(json.dumps(payload) + "\n\n")
                proc.stdin.flush()
                buf = ""
                while True:
                    line = proc.stdout.readline()
                    if line == "":  # process died
                        holder["resp"] = None
                        return
                    buf += line
                    if buf.strip():
                        try:
                            holder["resp"] = json.loads(buf.strip())
                            return
                        except json.JSONDecodeError:
                            continue
            except (BrokenPipeError, OSError):
                holder["resp"] = None

        worker = threading.Thread(target=_exchange, daemon=True)
        worker.start()
        worker.join(self.timeout_s)
        if worker.is_alive():
            # The REPL did not answer within timeout_s. Tear it down so the blocked read
            # unblocks (and the wedge cannot persist), then report None. This is conservative:
            # a timed-out check is NEVER kernel_verified (discharge re-checks; it can only
            # false-REJECT a pathological hang, never false-ACCEPT). close() drops the env
            # cache so the next call rebuilds it against a fresh process.
            self.close()
            return None
        return holder.get("resp")

    # Must compile in ANY healthy env: core-prelude only, ASCII only (a broken env has
    # no notation, so a unicode canary would conflate "broken" with "missing notation").
    _ENV_CANARY = "example : (1 : Nat) = 1 := rfl"

    def _env_for(self, key: tuple) -> Optional[int]:
        """REPL env id with `key` imports preloaded (cached). None if they error.

        The repl SWALLOWS some failed imports (e.g. a module whose .olean is absent,
        like an image without the umbrella Mathlib.olean): it answers {"env": N} with
        no error messages, but the env is coreless — every later check in it dies with
        "Unknown constant" noise. Probe each new env with a canary before caching; a
        failed canary means the env is broken -> None (fail-closed), never cached."""
        if key in self._envs:
            return self._envs[key]
        resp = self._send({"cmd": "\n".join(f"import {m}" for m in key)})
        if resp is None or "env" not in resp:
            return None
        if any(m.get("severity") == "error" for m in resp.get("messages", []) or []):
            return None
        env = resp["env"]
        # The canary elaborates in a throwaway child env; `env` itself is untouched.
        probe = self._send({"cmd": self._ENV_CANARY, "env": env})
        if probe is None or any(
            m.get("severity") == "error" for m in probe.get("messages", []) or []
        ):
            return None
        self._envs[key] = env
        return env

    def _run(self, decl: str, imports) -> Optional[dict]:
        key = tuple(imports or ())
        with self._lock:
            if key:
                env = self._env_for(key)
                if env is None:
                    return None
                return self._send({"cmd": decl, "env": env})
            return self._send({"cmd": decl})

    @staticmethod
    def _kernel_ok(resp: Optional[dict]) -> bool:
        if resp is None:
            return False
        msgs = resp.get("messages", []) or []
        has_error = any(m.get("severity") == "error" for m in msgs)
        has_sorry = any("sorry" in (m.get("data", "") or "") for m in msgs)
        return (not has_error) and (not has_sorry)

    # --- LeanBackend Protocol -------------------------------------------------
    def compile_statement(self, expr: Expressio) -> bool:
        resp = self._run(_join_proof(expr.theorem_src, "by sorry", expr.preamble), expr.imports)
        if resp is None:
            return False
        return not any(m.get("severity") == "error" for m in resp.get("messages", []) or [])

    def check_proof(self, expr: Expressio, proof_src: str) -> bool:
        return self._kernel_ok(self._run(_join_proof(expr.theorem_src, proof_src, expr.preamble), expr.imports))

    def check_proof_with_error(self, expr: Expressio, proof_src: str):
        """Like check_proof, but also surface the kernel diagnostics (ADR 0029).

        Returns (ok, error_text). This is an OPTIONAL backend method used only by the
        agentic repair loop to feed the kernel's complaint back to the reasoner; it does
        NOT write kernel_verified — that stays solely with LeanVerifier.discharge, which
        re-checks any candidate this surfaces as ok before stamping it."""
        resp = self._run(_join_proof(expr.theorem_src, proof_src, expr.preamble), expr.imports)
        if resp is None:
            return (False, "lean backend unavailable")
        msgs = resp.get("messages", []) or []
        errors = [str(m.get("data", "") or "") for m in msgs if m.get("severity") == "error"]
        sorry = [str(m.get("data", "") or "") for m in msgs if "sorry" in (m.get("data", "") or "")]
        ok = (not errors) and (not sorry)
        return (ok, "\n".join(errors) or ("proof still contains `sorry`" if sorry else ""))

    def closed_by_decision_procedure(self, expr: Expressio) -> bool:
        for tac in self.trivial_tactics:
            if self._kernel_ok(self._run(_join_proof(expr.theorem_src, f"by {tac}", expr.preamble), expr.imports)):
                return True
        return False

    # --- lifecycle ------------------------------------------------------------
    def close(self) -> None:
        if self._proc is not None:
            try:
                # EOF first: the REPL runs as container PID 1, which IGNORES the proxied SIGTERM
                # (kernel default for PID 1) — observed 2026-07-23: terminate() alone left the
                # container running until this Python process exited and its pipe fd closed.
                # Closing OUR write end delivers EOF; the REPL exits on its own; `--rm` reaps.
                if self._proc.stdin is not None:
                    self._proc.stdin.close()
            except Exception:
                pass
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None
        # Cached REPL env ids belong to the (now dead) process; a restarted REPL has fresh
        # ids, so a stale cache would make every import-keyed check target a non-existent env.
        self._envs.clear()

    def __enter__(self) -> "LeanReplBackend":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def available(image: str = REPL_IMAGE) -> bool:
    try:
        return subprocess.run(
            ["docker", "image", "inspect", image], capture_output=True, timeout=30
        ).returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

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
from dataclasses import dataclass, field
from typing import Optional

from leibniz.propositio import Expressio

REPL_IMAGE = "leibniz-lean-repl:v4.31.0"
DEFAULT_TRIVIAL_TACTICS = ("decide", "simp", "omega", "trivial", "aesop")


def _join_proof(theorem_src: str, proof_src: str) -> str:
    head = theorem_src.rstrip()
    cut = head.find(":=")
    if cut != -1:
        head = head[:cut].rstrip()
    proof = proof_src.strip()
    return f"{head} := {proof}" if proof else f"{head} := by sorry"


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
        except FileNotFoundError:
            self._proc = None
        return self._proc

    def _send(self, payload: dict) -> Optional[dict]:
        proc = self._start()
        if proc is None or proc.stdin is None or proc.stdout is None:
            return None
        try:
            proc.stdin.write(json.dumps(payload) + "\n\n")
            proc.stdin.flush()
            buf = ""
            while True:
                line = proc.stdout.readline()
                if line == "":  # process died
                    return None
                buf += line
                if buf.strip():
                    try:
                        return json.loads(buf.strip())
                    except json.JSONDecodeError:
                        continue
        except (BrokenPipeError, OSError):
            return None

    def _env_for(self, key: tuple) -> Optional[int]:
        """REPL env id with `key` imports preloaded (cached). None if they error."""
        if key in self._envs:
            return self._envs[key]
        resp = self._send({"cmd": "\n".join(f"import {m}" for m in key)})
        if resp is None or "env" not in resp:
            return None
        if any(m.get("severity") == "error" for m in resp.get("messages", []) or []):
            return None
        self._envs[key] = resp["env"]
        return resp["env"]

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
        resp = self._run(_join_proof(expr.theorem_src, "by sorry"), expr.imports)
        if resp is None:
            return False
        return not any(m.get("severity") == "error" for m in resp.get("messages", []) or [])

    def check_proof(self, expr: Expressio, proof_src: str) -> bool:
        return self._kernel_ok(self._run(_join_proof(expr.theorem_src, proof_src), expr.imports))

    def closed_by_decision_procedure(self, expr: Expressio) -> bool:
        for tac in self.trivial_tactics:
            if self._kernel_ok(self._run(_join_proof(expr.theorem_src, f"by {tac}"), expr.imports)):
                return True
        return False

    # --- lifecycle ------------------------------------------------------------
    def close(self) -> None:
        if self._proc is not None:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None

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

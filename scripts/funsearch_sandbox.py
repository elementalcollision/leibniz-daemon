"""Untrusted-code sandbox + LLM-free evaluator for the FunSearch CWC pilot.

SECURITY-CRITICAL — this is the isolation boundary that must exist BEFORE any LLM-generated program is
ever executed (docs/funsearch-decision-package.md §5/§6). A FunSearch loop runs UNTRUSTED construction
programs; this module executes each candidate inside a locked-down, ephemeral Docker container and
returns only its claimed output (a constant-weight code) parsed from stdout.

Isolation (the container IS the sandbox; the host NEVER execs the untrusted program in-process):
  --network none        no network at all
  --read-only           read-only root filesystem
  --tmpfs /tmp          the only writable space, size-capped, in RAM
  --memory / --cpus     bounded RAM + CPU
  --pids-limit          bounded process count (fork-bomb guard)
  --cap-drop ALL        no Linux capabilities
  --security-opt no-new-privileges
  --user 65534:65534    runs as `nobody` (host kernel + runc are the trust anchor; no userns-remap)
  + a HOST wall-clock deadline with a BOUNDED stdout read (host cannot be OOM-flooded), container
    force-removed on timeout/overflow. (An in-container SIGALRM is set too, but it is best-effort
    convenience, NOT a security control — the untrusted program shares that interpreter and can disarm
    it, and a C-extension busy loop never returns to a bytecode boundary. The host deadline + --cpus +
    the bounded read are the real backstops.)

Contract for an untrusted program: define `construct(n, d, w)` returning an iterable of weight-w
codewords (each an iterable of distinct ints in [0,n)). It may do anything inside the container; it
cannot reach the network, the host filesystem, or persist anything.

TRUST POSTURE: the sandbox output is UNTRUSTED DATA. Nothing downstream trusts it without re-checking —
`evaluate_program` re-validates with `verify_cwc` (untrusted fitness), and a genuine record beat is
decided only by the Lean kernel (`scripts/cwc_check.py`) + the automated oracle, never here. This module
contains NO LLM and NO GPU and authorizes NO spend; the LLM proposer + evolutionary loop (the billable
part) remain GATED on an explicit operator GO.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cwc_table_oracle as ora  # noqa: E402
from probe_beta_cwc_pilot import verify_cwc  # noqa: E402

# Base image pinned by DIGEST (supply-chain: the trusted in-container harness runs in this image, so a
# moving tag could change its runtime). Refresh: `docker pull python:3.12-slim` then
# `docker image inspect python:3.12-slim --format '{{index .RepoDigests 0}}'`.
DEFAULT_IMAGE = "python@sha256:ec948fa5f90f4f8907e89f4800cfd2d2e91e391a4bce4a6afa77ba265bc3a2fe"
RESULT_SENTINEL = "LEIBNIZ_CWC_RESULT:"
ERROR_SENTINEL = "LEIBNIZ_CWC_ERROR:"
MAX_CODEWORDS = 200_000          # in-container cap on the codeword list (after construct returns)
MAX_OUTPUT_BYTES = 8 * 1024 * 1024   # HOST-side cap on captured output (the real flood guard; the
#                                      legitimate 200k-codeword result line is well under this)

# Trusted harness, run as `python3 -I -c <HARNESS>` INSIDE the container. The untrusted program arrives
# as DATA on stdin (never as argv), is exec'd in a fresh namespace, and its `construct` output is
# serialized behind a sentinel. ALARM is the in-container wall-clock backstop.
_HARNESS_TEMPLATE = (
    "import sys, json, signal\n"
    "def _t(s, f):\n"
    "    raise TimeoutError('construct exceeded time limit')\n"
    "signal.signal(signal.SIGALRM, _t)\n"
    "signal.alarm(ALARM)\n"
    "try:\n"
    "    p = json.load(sys.stdin)\n"
    "    ns = {}\n"
    "    exec(p['program'], ns)\n"
    "    fn = ns.get('construct')\n"
    "    if not callable(fn):\n"
    "        raise ValueError('program must define construct(n, d, w)')\n"
    "    raw = fn(int(p['n']), int(p['d']), int(p['w']))\n"
    "    code = [sorted(int(x) for x in cw) for cw in raw]\n"
    "    if len(code) > MAXCW:\n"
    "        raise ValueError('output too large')\n"
    "    print('" + RESULT_SENTINEL + "' + json.dumps(code))\n"
    "except Exception as e:\n"
    "    print('" + ERROR_SENTINEL + "' + json.dumps(str(e)[:500]))\n"
)


def _harness(alarm_s: int) -> str:
    return _HARNESS_TEMPLATE.replace("ALARM", str(max(1, alarm_s))).replace("MAXCW", str(MAX_CODEWORDS))


def _docker_argv(name: str, image: str, memory: str, cpus: str, pids: int) -> list[str]:
    """The locked-down `docker run` argv (pure, so the isolation flags are unit-testable). Note the
    deliberate ABSENCE of any `-v` host mount — the untrusted program gets no host filesystem."""
    return [
        "docker", "run", "--rm", "-i", "--name", name,
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=64m",   # explicit (don't rely on daemon defaults)
        "--memory", memory, "--memory-swap", memory,   # ==memory => no swap
        "--cpus", cpus,
        "--pids-limit", str(pids),
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--user", "65534:65534",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-w", "/tmp",
        image,
    ]


@dataclass
class SandboxResult:
    ok: bool
    code: Optional[list[list[int]]]
    error: str
    raw: str = ""


def _parse_output(stdout: str) -> SandboxResult:
    """Parse the harness output. Takes the LAST sentinel line (the harness prints its line after the
    untrusted program returns, so a program that prints a fake sentinel cannot displace it; and the
    result is re-checked downstream regardless)."""
    result_line = error_line = None
    for line in stdout.splitlines():
        if line.startswith(RESULT_SENTINEL):
            result_line = line[len(RESULT_SENTINEL):]
        elif line.startswith(ERROR_SENTINEL):
            error_line = line[len(ERROR_SENTINEL):]
    if result_line is not None:
        try:
            code = json.loads(result_line)
            if not isinstance(code, list):
                return SandboxResult(False, None, "result was not a list", stdout)
            return SandboxResult(True, [list(c) for c in code], "", stdout)
        except (json.JSONDecodeError, TypeError) as e:
            return SandboxResult(False, None, f"unparseable result: {e}", stdout)
    if error_line is not None:
        try:
            return SandboxResult(False, None, f"program error: {json.loads(error_line)}", stdout)
        except json.JSONDecodeError:
            return SandboxResult(False, None, "program error (unparseable)", stdout)
    return SandboxResult(False, None, "no result emitted (crash / killed / silent)", stdout)


def available(image: str = DEFAULT_IMAGE) -> bool:
    """True iff docker and the sandbox image are usable."""
    try:
        proc = subprocess.run(["docker", "image", "inspect", image],
                              capture_output=True, text=True, timeout=30)
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _reap(name: str) -> None:
    """Force-remove a container by name, with its OWN timeout so a wedged daemon (plausible under the
    memory pressure a hostile program induces) cannot hang the host. --rm makes this idempotent."""
    try:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=10)
    except Exception:
        pass


def _kill_and_reap(proc, name: str) -> None:
    try:
        proc.kill()
    except Exception:
        pass
    try:
        proc.wait(timeout=2)
    except Exception:
        pass
    _reap(name)


def run_program(program_src: str, n: int, d: int, w: int, *, image: str = DEFAULT_IMAGE,
                timeout_s: int = 20, memory: str = "512m", cpus: str = "1.0",
                pids: int = 128) -> SandboxResult:
    """Execute an UNTRUSTED construction program in the locked-down container and return its claimed
    CWC code. NEVER raises on program misbehavior — timeout, crash, OOM, network attempt, non-UTF-8
    output, or an stdout flood all return SandboxResult(ok=False, ...). Output is read with a HOST-side
    byte cap (MAX_OUTPUT_BYTES) so a program that prints in an infinite loop cannot OOM the host; the
    container is force-removed on every abnormal exit."""
    name = f"leibniz-fs-{uuid.uuid4().hex[:12]}"
    payload = json.dumps({"program": program_src, "n": n, "d": d, "w": w}).encode()
    argv = _docker_argv(name, image, memory, cpus, pids) + ["python3", "-I", "-c", _harness(timeout_s - 1)]

    bufs = {"out": bytearray(), "err": bytearray()}
    overflow = {"hit": False}

    def _pump(stream, key):
        b = bufs[key]
        try:
            for chunk in iter(lambda: stream.read(65536), b""):
                if len(b) < MAX_OUTPUT_BYTES:
                    b.extend(chunk[: MAX_OUTPUT_BYTES - len(b)])
                else:
                    overflow["hit"] = True
                    break
        except Exception:
            pass

    proc = None
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            proc.stdin.write(payload)
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        threads = [threading.Thread(target=_pump, args=(proc.stdout, "out"), daemon=True),
                   threading.Thread(target=_pump, args=(proc.stderr, "err"), daemon=True)]
        for t in threads:
            t.start()
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if overflow["hit"]:
                _kill_and_reap(proc, name)
                return SandboxResult(False, None, f"output exceeded {MAX_OUTPUT_BYTES} bytes", "")
            if proc.poll() is not None and not any(t.is_alive() for t in threads):
                break
            time.sleep(0.05)
        else:
            _kill_and_reap(proc, name)
            return SandboxResult(False, None, f"timeout after {timeout_s}s", "")
        text = (bytes(bufs["out"]) + b"\n" + bytes(bufs["err"])).decode("utf-8", errors="replace")
        return _parse_output(text)
    except FileNotFoundError:
        return SandboxResult(False, None, "docker unavailable", "")
    except Exception as e:                               # no untrusted-driven exception may escape
        return SandboxResult(False, None, f"sandbox failure: {type(e).__name__}: {e}", "")
    finally:
        if proc is not None and proc.poll() is None:     # only abnormal paths reach here still-alive
            _kill_and_reap(proc, name)


def evaluate_program(program_src: str, n: int, d: int, w: int, snap=None, **run_kw) -> dict:
    """LLM-free evaluator: run the untrusted program in the sandbox, re-validate its output with
    verify_cwc (UNTRUSTED fitness = valid code size; 0 if invalid), and look up the table-of-record.
    `beats_record` here is a CANDIDATE flag from the automated oracle — a real beat still requires the
    Lean kernel re-check (scripts/cwc_check.py) and the ADR 0040 carve-out before any promulgation."""
    res = run_program(program_src, n, d, w, **run_kw)
    out = {"sandbox_ok": res.ok, "sandbox_error": res.error, "valid": False, "fitness": 0,
           "size": 0, "beats_record": False, "best_known": None}
    if not res.ok or res.code is None:
        return out
    code_sets = [frozenset(c) for c in res.code]
    ok, reason = verify_cwc(code_sets, n, d, w)
    out["valid"] = ok
    out["verify_reason"] = reason
    if ok:
        out["size"] = len(res.code)
        out["fitness"] = len(res.code)               # untrusted fitness; invalid stays 0
        snap = snap if snap is not None else ora.load_snapshot()[0]
        out["best_known"] = ora.best_known(n, d, w, snap)
        out["beats_record"] = ora.is_improvement(n, d, w, len(res.code), snap)
    return out


def main() -> int:
    """Smoke: run a benign construction program (the Fano A(7,4,3) code) through the sandbox."""
    if not available():
        print("[funsearch-sandbox] docker/image unavailable; cannot smoke-test")
        return 0
    prog = ("def construct(n, d, w):\n"
            "    return [[0,1,2],[0,3,4],[0,5,6],[1,3,5],[1,4,6],[2,3,6],[2,4,5]]\n")
    r = evaluate_program(prog, 7, 4, 3)
    print(f"[funsearch-sandbox] Fano program -> valid={r['valid']} fitness={r['fitness']} "
          f"best_known={r['best_known']} beats={r['beats_record']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

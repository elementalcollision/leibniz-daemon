"""ADR 0011 robustness: the REPL backend must not hang forever on a wedged process.

`_send` previously did an unbounded `readline()`; a non-responsive REPL would hold the
backend lock indefinitely and stall the whole consensus ensemble. The watchdog-bounded read
gives up after `timeout_s`, tears the process down, and returns None (conservative — a
timed-out check is never kernel_verified). These use a FAKE proc (no Docker/Lean), so they
run in CI. Not a trust-edge change: discharge stays the sole kernel_verified writer, and
timeout -> None can only fail-toward-unproven, never false-accept.
"""
from __future__ import annotations

import threading
import time

from leibniz.backends.lean_repl import LeanReplBackend


class _Stdin:
    def write(self, *_a): pass
    def flush(self): pass


class _HangStdout:
    """readline() blocks until the proc is terminated (simulates a wedged REPL)."""
    def __init__(self):
        self._released = threading.Event()
    def readline(self):
        self._released.wait()      # block forever until terminate() releases it
        return ""                  # then EOF


class _LineStdout:
    def __init__(self, lines):
        self._lines = list(lines)
    def readline(self):
        return self._lines.pop(0) if self._lines else ""


class _FakeProc:
    def __init__(self, stdout):
        self.stdin = _Stdin()
        self.stdout = stdout
        self.terminated = False
    def terminate(self):
        self.terminated = True
        rel = getattr(self.stdout, "_released", None)
        if rel is not None:
            rel.set()              # a real dying process closes stdout -> readline returns ""


def test_hung_repl_times_out_instead_of_blocking_forever():
    b = LeanReplBackend(timeout_s=0.3)
    proc = _FakeProc(_HangStdout())
    b._proc = proc
    b._envs[("Mathlib.Tactic",)] = 7        # a stale cached env to prove it's dropped
    t0 = time.time()
    resp = b._send({"cmd": "by sorry"})
    dt = time.time() - t0
    assert resp is None                      # conservative: no answer -> None (never verified)
    assert dt < 5.0                          # did NOT hang (bounded by ~timeout_s)
    assert proc.terminated is True           # wedged process was torn down
    assert b._proc is None                   # and dropped
    assert b._envs == {}                     # stale env cache invalidated on teardown


def test_responsive_repl_unchanged_happy_path():
    b = LeanReplBackend(timeout_s=5)
    b._proc = _FakeProc(_LineStdout(['{"env": 0, "messages": []}\n']))
    resp = b._send({"cmd": "import Mathlib.Tactic"})
    assert resp == {"env": 0, "messages": []}


def test_dead_process_returns_none():
    b = LeanReplBackend(timeout_s=5)
    b._proc = _FakeProc(_LineStdout([]))     # immediate EOF (process died)
    assert b._send({"cmd": "x"}) is None


def test_close_clears_env_cache():
    b = LeanReplBackend()
    b._proc = _FakeProc(_LineStdout([]))
    b._envs[("Mathlib.Tactic",)] = 3
    b.close()
    assert b._proc is None and b._envs == {}

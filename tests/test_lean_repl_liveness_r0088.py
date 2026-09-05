"""ADR 0088 adversarial review — a dead REPL process must not be handed out forever.

`_send`'s TIMEOUT path tears the process down, but its EOF / BrokenPipe paths do not. Since
ADR 0088 a near-miss `decide` over a large `ZMod` can overflow the Lean kernel stack and abort
the process (exit 134); at the old MAX_LCM = 64 it could not. Without a liveness check in
`_start`, that corpse was returned on every later call, so every subsequent kernel check read
EOF, returned None and DEFERred — silently, for the life of the backend. Fail-closed, but an
entire unattended cycle of DEFERs with nothing in the journal to explain it.
"""
from __future__ import annotations

import subprocess

from leibniz.backends.lean_repl import LeanReplBackend


def _dead_proc() -> subprocess.Popen:
    p = subprocess.Popen(["sh", "-c", "exit 134"], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    p.wait()
    return p


def test_start_does_not_return_a_dead_process():
    be = LeanReplBackend(timeout_s=5)
    dead = _dead_proc()
    assert dead.poll() == 134
    be._proc = dead
    got = be._start()          # may be None when Docker is absent — either way, NOT the corpse
    assert got is not dead
    be.close()


def test_dead_process_is_dropped_and_env_cache_cleared():
    be = LeanReplBackend(timeout_s=5)
    dead = _dead_proc()
    be._proc = dead
    be._envs[("Mathlib",)] = 7          # ids belong to the dead process; must not survive
    be._start()
    assert be._envs == {}
    assert be._proc is not dead
    be.close()

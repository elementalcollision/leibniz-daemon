"""Bound the Lean-container lifetime across a test session.

`LeanReplBackend` spawns `docker run -i --rm <image>` and registers only an `atexit` close, so a
backend constructed in a test stays alive for the whole pytest PROCESS. There are 73 such
constructions in tests/, and nothing in the pytest path calls `close_all()` -- only
`scripts/heartbeat.py:164` does. A full run therefore accumulates containers against a 15.66 GiB
Docker VM until the heavy ones are OOM-killed.

That is the mechanism behind `test_ziegler_counterexample::test_live_kernel_legs` failing only
under suite contention while passing alone: measured idle, its slowest leg takes 53.2 s and its
container survives; under a loaded VM the container is killed and `_run` returns None, which the
test could not distinguish from a timeout.

Module-scoped rather than function-scoped on purpose: within a module a backend is legitimately
reused across tests (the Mathlib import is cached per env id, `lean_repl._env_for`), and closing
per test would respawn and re-import for every one of them. Per module bounds accumulation to one
module's worth while keeping that reuse.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True, scope="module")
def _close_lean_backends_after_each_module():
    yield
    try:
        from leibniz.backends import lean_repl
    except Exception:                      # backend not importable in this environment
        return
    try:
        lean_repl.close_all()
    except Exception:                      # teardown must never fail a green module
        pass

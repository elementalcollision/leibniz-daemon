"""ADR 0011 robustness: a silently-broken REPL env must be detected, not cached.

The leanprover-community repl SWALLOWS some failed imports: `import Mathlib` against
an image whose lake cache lacks the umbrella Mathlib.olean answers `{"env": 0}` with
NO error messages, yet the env is coreless — every later check in it fails with
"Unknown constant `OfNat`" noise. Before the canary probe, `_env_for` cached that
poisoned env and every Mathlib-defaulted check fail-closed for the process lifetime
with misleading diagnostics. Now each freshly created env must compile a core-prelude
canary (`example : (1 : Nat) = 1 := rfl`) before being cached; a failing canary yields
None (conservative, fail-closed) and nothing is cached.

These use a FAKE proc (no Docker/Lean), so they run in CI. Not a trust-edge change:
discharge stays the sole kernel_verified writer, and broken-env -> None can only
fail-toward-unproven, never false-accept. The live-image counterpart tests are in
test_lean_repl_r0011.py (docker-gated).
"""
from __future__ import annotations

import json

from leibniz.backends.lean_repl import LeanReplBackend
from leibniz.propositio import Expressio


class _RecordingStdin:
    def __init__(self):
        self.payloads = []

    def write(self, data):
        data = data.strip()
        if data:
            self.payloads.append(json.loads(data))

    def flush(self):
        pass


class _LineStdout:
    def __init__(self, lines):
        self._lines = list(lines)

    def readline(self):
        return self._lines.pop(0) if self._lines else ""


class _FakeProc:
    def __init__(self, responses):
        self.stdin = _RecordingStdin()
        self.stdout = _LineStdout([json.dumps(r) + "\n" for r in responses])

    def terminate(self):
        pass


def test_swallowed_import_failure_is_detected_and_not_cached():
    """The regression: import answered {"env": 0} with no errors, but the env is
    broken (the canary dies exactly as real checks did). Must be None + uncached."""
    b = LeanReplBackend(timeout_s=5)
    b._proc = _FakeProc([
        {"env": 0},  # repl swallowed the failed umbrella import
        {"messages": [{"severity": "error", "data": "Unknown constant `OfNat`"}], "env": 1},
    ])
    assert b._env_for(("Mathlib",)) is None
    assert b._envs == {}                     # the poisoned env was NOT cached


def test_broken_env_fails_closed_through_public_api():
    """compile_statement on a broken-env import set degrades to False (fail-closed),
    the same conservative path as an unavailable backend — never a poisoned cache."""
    b = LeanReplBackend(timeout_s=5)
    b._proc = _FakeProc([
        {"env": 0},
        {"messages": [{"severity": "error", "data": "Unknown constant `OfNat`"}], "env": 1},
    ])
    expr = Expressio(theorem_src="theorem t : 1 + 1 = 2", imports=("Mathlib",))
    assert b.compile_statement(expr) is False
    assert b._envs == {}


def test_healthy_env_passes_canary_and_is_cached_once():
    b = LeanReplBackend(timeout_s=5)
    b._proc = _FakeProc([
        {"env": 0},          # import ok
        {"env": 1},          # canary compiles cleanly (in a throwaway child env)
    ])
    assert b._env_for(("Mathlib.Tactic",)) == 0
    assert b._envs == {("Mathlib.Tactic",): 0}
    # cached: a second call answers from the cache without touching the repl
    assert b._env_for(("Mathlib.Tactic",)) == 0
    assert len(b._proc.stdin.payloads) == 2  # import + canary, nothing more


def test_canary_probes_the_env_the_import_created():
    b = LeanReplBackend(timeout_s=5)
    b._proc = _FakeProc([{"env": 7}, {"env": 8}])
    b._env_for(("Mathlib",))
    probe = b._proc.stdin.payloads[1]
    assert probe["env"] == 7                            # targets the new env...
    assert probe["cmd"] == LeanReplBackend._ENV_CANARY  # ...with the core-only canary


def test_dead_repl_during_canary_is_none_not_cached():
    b = LeanReplBackend(timeout_s=5)
    b._proc = _FakeProc([{"env": 0}])        # EOF before the canary answer
    assert b._env_for(("Mathlib",)) is None
    assert b._envs == {}

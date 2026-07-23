"""ADR 0011: the Lean REPL backend (import-caching for throughput).

These require the REPL container (leibniz-lean-repl:v4.31.0); they skip cleanly
where it is absent (e.g. CI), so the stdlib invariant tests stay the universal
gate. Build the image with:

    docker build -f docker/lean-repl.Dockerfile -t leibniz-lean-repl:v4.31.0 .

The REPL backend satisfies the same LeanBackend Protocol as the CLI backend and
must agree with the kernel on the same true/false/sorry verdicts — only faster,
because Mathlib loads once per import-set instead of once per check.
"""
from __future__ import annotations

import pytest

from leibniz.backends.lean_repl import LeanReplBackend, available
from leibniz.propositio import Demonstratio, Expressio
from leibniz.trust import PROOF_EDGE
from leibniz.types import TrustTier, Verdict
from leibniz.verifiers import LeanVerifier

pytestmark = [
    pytest.mark.lean,
    pytest.mark.skipif(
        not available(), reason="REPL container leibniz-lean-repl:v4.31.0 not available"
    ),
]


def test_true_theorem_is_kernel_verified():
    with LeanReplBackend() as backend:
        expr = Expressio(theorem_src="theorem t : 1 + 1 = 2", imports=())
        demo = Demonstratio(proof_obligation="t", proof_src="by decide")
        ev = LeanVerifier(backend).discharge(expr, demo)
        assert demo.kernel_verified is True
        assert demo.qed == "Q.E.D."
        assert ev.edge == PROOF_EDGE
        assert ev.tier is TrustTier.MECHANICAL
        assert ev.verdict is Verdict.PASS


def test_false_theorem_is_unproven():
    with LeanReplBackend() as backend:
        expr = Expressio(theorem_src="theorem f : 1 + 1 = 3", imports=())
        demo = Demonstratio(proof_obligation="f", proof_src="by decide")
        ev = LeanVerifier(backend).discharge(expr, demo)
        assert demo.kernel_verified is False
        assert demo.qed == "Q.E.I."
        assert ev.tier is TrustTier.MECHANICAL
        assert ev.verdict is Verdict.FAIL


def test_sorry_is_never_a_proof():
    """The axiom of `sorry` must not earn a Q.E.D. — the core soundness property."""
    with LeanReplBackend() as backend:
        expr = Expressio(theorem_src="theorem t : 1 + 1 = 2", imports=())
        demo = Demonstratio(proof_obligation="t", proof_src="by sorry")
        LeanVerifier(backend).discharge(expr, demo)
        assert demo.kernel_verified is False
        assert demo.qed == "Q.E.I."


def test_tautology_is_trivial():
    with LeanReplBackend() as backend:
        assert backend.closed_by_decision_procedure(
            Expressio(theorem_src="theorem taut : True", imports=())
        ) is True


def test_malformed_statement_does_not_compile():
    with LeanReplBackend() as backend:
        assert backend.compile_statement(
            Expressio(theorem_src="theorem bad : NoSuchIdent", imports=())
        ) is False


def test_mathlib_import_cached_across_checks():
    """The reason the REPL exists: import once, reuse the env. Two Mathlib checks
    on the same import-set must both verify, and the env is created exactly once."""
    with LeanReplBackend() as backend:
        imports = ("Mathlib.Tactic",)
        e1 = Expressio(theorem_src="theorem t (a b : Nat) : a + b = b + a", imports=imports)
        e2 = Expressio(theorem_src="theorem t (a b : Nat) : a * b = b * a", imports=imports)
        assert backend.check_proof(e1, "by ring") is True
        assert backend.check_proof(e2, "by ring") is True
        assert list(backend._envs.keys()) == [imports]  # imports loaded exactly once


def test_umbrella_mathlib_import_yields_working_env():
    """`import Mathlib` is the pipeline's DEFAULT import set (pipeline._parse_expressio),
    so it must produce a usable env. Regression: the image's lake cache used to ship
    per-module oleans but no umbrella Mathlib.olean; the repl swallowed the failed
    import and answered a coreless env with no error, so every Mathlib-defaulted
    check fail-closed for the process lifetime. The image now builds the umbrella
    (docker/lean.Dockerfile `lake build Mathlib`) and this must verify."""
    with LeanReplBackend() as backend:
        imports = ("Mathlib",)
        expr = Expressio(theorem_src="theorem u (a b : ℕ) : a + b = b + a", imports=imports)
        assert backend.check_proof(expr, "by ring") is True
        assert list(backend._envs.keys()) == [imports]  # healthy env cached for reuse


def test_swallowed_bad_import_fails_closed_and_is_not_cached():
    """The repl swallows imports of modules with no .olean (answers {"env": N}, no
    error). The canary probe in _env_for must catch that: the check degrades to
    False (fail-closed) and the broken env is never cached."""
    with LeanReplBackend() as backend:
        expr = Expressio(
            theorem_src="theorem t : 1 + 1 = 2",
            imports=("Leibniz.NoSuchModule123",),
        )
        assert backend.compile_statement(expr) is False
        assert backend._envs == {}


# === close_all — batch teardown (2026-07-23 soak fix); CI-safe, no container needed ================

def test_close_all_terminates_registered_backends(monkeypatch):
    from leibniz.backends import lean_repl

    class _StubProc:
        def __init__(self):
            self.terminated = False
            self.stdin = self.stdout = None

        def terminate(self):
            self.terminated = True

    monkeypatch.setattr(lean_repl, "_LIVE", [])            # isolate the registry for this test
    monkeypatch.setattr(lean_repl.subprocess, "Popen", lambda *a, **k: _StubProc())
    a, b = lean_repl.LeanReplBackend(), lean_repl.LeanReplBackend()
    pa, pb = a._start(), b._start()                        # spawn (stub) → registers both
    assert len(lean_repl._LIVE) == 2
    assert lean_repl.close_all() == 2                      # both closed, containers terminated
    assert pa.terminated and pb.terminated
    assert a._proc is None and b._proc is None and lean_repl._LIVE == []
    assert lean_repl.close_all() == 0                      # idempotent: nothing left to close
    c = lean_repl.LeanReplBackend()                        # a backend that never started a container
    assert c._proc is None and lean_repl.close_all() == 0  # is not counted (and not crashed on)

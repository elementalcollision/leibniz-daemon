"""R1 exit tests: the real Lean kernel behind LeanBackend.

These require the pinned Lean container (leibniz-lean:v4.31.0); they skip cleanly
where it is absent (e.g. CI), so the 11 stdlib invariant tests stay the universal
gate. Build the image with:

    docker build -f docker/lean.Dockerfile -t leibniz-lean:v4.31.0 .
"""
from __future__ import annotations

import pytest

from leibniz.backends.lean_cli import LeanCliBackend, available
from leibniz.propositio import Demonstratio, Expressio
from leibniz.trust import PROOF_EDGE
from leibniz.types import TrustTier, Verdict
from leibniz.verifiers import LeanVerifier

pytestmark = [
    pytest.mark.lean,
    pytest.mark.skipif(
        not available(), reason="Lean container leibniz-lean:v4.31.0 not available"
    ),
]


def _verifier() -> LeanVerifier:
    return LeanVerifier(LeanCliBackend())


def test_true_theorem_is_kernel_verified():
    expr = Expressio(theorem_src="theorem t : 1 + 1 = 2", imports=())
    demo = Demonstratio(proof_obligation="t", proof_src="by decide")
    ev = _verifier().discharge(expr, demo)
    assert demo.kernel_verified is True
    assert demo.qed == "Q.E.D."
    assert ev.edge == PROOF_EDGE
    assert ev.tier is TrustTier.MECHANICAL
    assert ev.verdict is Verdict.PASS


def test_false_theorem_is_unproven_with_a_mechanical_fail_edge():
    """The exit-test 'false -> UNPROVEN'. Assert it fails for the RIGHT reason:
    a present, MECHANICAL, FAIL proof edge (not a missing/absent edge)."""
    expr = Expressio(theorem_src="theorem f : 1 + 1 = 3", imports=())
    demo = Demonstratio(proof_obligation="f", proof_src="by decide")
    ev = _verifier().discharge(expr, demo)
    assert demo.kernel_verified is False
    assert demo.qed == "Q.E.I."
    assert ev.edge == PROOF_EDGE
    assert ev.tier is TrustTier.MECHANICAL
    assert ev.verdict is Verdict.FAIL


def test_sorry_is_never_a_proof():
    """The axiom of `sorry` must not earn a Q.E.D. — the core soundness property."""
    expr = Expressio(theorem_src="theorem t : 1 + 1 = 2", imports=())
    demo = Demonstratio(proof_obligation="t", proof_src="by sorry")
    _verifier().discharge(expr, demo)
    assert demo.kernel_verified is False
    assert demo.qed == "Q.E.I."


def test_tautology_is_trivial():
    backend = LeanCliBackend()
    assert backend.closed_by_decision_procedure(Expressio(theorem_src="theorem taut : True", imports=())) is True


def test_malformed_statement_does_not_compile():
    backend = LeanCliBackend()
    assert backend.compile_statement(Expressio(theorem_src="theorem bad : NoSuchIdent", imports=())) is False


def test_well_formed_statement_compiles():
    backend = LeanCliBackend()
    assert backend.compile_statement(Expressio(theorem_src="theorem ok : 1 + 1 = 2", imports=())) is True

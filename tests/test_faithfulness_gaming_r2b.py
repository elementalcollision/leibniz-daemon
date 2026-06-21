"""R2b: the faithfulness gate end-to-end over the real Z3 gaming-witness (ADR 0004).

The exit test for R2: a kernel-provable-but-vacuous specialization is caught GAMED
*before* proof. z3-gated; skips where the verify extra is absent.
"""
from __future__ import annotations

import pytest

from leibniz.backends.smt_z3 import Z3Backend, available
from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.probes import default_probes
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimType, FinishReason, TrustTier, Verdict
from leibniz.verifiers import SMTVerifier

pytestmark = [
    pytest.mark.z3,
    pytest.mark.skipif(not available(), reason="z3-solver (verify extra) not installed"),
]


def _gate() -> FaithfulnessGate:
    smt = SMTVerifier(Z3Backend())
    return FaithfulnessGate(smt=smt, probes=default_probes(smt), judge=None)


def _prop(claim_domain: str, claim_property: str, established_domain: str) -> Propositio:
    en = Enuntiatio(
        statement="a complexity bound",
        claim_type=ClaimType.COMPLEXITY_BOUND,
        falsifiable_claim="prose form, unused on the structured path",
        claim_domain=claim_domain,
        claim_property=claim_property,
    )
    expr = Expressio(theorem_src="theorem t : P", established_domain=established_domain)
    return Propositio(enuntiatio=en, expressio=expr)


def test_vacuous_specialization_is_caught_as_gamed_before_proof():
    # Enuntiatio: forall n>=0, 2n >= n+1  (FALSE at n=0).
    # The formal statement only established it for n>=1 (domain narrowed).
    prop = _prop(claim_domain="n >= 0", claim_property="2*n >= n + 1", established_domain="n >= 1")
    ev = _gate().check(prop)
    assert ev.tier is TrustTier.ADVERSARIAL
    assert ev.verdict is Verdict.FAIL
    assert prop.finish_reason is FinishReason.GAMED
    assert ev.detail.get("gaming_witness") == {"n": 0}


def test_faithful_statement_passes_via_the_mechanical_probe():
    # Claim domain == established domain (n>=1); property true there.
    prop = _prop(claim_domain="n >= 1", claim_property="2*n >= n + 1", established_domain="n >= 1")
    ev = _gate().check(prop)
    assert ev.tier is TrustTier.MECHANICAL
    assert ev.verdict is Verdict.PASS
    assert prop.finish_reason is None  # not quarantined


def test_coverage_gap_without_property_failure_defers():
    # Property holds everywhere (n>=0), but the proof only covered n>=5: there is a
    # coverage gap yet no concrete property-failure witness -> DEFER, never PASS.
    prop = _prop(claim_domain="n >= 0", claim_property="n >= 0", established_domain="n >= 5")
    ev = _gate().check(prop)
    assert ev.tier is TrustTier.MECHANICAL
    assert ev.verdict is Verdict.DEFER
    assert prop.finish_reason is None

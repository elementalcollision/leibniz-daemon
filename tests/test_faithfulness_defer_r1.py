"""Guard the faithfulness sequencing rule (ADR 0003) while the real kernel is online.

`_negate` is still a placeholder, so the adversarial gaming-witness passes
vacuously. The safety net is that a *measurable* claim with no decisive probe must
return DEFER (never PASS, never JUDGED) — so with the R1 daemon's empty probe
table, nothing can promulgate on a vacuous faithfulness check. This test pins that
behavior so a future edit cannot quietly launder an un-probed measurable claim
into a pass before R2 lands real probes + a real `_negate`.
"""
from __future__ import annotations

from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimType, TrustTier, Verdict


class _NoWitnessBackend:
    def find_gaming_witness(self, statement, negated_claim, bound):
        return None  # adversarial spine finds nothing (vacuous until R2's real _negate)


class _NoWitnessSMT:
    backend = _NoWitnessBackend()


def _gate() -> FaithfulnessGate:
    # Empty probe table = the real R1 configuration (probes are an R2 deliverable).
    return FaithfulnessGate(smt=_NoWitnessSMT(), probes={}, judge=None)


def _prop(claim_type: ClaimType) -> Propositio:
    en = Enuntiatio(
        statement="comparison sort lower bound",
        claim_type=claim_type,
        falsifiable_claim="exists comparison sort beating n log n",
    )
    return Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem t : P"))


def test_measurable_claim_without_probe_defers_never_judges():
    ev = _gate().check(_prop(ClaimType.COMPLEXITY_BOUND))
    assert ev.tier is TrustTier.MECHANICAL
    assert ev.verdict is Verdict.DEFER
    assert ev.tier is not TrustTier.JUDGED


def test_correctness_claim_without_probe_also_defers():
    ev = _gate().check(_prop(ClaimType.CORRECTNESS_OVER_DOMAIN))
    assert ev.verdict is Verdict.DEFER

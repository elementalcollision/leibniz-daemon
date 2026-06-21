"""Real claim-type probes (R2b) — the faithfulness gate's mechanical fast path.

A probe positively certifies that the formal statement establishes the claimed
property over the *full* claim domain. It asks the SMT backend for a coverage gap —
an input the Enuntiatio's ``claim_domain`` covers but the Expressio's
``established_domain`` does not:

    gap := claim_domain(n) ∧ ¬established_domain(n)

No gap  -> the statement covers the whole claim domain -> MECHANICAL PASS.
A gap   -> we cannot mechanically certify faithfulness -> None (DEFER); the gate
           refuses to launder it through a judge, and the adversarial gaming-witness
           remains responsible for any hard refutation (GAMED).

Probes never PASS on judgment, and never hard-FAIL on a merely-imperfect domain
read (that stays a DEFER). This module is outside the trust-guarded core: it only
*assembles* SMT queries; the tier/verdict are still decided in the gate.
"""
from __future__ import annotations

from typing import Optional

from leibniz.propositio import Propositio
from leibniz.types import ClaimType


def coverage_probe(smt, bound: int = 64):
    """Build a probe that PASSes iff established_domain covers claim_domain."""

    def probe(prop: Propositio) -> Optional[bool]:
        en = prop.enuntiatio
        expr = prop.expressio
        if not (en.claim_domain and expr is not None and expr.established_domain):
            return None  # no structured contract -> cannot certify mechanically
        gap = smt.backend.find_gaming_witness(
            statement=f"not ({expr.established_domain})",
            negated_claim=en.claim_domain,
            bound=bound,
        )
        return True if gap is None else None  # full coverage -> PASS; gap -> DEFER

    return probe


def default_probes(smt, bound: int = 64) -> dict[ClaimType, object]:
    """The probe table the daemon wires into the FaithfulnessGate. COMPLEXITY_BOUND
    and CORRECTNESS_OVER_DOMAIN share the domain-coverage probe; other measurable
    types DEFER until they get a dedicated probe (never laundered to a judge)."""
    probe = coverage_probe(smt, bound)
    return {
        ClaimType.COMPLEXITY_BOUND: probe,
        ClaimType.CORRECTNESS_OVER_DOMAIN: probe,
    }

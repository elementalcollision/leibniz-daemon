"""Real claim-type probes (R2b) — the faithfulness gate's mechanical fast path.

A probe positively certifies that the formal statement establishes the claimed
property over the *full* claim domain. It asks the SMT backend for two conclusive
results (ADR 0022 tightened the second so the property is genuinely tested):

    coverage := claim_domain(n) ∧ ¬established_domain(n)        is UNSAT  (no gap), and
    property := established_domain(n) ∧ claim_domain(n) ∧ ¬claim_property(n)  is UNSAT.

Both UNSAT -> the statement covers the whole claim domain AND the property holds
              everywhere it establishes it -> MECHANICAL PASS.
A gap, a falsified property, or an undecided/timed-out search -> None (DEFER); the
gate refuses to launder it through a judge, and the adversarial gaming-witness
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
        if not (en.claim_domain and en.claim_property and expr is not None and expr.established_domain):
            return None  # incomplete contract -> cannot certify mechanically -> DEFER
        be = smt.backend
        # A mechanical PASS must rest on a contract the SMT can ACTUALLY search and on
        # CONCLUSIVE results. If any part is un-encodable (richer than the DSL), DEFER —
        # the search would degrade to None, which read as "no gap" is a vacuous PASS
        # (ADR 0020). Requiring claim_property encodable too makes a PASS mean the gaming
        # check below genuinely ran.
        encodable = getattr(be, "encodable", None)
        if encodable is not None and not (
            encodable(en.claim_domain) and encodable(en.claim_property) and encodable(expr.established_domain)
        ):
            return None
        decide = getattr(be, "decide_unsat", None)
        if decide is not None:
            # Certify ONLY on conclusive UNSAT of BOTH (ADR 0021 soundness review; the
            # property check tightened in ADR 0022):
            #  (1) coverage — claim_domain ⊆ established_domain (no gap), and
            #  (2) property — claim_property actually holds everywhere the statement
            #      establishes it AND the claim covers: ¬UNSAT of
            #      established_domain ∧ claim_domain ∧ ¬claim_property.
            # NB: the old "no gaming" form ANDed ¬established_domain, which under (1) is
            # already empty — so it was vacuously UNSAT for ANY claim_property and never
            # tested the property (ADR 0022 review). Searching *inside* established_domain
            # makes the conjunction non-empty, so the property is genuinely checked.
            # A gap, a falsified property, OR an undecided/timed-out search (None) all
            # DEFER; a PASS never rests on a None that meant "could not check".
            covered = decide([f"({en.claim_domain})", f"not ({expr.established_domain})"], bound)
            if covered is not True:
                return None
            property_holds = decide(
                [f"({expr.established_domain})", f"({en.claim_domain})", f"not ({en.claim_property})"],
                bound,
            )
            return True if property_holds is True else None
        # Fallback for minimal backends (test doubles without decide_unsat): legacy gap check.
        gap = be.find_gaming_witness(
            statement=f"not ({expr.established_domain})",
            negated_claim=en.claim_domain,
            bound=bound,
        )
        return True if gap is None else None

    return probe


def default_probes(smt, bound: int = 64) -> dict[ClaimType, object]:
    """The probe table the daemon wires into the FaithfulnessGate (ADR 0010).

    Every "for all n in domain D, property P(n)" claim shares the domain-coverage
    probe — COMPLEXITY_BOUND, CORRECTNESS_OVER_DOMAIN, OPTIMALITY, INVARIANT. The
    probe PASSes iff the statement's established_domain covers the claim_domain
    (no gap), else DEFER. EXISTENCE and STRUCTURAL do not fit the ∀-over-domain
    shape and have no decisive arithmetic check, so they stay DEFER (never laundered
    to a judge) until a bespoke probe exists."""
    probe = coverage_probe(smt, bound)
    return {
        ClaimType.COMPLEXITY_BOUND: probe,
        ClaimType.CORRECTNESS_OVER_DOMAIN: probe,
        ClaimType.OPTIMALITY: probe,
        ClaimType.INVARIANT: probe,
    }

"""The faithfulness gate -- the one irreducible residual, handled carefully.

The Lean kernel guarantees proof <-> statement. Nothing guarantees
statement <-> Enuntiatio (the human-readable claim the public ledger is held
accountable to). That is the 3-body faithfulness problem, and it is the entire
risk surface of a system whose proofs are otherwise mechanical: a kernel-valid
proof of a *mis-stated* theorem is strictly worse than no proof, because it is
most authoritative exactly when it is most wrong, and the ledger makes it
permanent.

A naive gate -- "ask an LLM whether the statement matches the claim" -- is
theater: the judge shares the formalizer's blind spots and rubber-stamps. So the
gate tries, strongest first:

  1. ADVERSARIAL (gaming-witness). Try to satisfy the formal statement while
     *violating* the Enuntiatio. If such a witness exists, the statement
     underspecifies the claim -> FAIL (FinishReason.GAMED). Generative, so it
     catches gaps a concordance judge waves through. This is the spine.

  2. MECHANICAL (claim-type probe). For claims that assert a *measurable*
     property, check the property directly -- no LLM in the loop. Dispatched by
     ClaimType. This is where the 'claim-type router' actually belongs.

  3. JUDGED (round-trip + independent judge). Only for claims that resist
     operationalization (ClaimType.OPEN_FORM). Logged against the trust budget so
     the residual stays bounded and visible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from leibniz.propositio import Propositio
from leibniz.types import ClaimType, EdgeEvidence, FinishReason, TrustTier, Verdict
from leibniz.trust import FAITHFULNESS_EDGE
from leibniz.verifiers import SMTVerifier


class ClaimProbe(Protocol):
    """A mechanical check that the formal statement actually encodes the property
    the Enuntiatio asserts -- e.g. that a 'complexity bound' statement really
    quantifies over input size and bounds an operation count."""

    def __call__(self, prop: Propositio) -> Optional[bool]: ...


class FaithfulnessJudge(Protocol):
    """Last-resort LLM judgment. Returns confidence in [0,1] that statement and
    Enuntiatio agree, via round-trip back-translation + independent review."""

    def round_trip_agrees(self, prop: Propositio) -> float: ...


@dataclass
class FaithfulnessGate:
    smt: SMTVerifier
    probes: dict[ClaimType, ClaimProbe]
    judge: FaithfulnessJudge
    judge_threshold: float = 0.9
    gaming_bound: int = 64

    def check(self, prop: Propositio) -> EdgeEvidence:
        assert prop.expressio is not None, "formalize before faithfulness"
        en = prop.enuntiatio

        # 1. Adversarial spine. Always run; cheap relative to proof.
        # When the claim carries a structured contract (ADR 0004), search the real
        # gaming target: an input the claim covers, the proof leaves unconstrained,
        # and on which the claimed property fails. Otherwise fall back to the legacy
        # (prose) call so prose-only claims and the deterministic fakes still work.
        if en.claim_domain and en.claim_property and prop.expressio.established_domain:
            statement = f"not ({prop.expressio.established_domain})"
            negated_claim = f"({en.claim_domain}) and {_negate(en.claim_property)}"
        else:
            statement = prop.expressio.theorem_src
            negated_claim = _negate(en.falsifiable_claim)
        witness = self.smt.backend.find_gaming_witness(
            statement=statement,
            negated_claim=negated_claim,
            bound=self.gaming_bound,
        )
        if witness is not None:
            prop.quarantine(FinishReason.GAMED)
            return EdgeEvidence(
                edge=FAITHFULNESS_EDGE,
                tier=TrustTier.ADVERSARIAL,
                verdict=Verdict.FAIL,
                detail={"gaming_witness": witness},
                cost_units=2.0,
            )

        # 2. Mechanical fast path, dispatched by claim type.
        probe = self.probes.get(en.claim_type)
        if probe is not None:
            result = probe(prop)
            if result is not None:  # probe was decisive
                if not result:
                    prop.quarantine(FinishReason.UNFAITHFUL)
                return EdgeEvidence(
                    edge=FAITHFULNESS_EDGE,
                    tier=TrustTier.MECHANICAL,
                    verdict=Verdict.PASS if result else Verdict.FAIL,
                    detail={"probe": en.claim_type.value},
                    cost_units=2.0,
                )

        # 3. Judged fallback. Only legitimate for open-form claims. Logged.
        if en.claim_type is not ClaimType.OPEN_FORM:
            # A measurable claim with no decisive probe is a DEFER, not a pass:
            # we refuse to launder it through a judge.
            return EdgeEvidence(
                edge=FAITHFULNESS_EDGE,
                tier=TrustTier.MECHANICAL,
                verdict=Verdict.DEFER,
                detail={"reason": "no decisive probe for measurable claim"},
                cost_units=2.0,
            )

        confidence = self.judge.round_trip_agrees(prop)
        passed = confidence >= self.judge_threshold
        if not passed:
            prop.quarantine(FinishReason.UNFAITHFUL)
        return EdgeEvidence(
            edge=FAITHFULNESS_EDGE,
            tier=TrustTier.JUDGED,
            verdict=Verdict.PASS if passed else Verdict.FAIL,
            detail={"round_trip_confidence": confidence, "residual": True},
            cost_units=3.0,
        )


def _negate(predicate: str) -> str:
    """Boolean negation of a predicate, for the gaming-witness search target.

    For a structured claim (ADR 0004) ``predicate`` is the DSL ``claim_property``
    and this yields a Z3-searchable ``not (...)``. For a prose ``falsifiable_claim``
    it yields ``not (...)`` too; the Z3 backend cannot parse prose and degrades to
    "no witness" (the structured path is what makes the spine real)."""
    return f"not ({predicate})"

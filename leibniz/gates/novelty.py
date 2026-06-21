"""The novelty gate -- fixes Newton's real second gap.

Newton's dedup is internal and offline (difflib against its own Codex). That lets
it triumphantly rediscover a textbook theorem. Here novelty is a *promotion gate*
with two mechanical parts:

  external dedup -- retrieve nearest neighbors from a known-results corpus
                    (Mathlib + a curated analysis-of-algorithms set: CLRS-style
                    bounds, named theorems) and compare *structure* via the
                    ClaimSignature, not prose. A structural match -> KNOWN.

  non-triviality -- a statement an automated tactic closes on its own is vacuous.
                    This is the `aesop` test from LeanConjecturer, and it is the
                    convergent-evolution twin of Newton's 'teeth' (a test that
                    kills no mutants is vacuous).

Neither part uses a judge: novelty is settled by retrieval + a decision
procedure, per the trust policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from leibniz.propositio import Propositio
from leibniz.types import ClaimSignature, EdgeEvidence, FinishReason, TrustTier, Verdict
from leibniz.trust import NOVELTY_EDGE
from leibniz.verifiers import LeanVerifier


class KnownCorpus(Protocol):
    """Mathlib + curated known results, queried by structural signature."""

    def contains_equivalent(self, sig: ClaimSignature) -> bool: ...
    def nearest(self, sig: ClaimSignature, k: int = 5) -> list[tuple[str, float]]: ...


@dataclass
class NoveltyGate:
    corpus: KnownCorpus
    lean: LeanVerifier

    def check(self, prop: Propositio) -> EdgeEvidence:
        assert prop.expressio is not None and prop.signature is not None

        # Non-triviality first: cheapest, and a trivial result isn't worth a
        # corpus lookup.
        if self.lean.is_trivial(prop.expressio):
            prop.quarantine(FinishReason.TRIVIAL)
            return EdgeEvidence(
                edge=NOVELTY_EDGE,
                tier=TrustTier.MECHANICAL,
                verdict=Verdict.FAIL,
                detail={"reason": "closed by decision procedure"},
                cost_units=1.0,
                producer="LeanVerifier.is_trivial",  # ADR 0013 §2
            )

        if self.corpus.contains_equivalent(prop.signature):
            prop.quarantine(FinishReason.KNOWN)
            return EdgeEvidence(
                edge=NOVELTY_EDGE,
                tier=TrustTier.MECHANICAL,
                verdict=Verdict.FAIL,
                detail={
                    "reason": "structural match in known corpus",
                    "neighbors": self.corpus.nearest(prop.signature),
                },
                cost_units=1.0,
                producer="CorpusBackend",  # ADR 0013 §2
            )

        return EdgeEvidence(
            edge=NOVELTY_EDGE,
            tier=TrustTier.MECHANICAL,
            verdict=Verdict.PASS,
            detail={"neighbors": self.corpus.nearest(prop.signature)},
            cost_units=1.0,
            producer="NoveltyGate",  # ADR 0013 §2
        )

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
from typing import Optional, Protocol

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
    smt: Optional[object] = None   # accepted for back-compat; ADR 0031 L2 retracted (unused)

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

        # ADR 0032: a RESTATEMENT the exact hash missed — STRUCTURAL congruence match. Two
        # claims share a signature IFF they assert the same polynomial congruence (by FORM, not
        # truth), so this cannot false-KNOWN — the unsoundness that retracted ADR 0031 L2.
        # Unrecognized shapes -> no signature -> stays NOVEL. No backend needed.
        structural_known = getattr(self.corpus, "structural_known", None)
        en = prop.enuntiatio
        if callable(structural_known) and en is not None:
            match = structural_known(en.claim_property)
            if match:
                prop.quarantine(FinishReason.KNOWN)
                return EdgeEvidence(
                    edge=NOVELTY_EDGE,
                    tier=TrustTier.MECHANICAL,
                    verdict=Verdict.FAIL,
                    detail={"reason": "structural congruence match", "match": match},
                    cost_units=1.0,
                    producer="CorpusBackend.structural_known",  # ADR 0013 §2
                )

        return EdgeEvidence(
            edge=NOVELTY_EDGE,
            tier=TrustTier.MECHANICAL,
            verdict=Verdict.PASS,
            detail={"neighbors": self.corpus.nearest(prop.signature)},
            cost_units=1.0,
            producer="NoveltyGate",  # ADR 0013 §2
        )

    def revalidate(self, prop: Propositio) -> Optional[EdgeEvidence]:
        """Re-run the novelty checks on the CURRENT statement/signature/claim, for a
        decision-procedure fast-path that installed a **canonical LAW** after the FORMALIZE
        `check` already ran on the *autoformalized* statement (ADR 0059 review #3). The
        FORMALIZE novelty PASS was recorded against a different theorem string and hash; this
        re-checks the promulgated form. If the canonical law is now TRIVIAL (a tactic closes it)
        or KNOWN (exact-hash or structural-congruence match), quarantine and return a **FAIL**
        `NOVELTY_EDGE` for the caller to record — so `is_promotable` refuses it (a required edge
        is no longer PASS). Otherwise return None: the FORMALIZE PASS stands.

        Same three mechanical parts as `check`, in the same order, no judge — only re-applied to
        the final statement. Idempotent when the statement did not change (returns None)."""
        if prop.expressio is None:
            return None
        if self.lean.is_trivial(prop.expressio):
            prop.quarantine(FinishReason.TRIVIAL)
            return EdgeEvidence(
                edge=NOVELTY_EDGE, tier=TrustTier.MECHANICAL, verdict=Verdict.FAIL,
                detail={"reason": "canonical law closed by decision procedure", "stage": "post-derive"},
                cost_units=1.0, producer="LeanVerifier.is_trivial",  # ADR 0013 §2
            )
        if prop.signature is not None and self.corpus.contains_equivalent(prop.signature):
            prop.quarantine(FinishReason.KNOWN)
            return EdgeEvidence(
                edge=NOVELTY_EDGE, tier=TrustTier.MECHANICAL, verdict=Verdict.FAIL,
                detail={"reason": "canonical law: structural match in known corpus", "stage": "post-derive"},
                cost_units=1.0, producer="CorpusBackend",  # ADR 0013 §2
            )
        structural_known = getattr(self.corpus, "structural_known", None)
        en = prop.enuntiatio
        if callable(structural_known) and en is not None and structural_known(en.claim_property):
            prop.quarantine(FinishReason.KNOWN)
            return EdgeEvidence(
                edge=NOVELTY_EDGE, tier=TrustTier.MECHANICAL, verdict=Verdict.FAIL,
                detail={"reason": "canonical law: structural congruence match", "stage": "post-derive"},
                cost_units=1.0, producer="CorpusBackend.structural_known",  # ADR 0013 §2
            )
        return None

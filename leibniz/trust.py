"""The trust policy -- the load-bearing invariant of the system.

This module exists to make "without relying on capricious LLMs" a property the
code can *check*, not a slogan in a README. It encodes two rules:

  R1. LLMs may occupy only proposal roles (``Role``). They never adjudicate.
  R2. A promotion path is valid only if every edge is MECHANICAL, except the
      single faithfulness edge, which may be ADVERSARIAL or (last resort) JUDGED.

``TrustPolicy.validate_path`` is called by the verification gate before any
promotion. If a path tries to rest a proof on a judged verdict, it raises.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from leibniz.types import EdgeEvidence, TrustTier, Verdict


# The proof edge is sacred. Listed explicitly so a future refactor can't quietly
# downgrade it to a judged verdict.
PROOF_EDGE = "proof<->statement"
FAITHFULNESS_EDGE = "enuntiatio<->statement"
NOVELTY_EDGE = "novelty"

# ADR 0013: the only legitimate producer of a proof-edge verdict. A proof edge that
# carries any other producer is a mislabel and is rejected structurally.
KERNEL_PRODUCER = "LeanVerifier.discharge"


class TrustViolation(Exception):
    """Raised when a promotion path would trust an LLM where it must not."""


@dataclass
class TrustPolicy:
    # Budget for how much judged trust the whole system tolerates, as a fraction
    # of promulgated laws whose faithfulness edge fell back to JUDGED. Tracked so
    # the residual is bounded and visible rather than creeping.
    max_judged_faithfulness_fraction: float = 0.15

    def validate_edge(self, ev: EdgeEvidence) -> None:
        if ev.edge == PROOF_EDGE and ev.tier is not TrustTier.MECHANICAL:
            raise TrustViolation(
                f"proof edge resolved at {ev.tier.value}; only the kernel may "
                f"decide a proof"
            )
        if ev.edge == NOVELTY_EDGE and ev.tier is TrustTier.JUDGED:
            raise TrustViolation(
                "novelty must be settled by retrieval + a decision procedure, "
                "not a judge"
            )
        # ADR 0013: provenance. A proof edge that names a producer must be the
        # kernel's. (Legacy/unstamped edges carry producer=None and are unaffected,
        # so the executable invariants stay byte-identical and green.)
        if (ev.edge == PROOF_EDGE and ev.producer is not None
                and ev.producer != KERNEL_PRODUCER):
            raise TrustViolation(
                f"proof edge produced by {ev.producer!r}; only the Lean kernel "
                f"({KERNEL_PRODUCER}) may decide a proof"
            )

    def validate_path(self, edges: Iterable[EdgeEvidence]) -> None:
        """Raise unless this is an admissible promotion path."""
        edges = list(edges)
        by_edge = {e.edge: e for e in edges}

        if PROOF_EDGE not in by_edge:
            raise TrustViolation("no proof edge present; cannot promulgate")
        for ev in edges:
            self.validate_edge(ev)
            if ev.verdict is not Verdict.PASS:
                raise TrustViolation(
                    f"edge {ev.edge!r} did not PASS ({ev.verdict.value})"
                )

        faith = by_edge.get(FAITHFULNESS_EDGE)
        if faith is None:
            raise TrustViolation("no faithfulness edge present; cannot promulgate")
        # JUDGED faithfulness is *allowed* but flagged for the budget tracker.

    @staticmethod
    def is_judged_faithfulness(edges: Iterable[EdgeEvidence]) -> bool:
        for e in edges:
            if e.edge == FAITHFULNESS_EDGE:
                return e.tier is TrustTier.JUDGED
        return False

    def admits_judged_faithfulness(self, judged_count: int, total_count: int) -> bool:
        """Whether admitting ONE more JUDGED-faithfulness promulgation keeps the
        residual within budget (ADR 0001 §5): ``(judged+1)/(total+1) <= max``.

        Pure and separate from ``validate_path`` (which must still admit a lone
        judged edge for invariant 5). Stateful counting lives in
        ``leibniz.budget.TrustBudget``; this is just the policy arithmetic. The
        first judged promulgation on an empty ledger is refused (1/1 > 0.15), so
        judged faithfulness is admitted only once the ledger is large enough to
        keep it under budget."""
        return (judged_count + 1) <= self.max_judged_faithfulness_fraction * (total_count + 1)

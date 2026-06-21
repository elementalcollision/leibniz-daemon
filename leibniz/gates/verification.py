"""The verification gate -- the deterministic promotion verdict.

Like Newton's gate, ``is_promotable`` is a pure boolean over recorded edge
evidence; it renders no new judgments and re-runs nothing. Unlike Newton's gate,
the conjunction it checks is anchored on a *kernel proof*, and it delegates to
``TrustPolicy`` so the promotion can be rejected if any edge sits at the wrong
trust tier.

Promotion order is also enforced here, so the daemon spends compute in the
cheap-refutation-first order:

    cheap_refutation (SMT, cost~1)
        -> novelty/non-triviality (cost~1)
        -> faithfulness (cost~2-3)
        -> proof (Lean kernel, cost~10)

A failure at any earlier, cheaper edge short-circuits before the expensive proof.
"""

from __future__ import annotations

from dataclasses import dataclass

from leibniz.propositio import Propositio
from leibniz.types import EdgeEvidence, FinishReason, Verdict
from leibniz.trust import (
    FAITHFULNESS_EDGE,
    NOVELTY_EDGE,
    PROOF_EDGE,
    TrustPolicy,
    TrustViolation,
)


@dataclass
class VerificationGate:
    policy: TrustPolicy

    def is_promotable(self, prop: Propositio) -> bool:
        """Pure boolean over recorded evidence. No new judgments, no re-execution."""
        required = {PROOF_EDGE, FAITHFULNESS_EDGE, NOVELTY_EDGE}
        present = {e.edge for e in prop.edges}
        if not required.issubset(present):
            return False
        try:
            self.policy.validate_path(
                [e for e in prop.edges if e.edge in required]
            )
        except TrustViolation:
            return False
        return all(
            e.verdict is Verdict.PASS
            for e in prop.edges
            if e.edge in required
        )

    def finalize(self, prop: Propositio) -> FinishReason:
        """Decide the candidate's terminal state and return the reason."""
        if self.is_promotable(prop):
            prop.promulgated = True
            prop.finish_reason = FinishReason.PROMULGATED
            return FinishReason.PROMULGATED
        # If a gate already quarantined with a specific reason, keep it.
        if prop.finish_reason is not None:
            return prop.finish_reason
        # Otherwise the proof simply wasn't found.
        prop.quarantine(FinishReason.UNPROVEN)
        return FinishReason.UNPROVEN

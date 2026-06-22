"""Lemma-decomposition proving strategy (ADR 0024).

A `DecompositionProver` wraps any base prover and, for a PROOF_DRAFT, asks it to prove
the goal by DECOMPOSITION — establish the intermediate facts it needs as `have`/
`suffices` lemmas, prove each, then close the main goal using them. A structured
multi-step proof routinely closes goals a single one-shot tactic script misses, which is
exactly the bottleneck the ADR 0022/0023 calibrations exposed (conjectures reach the
kernel but the ensemble cannot close them).

Pure proposal-side (ADR 0001): it only reshapes the prompt. The base prover drafts; the
Lean kernel (`LeanVerifier.discharge`) still SOLELY decides, and it checks the *entire*
structured proof — every `have` sub-lemma is kernel-verified as part of the whole, so a
decomposed proof is exactly as trustworthy as a flat one. It slots into the existing N+1
consensus as an additional independent attempt; it never weakens the proof edge.
"""
from __future__ import annotations

from dataclasses import dataclass

from leibniz.types import Role

# Prepended to the PROOF_DRAFT context (the theorem statement). The base prover's own
# system prompt already says "output ONLY the `by` script" — this only changes the
# *strategy*, not the output shape, so it flows through normalize_proof + discharge
# unchanged.
_DECOMPOSE_INSTRUCTION = (
    "Prove this by DECOMPOSITION: first establish the intermediate facts you need as "
    "`have <name> : <statement> := by <proof>` steps (or reduce the goal with "
    "`suffices`), proving each step, then close the main goal using them. A structured "
    "multi-step proof often succeeds where a single tactic does not. Output ONLY the "
    "`by` tactic block.\n\nGoal:\n"
)


@dataclass
class DecompositionProver:
    """Wrap a base prover so its PROOF_DRAFTs are lemma-decomposed. Other roles pass
    through unchanged, so it is a drop-in ensemble member."""

    base: object  # a ProviderAdapter: .propose(role, context) [+ optional .available()]

    def available(self) -> bool:
        check = getattr(self.base, "available", None)
        return check() if callable(check) else True

    def propose(self, role: Role, context: str) -> str:
        if role is Role.PROOF_DRAFT:
            context = _DECOMPOSE_INSTRUCTION + context
        return self.base.propose(role, context)

"""Role router (R4) — a ProviderAdapter that dispatches proposal roles to the right
backend: PROOF_DRAFT to the hosted prover, everything else to the autoformalizer
(ADR 0005). Proposal-only; the kernel still decides.
"""
from __future__ import annotations

from dataclasses import dataclass

from leibniz.types import Role


@dataclass
class RoleRouter:
    autoformalizer: object  # ProviderAdapter for CONJECTURE / FORMALIZE
    prover: object          # ProviderAdapter for PROOF_DRAFT

    def propose(self, role: Role, context: str) -> str:
        if role is Role.PROOF_DRAFT:
            return self.prover.propose(role, context)
        return self.autoformalizer.propose(role, context)

    def available(self) -> bool:
        return self.autoformalizer.available() and self.prover.available()

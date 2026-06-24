"""Failover frontier reasoner — try the primary, fall back through backups (ADR 0029).

The agentic repair loop needs a frontier reasoner for its proof roles (PROOF_DRAFT,
repair_proof). A single provider is a single point of failure: a live measurement stalled
when Anthropic was mid-outage (opus 500s, sonnet 529s). This wraps an ORDERED chain of
providers and, per call, returns the first non-empty success — so an outage of the primary
transparently fails over to backups (e.g. OpenRouter-hosted GLM / Kimi / GPT) without
stalling the loop.

Proposal-only (ADR 0001): every backup only PROPOSES; the Lean kernel still decides every
candidate. Failover changes WHICH model drafts/repairs, never who verifies. `last_used`
records the provider that served the most recent successful call, so a measurement can
report which reasoner actually closed each goal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from leibniz.providers import ProviderUnavailable
from leibniz.types import Role


def _name(provider: object) -> str:
    """A short label for a provider (its model id, else the class name)."""
    return str(getattr(provider, "model", None) or type(provider).__name__)


@dataclass
class FailoverProvider:
    providers: list                      # ordered: primary first, then backups
    last_used: Optional[str] = field(default=None)  # model that served the last success

    def available(self) -> bool:
        return any(self._is_available(p) for p in self.providers)

    @staticmethod
    def _is_available(p: object) -> bool:
        check = getattr(p, "available", None)
        try:
            return bool(check()) if callable(check) else True
        except Exception:
            return False

    def _try(self, method: str, *args):
        """Call `method` on each available provider in order; return the first non-empty
        result. Any exception or empty/whitespace output is treated as a failure and we
        move to the next backup. Raises ProviderUnavailable only if ALL fail."""
        errors: list[str] = []
        for p in self.providers:
            fn = getattr(p, method, None)
            if fn is None or not self._is_available(p):
                continue
            try:
                out = fn(*args)
            except Exception as e:  # transient API error (5xx/429/timeout), bad key, etc.
                errors.append(f"{_name(p)}: {type(e).__name__}")
                continue
            if out and str(out).strip():
                self.last_used = _name(p)
                return out
            errors.append(f"{_name(p)}: empty")
        raise ProviderUnavailable(
            f"all {len(self.providers)} reasoner(s) failed for {method}: {'; '.join(errors) or 'none available'}"
        )

    # The repair loop's surface (ProofRepairer calls only these two).
    def propose(self, role: Role, context: str) -> str:
        return self._try("propose", role, context)

    def repair_proof(self, theorem_src: str, failed_proof: str, error: str) -> str:
        return self._try("repair_proof", theorem_src, failed_proof, error)

    # ADR 0029: the autoformalizer surface, so a failover-wrapped autoformalizer keeps its
    # CONJECTURE/FORMALIZE repair + decomposition loops (the pipeline looks these up via
    # getattr — omitting them would silently DISABLE those loops). Each delegates down the
    # chain: the primary serves them when up, a backup when it is overloaded.
    def repair_formalization(self, statement: str, prior_src: str, error: str) -> str:
        return self._try("repair_formalization", statement, prior_src, error)

    def repair_contract(
        self, statement: str, claim_domain: str, claim_property: str,
        established_domain: str, problems: list,
    ) -> str:
        return self._try(
            "repair_contract", statement, claim_domain, claim_property, established_domain, problems)

    def decompose(self, theorem_src: str) -> str:
        return self._try("decompose", theorem_src)

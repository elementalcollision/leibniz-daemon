"""Anthropic (Claude) proposal provider for CONJECTURE / FORMALIZE (R4).

Proposal-only (ADR 0001): returns structured JSON drafts (ADR 0005), never
verdicts. Lazy SDK import + env key, so this ships without the `propose` extra and
calls out only once `ANTHROPIC_API_KEY` is set.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from leibniz.providers import (
    AUTOFORMALIZE_DSL,
    AUTOFORMALIZE_PROMPTS,
    AUTOFORMALIZE_SYSTEM,
    ProviderUnavailable,
    decompose_prompt,
    repair_contract_prompt,
    repair_formalization_prompt,
    repair_proof_prompt,
)
from leibniz.types import Role

DEFAULT_MODEL = "claude-opus-4-8"

# Shared single source of truth (providers/__init__.py) so the OpenRouter failover backup
# builds byte-identical conjecture/formalize prompts — they cannot drift. Re-exported here
# under the historical names so existing tests/importers keep working.
_SYSTEM = AUTOFORMALIZE_SYSTEM
_DSL = AUTOFORMALIZE_DSL
# PROOF_DRAFT / repair_proof must return a BARE Lean tactic script — NOT JSON. The default
# _SYSTEM forces JSON (right for CONJECTURE/FORMALIZE, which are parsed as JSON), so the
# proof roles use this proof-system prompt instead, or the kernel gets `{"script": ...}`
# and can never elaborate it (caught by the ADR 0029 live measurement).
_PROOF_SYSTEM = (
    "You draft and repair Lean 4 tactic scripts for a theorem daemon. Output ONLY the "
    "proof term/script (e.g. starting with `by`), no prose, no backticks, no JSON. You "
    "PROPOSE; a Lean kernel DECIDES — never claim the proof is correct."
)

# The CONJECTURE/FORMALIZE/PROOF_DRAFT templates + the faithfulness DSL now live in
# providers/__init__.py (single source of truth) so the OpenRouter failover backup uses
# byte-identical prompts. Aliased here so the rest of this module is unchanged.
_PROMPTS = AUTOFORMALIZE_PROMPTS


@dataclass
class AnthropicProvider:
    model: str = DEFAULT_MODEL
    api_key_env: str = "ANTHROPIC_API_KEY"
    max_tokens: int = 2048
    meter: Optional[object] = None  # ADR 0014: has .record_usage(model, in, out)
    max_retries: int = 5  # SDK retries transient 429/5xx with backoff (live runs hit bursts)

    def available(self) -> bool:
        if not os.environ.get(self.api_key_env):
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            return False

    def _chat(self, user_content: str, system: Optional[str] = None) -> str:
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover
            raise ProviderUnavailable("anthropic SDK not installed (propose extra)") from e
        key = os.environ.get(self.api_key_env)
        if not key:
            raise ProviderUnavailable(f"{self.api_key_env} not set")
        client = anthropic.Anthropic(api_key=key, max_retries=self.max_retries)
        msg = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system or _SYSTEM,
            messages=[{"role": "user", "content": user_content}],
        )
        self._meter(msg)
        return "".join(getattr(b, "text", "") for b in msg.content).strip()

    def _meter(self, msg: object) -> None:
        """ADR 0014: report real token usage to the cost meter (best-effort)."""
        if self.meter is None:
            return
        usage = getattr(msg, "usage", None)
        if usage is None:
            return
        try:
            self.meter.record_usage(
                self.model,
                int(getattr(usage, "input_tokens", 0) or 0),
                int(getattr(usage, "output_tokens", 0) or 0),
            )
        except Exception:  # metering must never break a proposal
            pass

    def propose(self, role: Role, context: str) -> str:
        template = _PROMPTS.get(role)
        if template is None:
            raise ProviderUnavailable(f"AnthropicProvider does not handle role {role}")
        # PROOF_DRAFT must come back as a BARE tactic script; CONJECTURE/FORMALIZE as JSON.
        system = _PROOF_SYSTEM if role is Role.PROOF_DRAFT else None
        return self._chat(template.format(context=context), system=system)

    def repair_proof(self, theorem_src: str, failed_proof: str, error: str) -> str:
        """ADR 0029: the kernel rejected this proof; repair it given the actual error.

        Returns ONLY a corrected `by ...` tactic script. The reasoner may change only
        the PROOF — never the theorem statement (changing it would let a repair 'prove'
        a different, weaker claim). The kernel re-checks whatever this returns; this only
        proposes. Toolchain is Lean 4.31 + current Mathlib."""
        # bare script, not JSON -> the proof system prompt (shared prompt: never drifts from
        # OpenRouterProvider.repair_proof, since both repair-capable providers use it)
        return self._chat(repair_proof_prompt(theorem_src, failed_proof, error), system=_PROOF_SYSTEM)

    def repair_formalization(self, statement: str, prior_src: str, error: str) -> str:
        """R4.2: hand a failed Lean compile back to the autoformalizer to fix the
        imports/statement, given the kernel's actual error. Returns corrected JSON.
        Prompt shared with the failover backup (providers/__init__.py)."""
        return self._chat(repair_formalization_prompt(statement, prior_src, error))

    def repair_contract(
        self,
        statement: str,
        claim_domain: str,
        claim_property: str,
        established_domain: str,
        problems: list[str],
    ) -> str:
        """ADR 0022: the faithfulness checker cannot decide this contract because one
        or more predicates are outside its DSL. Restate the three predicates INSIDE the
        DSL, preserving meaning — do NOT change the human claim and do NOT narrow
        claim_domain to dodge the checker. Returns corrected JSON. Prompt shared with the
        failover backup (providers/__init__.py)."""
        return self._chat(repair_contract_prompt(
            statement, claim_domain, claim_property, established_domain, problems))

    def decompose(self, theorem_src: str) -> str:
        """ADR 0027: a hard theorem one-shot proving missed. Propose helper LEMMAS that,
        once proven independently, make the main proof short — plus the main proof citing
        them by name. Each lemma is proven on its own and the kernel re-verifies the whole
        composed artifact, so this only proposes; it never decides. Returns JSON.
        Prompt shared with the failover backup (providers/__init__.py)."""
        return self._chat(decompose_prompt(theorem_src))

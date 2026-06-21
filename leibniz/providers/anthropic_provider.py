"""Anthropic (Claude) proposal provider for CONJECTURE / FORMALIZE (R4).

Proposal-only (ADR 0001): returns structured JSON drafts (ADR 0005), never
verdicts. Lazy SDK import + env key, so this ships without the `propose` extra and
calls out only once `ANTHROPIC_API_KEY` is set.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from leibniz.providers import ProviderUnavailable
from leibniz.types import Role

DEFAULT_MODEL = "claude-opus-4-8"

_SYSTEM = (
    "You are a proposal engine for an automated theorem daemon working in analysis "
    "of algorithms. You PROPOSE; a Lean kernel and mechanical gates DECIDE. Never "
    "claim something is proven. Respond with ONLY the requested JSON, no prose."
)

_PROMPTS = {
    Role.CONJECTURE: (
        "Propose ONE novel, plausibly-true, non-trivial conjecture seeded by: {context}\n"
        'Return JSON: {{"statement": <human claim>, "claim_type": '
        '"complexity_bound|correctness|optimality|invariant|existence|structural|open_form", '
        '"falsifiable_claim": <what would refute it>, '
        '"claim_domain": <arithmetic predicate over n, e.g. "n >= 1">, '
        '"claim_property": <arithmetic predicate over n the claim asserts>}}'
    ),
    Role.FORMALIZE: (
        "Formalize this claim as a Lean 4 theorem statement (header only, no proof): {context}\n"
        'Return JSON: {{"theorem_src": "theorem name : ...", '
        '"imports": ["Mathlib.Tactic"], '
        '"established_domain": <arithmetic predicate over n the statement actually covers>}}'
    ),
    Role.PROOF_DRAFT: (
        "Draft a Lean 4 tactic script proving this statement. Return ONLY the script "
        "starting with `by`:\n{context}"
    ),
}


@dataclass
class AnthropicProvider:
    model: str = DEFAULT_MODEL
    api_key_env: str = "ANTHROPIC_API_KEY"
    max_tokens: int = 2048
    meter: Optional[object] = None  # ADR 0014: has .record_usage(model, in, out)

    def available(self) -> bool:
        if not os.environ.get(self.api_key_env):
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            return False

    def _chat(self, user_content: str) -> str:
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover
            raise ProviderUnavailable("anthropic SDK not installed (propose extra)") from e
        key = os.environ.get(self.api_key_env)
        if not key:
            raise ProviderUnavailable(f"{self.api_key_env} not set")
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=_SYSTEM,
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
        return self._chat(template.format(context=context))

    def repair_formalization(self, statement: str, prior_src: str, error: str) -> str:
        """R4.2: hand a failed Lean compile back to the autoformalizer to fix the
        imports/statement, given the kernel's actual error. Returns corrected JSON."""
        prompt = (
            "Your Lean 4 formalization failed to compile. Fix it. Toolchain is Lean "
            "4.31 + current Mathlib — module paths may have moved since older Mathlib. "
            "If an import 'does not exist', replace it with the correct current module "
            "or drop it and rely on `import Mathlib.Tactic`. Keep the statement "
            "faithful to the claim; do not weaken it to make it compile.\n"
            f"Claim: {statement}\n"
            f"Previous attempt:\n{prior_src}\n"
            f"Lean error:\n{error[:1500]}\n"
            'Return corrected JSON only: {"theorem_src": "theorem name : ...", '
            '"imports": ["Mathlib.Tactic", ...], "established_domain": "<predicate over n>"}'
        )
        return self._chat(prompt)

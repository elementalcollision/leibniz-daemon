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

# ADR 0022: the faithfulness checker can only certify a contract whose predicates
# live in this sound, Z3-decidable arithmetic DSL (ADR 0021). A contract outside it
# DEFERs before any proof compute — so it can never be promulgated. Steer proposals
# INTO the grammar; this is the single source of truth quoted to both roles.
_DSL = (
    "FAITHFULNESS DSL — the contract predicates must use ONLY these constructs, or "
    "the claim is rejected (DEFERred) before it can ever be proven:\n"
    "  • non-negative integer variables — name them freely (n, a, b, k, ...)\n"
    "  • non-negative integer literals\n"
    "  • + - *  (add, subtract, multiply)\n"
    "  • ^ with a CONSTANT exponent 0..8 (n^2, (a+b)^3) — NOT a variable exponent\n"
    "  • / and % by a CONSTANT positive divisor (n/2, n%3)\n"
    "  • comparisons < <= > >= == != ; and / or / not ; parentheses\n"
    "FORBIDDEN (these make the claim un-checkable): named functions (log, sqrt, gcd, "
    "factorial, Nat.log, min, max, floor, sums/products), VARIABLE exponents (2^n, "
    "k^n), division/modulo by a variable, real/rational numbers, quantifiers inside "
    "a predicate. If the natural claim needs any of these, RESTATE it as an "
    "elementary-arithmetic statement that does fit (e.g. a concrete polynomial bound, "
    "a divisibility/mod identity) — that is the novel-yet-tractable band."
)

_PROMPTS = {
    Role.CONJECTURE: (
        "Propose ONE conjecture that is (a) NOVEL — not a textbook/Mathlib result, "
        "(b) genuinely NON-TRIVIAL, and (c) PLAUSIBLY PROVABLE with standard Mathlib "
        "tactics, possibly needing a short helper lemma or induction. The aim is the "
        "band of the novel-yet-tractable. Honour any lessons and target difficulty band "
        "in the context (emulate what proved, AVOID what was trivial/known, weaken what "
        "was too hard).\n"
        "NON-TRIVIALITY IS ENFORCED MECHANICALLY: a statement that a SINGLE decision "
        "procedure closes on its own — `decide`, `simp`, `omega`, `trivial`, `aesop`, "
        "`ring`, or `nlinarith` — is quarantined as TRIVIAL and can NEVER be promulgated. "
        "So DO NOT propose a pure polynomial identity or a polynomial (in)equality: "
        "`ring`/`nlinarith` close those instantly. Aim instead for claims needing "
        "INDUCTION, CASE ANALYSIS, or a HELPER LEMMA — e.g. a divisibility or modular "
        "fact about a NON-LINEAR expression, or a property that holds by parity / "
        "recursion.\n"
        "The claim must come with a machine-checkable CONTRACT (claim_domain, "
        "claim_property): for all integer inputs satisfying claim_domain, claim_property "
        "holds. BOTH predicates MUST be inside the DSL below.\n"
        f"{_DSL}\n"
        "Example (non-trivial AND encodable) — statement \"6 divides the product of any "
        "three consecutive integers\"; claim_domain \"n >= 0\"; claim_property "
        "\"n*(n+1)*(n+2) % 6 == 0\" — needs a divisibility/induction argument, so `ring` "
        "cannot close it, yet the contract is plain DSL.\n"
        "Context: {context}\n"
        'Return JSON: {{"statement": <human claim>, "claim_type": '
        '"complexity_bound|correctness|optimality|invariant|existence|structural|open_form", '
        '"falsifiable_claim": <what would refute it>, '
        '"claim_domain": <DSL predicate bounding the inputs>, '
        '"claim_property": <DSL predicate the claim asserts on that domain>}}'
    ),
    Role.FORMALIZE: (
        "Formalize this claim as a Lean 4 theorem statement (header only, no proof): {context}\n"
        "Also give established_domain: the DSL predicate over the same integer "
        "variables that the formal statement ACTUALLY establishes the property on. It "
        "must COVER claim_domain (be at least as broad) and stay inside the DSL.\n"
        f"{_DSL}\n"
        'Return JSON: {{"theorem_src": "theorem name : ...", '
        '"imports": ["Mathlib.Tactic"], '
        '"established_domain": <DSL predicate the statement covers>}}'
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

    def repair_proof(self, theorem_src: str, failed_proof: str, error: str) -> str:
        """ADR 0029: the kernel rejected this proof; repair it given the actual error.

        Returns ONLY a corrected `by ...` tactic script. The reasoner may change only
        the PROOF — never the theorem statement (changing it would let a repair 'prove'
        a different, weaker claim). The kernel re-checks whatever this returns; this only
        proposes. Toolchain is Lean 4.31 + current Mathlib."""
        prompt = (
            "Your Lean 4 proof FAILED to verify. Repair it using the kernel's error. "
            "Output ONLY the corrected proof — a tactic script starting with `by` — with "
            "no prose and no backticks. Do NOT change, restate, or weaken the theorem; "
            "fix only the proof. Toolchain is Lean 4.31 + current Mathlib (prefer "
            "`import Mathlib.Tactic` lemmas/tactics). You PROPOSE; the Lean kernel "
            "DECIDES — do not claim the repair is correct.\n"
            f"Theorem (do NOT change):\n{theorem_src}\n"
            f"Failed proof:\n{failed_proof}\n"
            f"Lean error:\n{error[:1500]}"
        )
        return self._chat(prompt)

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
        claim_domain to dodge the checker. Returns corrected JSON."""
        prompt = (
            "The machine-checkable CONTRACT for your claim cannot be verified: these "
            f"fields use constructs outside the decidable DSL: {', '.join(problems)}. "
            "Restate ALL THREE predicates so each is inside the DSL, WITHOUT changing "
            "what the claim means.\n"
            f"{_DSL}\n"
            f"Claim (do NOT change): {statement}\n"
            "Current contract:\n"
            f"  claim_domain: {claim_domain}\n"
            f"  claim_property: {claim_property}\n"
            f"  established_domain: {established_domain}\n"
            "Rules: keep claim_domain NON-EMPTY and just as broad (adding constraints "
            "to shrink it is cheating and will be rejected); keep claim_property at "
            "least as STRONG (a weaker/hollowed property is rejected — the new one must "
            "imply the old); established_domain must COVER claim_domain; preserve the "
            "mathematical meaning. If the claim genuinely cannot be expressed in this "
            "DSL, return the fields unchanged.\n"
            'Return JSON only: {"claim_domain": "...", "claim_property": "...", '
            '"established_domain": "..."}'
        )
        return self._chat(prompt)

    def decompose(self, theorem_src: str) -> str:
        """ADR 0027: a hard theorem one-shot proving missed. Propose helper LEMMAS that,
        once proven independently, make the main proof short — plus the main proof citing
        them by name. Each lemma is proven on its own and the kernel re-verifies the whole
        composed artifact, so this only proposes; it never decides. Returns JSON."""
        prompt = (
            "This Lean 4 theorem is hard to prove in one shot. DECOMPOSE it: propose 1-4 "
            "helper LEMMAS that, once proven, make the main proof short, plus the main "
            "proof that uses them BY NAME. Each lemma must be a self-contained Lean 4 "
            "statement provable on its own (induction / case analysis welcome), and "
            "genuinely useful for the main goal. Name them aux1, aux2, ... Use ONLY "
            "`lemma`/tactic proofs — never `axiom`, `sorry`, `admit`, or `opaque`.\n"
            f"Theorem:\n{theorem_src}\n"
            'Return JSON only: {"lemmas": [{"name": "aux1", "statement": "<binders> : '
            '<prop>"}], "main_proof": "by <tactic script citing aux1, aux2, ...>"}. '
            'The lemma "statement" is everything AFTER the lemma name, e.g. '
            '"(n : Nat) : 2 ∣ n * (n + 1)". One line per statement, no `:=`.'
        )
        return self._chat(prompt)

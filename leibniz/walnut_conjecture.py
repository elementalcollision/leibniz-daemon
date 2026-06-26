"""Conjecturer-side generation of automatic-sequence claims (ADR 0038) — the proposal side
that FEEDS the Walnut-decided Observatory tier.

It asks the provider (LLM, proposal-only) to propose a genuinely-novel automatic-sequence
conjecture as a FREE-VARIABLE Walnut FO predicate over a numeration, parses it into a
Propositio carrying ``Expressio.walnut_predicate`` / ``.walnut_numeration``, and (optionally)
decides it via ``WalnutObservatory``.

Trust: propose/decide separation holds — the LLM only PROPOSES; **Walnut** (a sound decision
procedure, via ``WalnutObservatory.decide``) decides, and the gate re-checks. A generated
claim can NEVER be Q.E.D.; it can only land in the non-Q.E.D. tier (ADR 0038). This module is
proposal-side only: it gates nothing and decides nothing. Off by default; live generation
needs the provider + the Walnut binary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from leibniz.adapters import ProviderAdapter
from leibniz.observatory import WalnutObservatory
from leibniz.pipeline import _maybe_json
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimType, Role

# The proposal prompt. Pushes toward NON-textbook automatic-sequence conjectures expressed
# as a single-free-variable FO predicate (what the Walnut tier can decide); forbids the
# command-language metacharacters the runner would reject anyway (so malformed proposals fail
# early rather than DEFERring in the runner).
WALNUT_SEED = (
    "Propose a genuinely NON-textbook conjecture about a k-automatic sequence (Thue-Morse, "
    "Rudin-Shapiro, paperfolding, Tribonacci/Fibonacci word, Stern, or a base-b/Pisot sequence) "
    "that is expressible as a FIRST-ORDER formula with exactly ONE free variable n over a "
    "numeration (msd_2, msd_fib, msd_trib, ...). Return JSON with keys: statement (plain English), "
    "walnut_predicate (a Walnut FO formula in n using E/A quantifiers, &, |, ~, =>, SEQ[i], +, <, "
    "with n the only free variable; NO quotes, semicolons, or newlines), walnut_numeration, and "
    "falsifiable_claim. The conjecture must be true for all n (the tier decides universality)."
)


def parse_walnut_claim(draft: str) -> Optional[Propositio]:
    """Parse a CONJECTURE draft into an automatic-sequence ``Propositio``, or ``None`` if it
    lacks a usable Walnut predicate + numeration + statement. Robust to fenced/JSON drafts."""
    data = _maybe_json(draft)
    if not data:
        return None
    pred, num, stmt = (data.get("walnut_predicate"), data.get("walnut_numeration"),
                       data.get("statement"))
    if not (pred and num and stmt):
        return None
    en = Enuntiatio(
        statement=str(stmt),
        claim_type=ClaimType.INVARIANT,
        falsifiable_claim=str(data.get("falsifiable_claim") or f"exists n violating: {stmt}"),
    )
    ex = Expressio(
        theorem_src=f"-- walnut-decided claim (non-Q.E.D.): {stmt}",
        walnut_predicate=str(pred),
        walnut_numeration=str(num),
    )
    return Propositio(enuntiatio=en, expressio=ex, seed_origin="walnut")


@dataclass
class WalnutConjecturer:
    """Generate automatic-sequence claims and file them in the non-Q.E.D. Walnut tier."""

    provider: ProviderAdapter
    observatory: WalnutObservatory = field(default_factory=WalnutObservatory)

    def generate(self, seed: str = WALNUT_SEED) -> Optional[Propositio]:
        """Propose ONE automatic-sequence claim (proposal only; nothing decided yet)."""
        try:
            draft = self.provider.propose(Role.CONJECTURE, seed)
        except Exception:
            return None  # a proposal failure must never break the caller
        return parse_walnut_claim(draft)

    def generate_and_decide(self, seed: str = WALNUT_SEED) -> Optional[Propositio]:
        """Propose, then DECIDE via Walnut (the non-Q.E.D. tier). Returns the filed Propositio,
        or ``None`` if the proposal was unusable. The decision/soundness is the Observatory's
        job (reviewed); this only routes a proposed claim to it."""
        prop = self.generate(seed)
        if prop is None:
            return None
        return self.observatory.decide(prop)

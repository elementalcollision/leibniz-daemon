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

# A LIGHT steering context. The full schema + Walnut syntax live in the shared
# Role.WALNUT_CONJECTURE prompt template (leibniz/providers/__init__.py), so they cannot drift
# across providers (the ADR 0013 shared-prompt discipline). This is just per-call variation.
WALNUT_SEED = "Vary the sequence and the property from any you have proposed before."


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
    # ADR 0039: carry the machine-checkable property descriptor (if any) so the Observatory's
    # faithfulness lint can cross-check the predicate's INTENT before filing DECIDED. Only a dict
    # is kept; anything else is dropped to None (the lint then DEFERs under require_descriptor).
    descriptor = data.get("property_descriptor")
    ex = Expressio(
        theorem_src=f"-- walnut-decided claim (non-Q.E.D.): {stmt}",
        walnut_predicate=str(pred),
        walnut_numeration=str(num),
        property_descriptor=descriptor if isinstance(descriptor, dict) else None,
    )
    return Propositio(enuntiatio=en, expressio=ex, seed_origin="walnut")


@dataclass
class WalnutConjecturer:
    """Generate automatic-sequence claims and file them in the non-Q.E.D. Walnut tier."""

    provider: ProviderAdapter
    # ADR 0039: the live tier REQUIRES a usable property_descriptor before filing a DECIDED-true
    # (the formal-first record needs a machine-checkable faithfulness anchor). A descriptor-less
    # or undescribable decision is quarantined, not filed.
    observatory: WalnutObservatory = field(
        default_factory=lambda: WalnutObservatory(require_descriptor=True))
    # Diagnostics for the most recent generate() (so a silent all-fail run is debuggable):
    last_draft: Optional[str] = None     # the raw provider draft (None if the provider errored)
    last_error: Optional[str] = None     # the provider exception text, if any

    def generate(self, context: str = WALNUT_SEED) -> Optional[Propositio]:
        """Propose ONE automatic-sequence claim via Role.WALNUT_CONJECTURE (proposal only;
        nothing decided yet). Records last_draft/last_error so a parse/provider failure is
        visible rather than a silent None."""
        self.last_draft = self.last_error = None
        try:
            draft = self.provider.propose(Role.WALNUT_CONJECTURE, context)
        except Exception as e:  # a proposal failure must never break the caller
            self.last_error = f"{type(e).__name__}: {e}"
            return None
        self.last_draft = draft
        return parse_walnut_claim(draft)

    def generate_and_decide(self, context: str = WALNUT_SEED) -> Optional[Propositio]:
        """Propose, then DECIDE via Walnut (the non-Q.E.D. tier). Returns the filed Propositio,
        or ``None`` if the proposal was unusable. The decision/soundness is the Observatory's
        job (reviewed); this only routes a proposed claim to it."""
        prop = self.generate(context)
        if prop is None:
            return None
        return self.observatory.decide(prop)

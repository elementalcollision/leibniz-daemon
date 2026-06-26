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
WALNUT_SEED = (
    "Propose a NON-textbook, plausibly-TRUE automatic-sequence conjecture. A FALSE claim is "
    "mechanically refuted and wastes the run, and a claim duplicating an earlier one is wasted "
    "too — aim for a property you believe holds for ALL n yet is not a first-year fact."
)

# Anti-collapse ROTATION (run-2 finding: 20/20 calls produced the *same* RS-4th-power-free claim
# because each call saw only a static seed with no memory). We steer breadth across the
# lint-checkable words × families so successive proposals cannot all collapse onto one idea.
# Paperfolding is omitted (the lint cannot anchor it yet ⇒ it would only quarantine).
WALNUT_WORDS = ("Thue-Morse T", "Rudin-Shapiro RS", "Fibonacci word F", "Tribonacci TR")
WALNUT_FAMILIES = (
    "power-freeness — choose an exponent e in 2..6 you believe HOLDS (e.g. cube-free, 5th-power-free)",
    "avoiding a specific short block — choose a concrete block over the sequence's own alphabet",
    "no strictly-alternating factor of a chosen length L",
)


def _rotation_target(i: int) -> str:
    """A breadth steer for call ``i``: word cycles fastest, family every len(WALNUT_WORDS)."""
    w = WALNUT_WORDS[i % len(WALNUT_WORDS)]
    f = WALNUT_FAMILIES[(i // len(WALNUT_WORDS)) % len(WALNUT_FAMILIES)]
    return (f"For THIS proposal, target sequence: {w}; property family: {f}. "
            "This is a breadth STEER, not a hard constraint — but do vary genuinely.")


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
    # Anti-collapse SESSION MEMORY: each proposal's (statement, outcome) so the next call's
    # context can say "do not repeat these" and "this one was refuted". `call_index` drives the
    # breadth rotation. Proposal-side only — no trust state lives here.
    history: list[dict] = field(default_factory=list)
    call_index: int = 0

    def _build_context(self) -> str:
        """The dynamic per-call steer: base seed + a rotating (word, family) target + the
        session avoid-list (prior statements and how they were decided)."""
        parts = [WALNUT_SEED, _rotation_target(self.call_index)]
        if self.history:
            avoid = "\n".join(f"  - {h['statement']} -> {h['outcome']}" for h in self.history[-12:])
            parts.append(
                "You have ALREADY proposed these THIS SESSION — do NOT repeat or trivially reword "
                "any (especially the ones marked refuted/unproven); choose a genuinely different "
                "sequence and/or property:\n" + avoid)
        return "\n".join(parts)

    def _remember(self, statement: Optional[str], outcome: str) -> None:
        self.history.append({"statement": (statement or "(unparseable draft)")[:100],
                             "outcome": outcome})

    def generate(self, context: Optional[str] = None) -> Optional[Propositio]:
        """Propose ONE automatic-sequence claim via Role.WALNUT_CONJECTURE (proposal only;
        nothing decided yet). Builds an anti-collapse context (rotation + session avoid-list)
        unless an explicit ``context`` is supplied. Records last_draft/last_error so a
        parse/provider failure is visible rather than a silent None, and appends to ``history``."""
        self.last_draft = self.last_error = None
        ctx = context if context is not None else self._build_context()
        self.call_index += 1
        try:
            draft = self.provider.propose(Role.WALNUT_CONJECTURE, ctx)
        except Exception as e:  # a proposal failure must never break the caller
            self.last_error = f"{type(e).__name__}: {e}"
            self._remember(None, "no_proposal")
            return None
        self.last_draft = draft
        prop = parse_walnut_claim(draft)
        self._remember(prop.enuntiatio.statement if prop else None,
                       "proposed" if prop else "no_proposal")
        return prop

    def generate_and_decide(self, context: Optional[str] = None) -> Optional[Propositio]:
        """Propose, then DECIDE via Walnut (the non-Q.E.D. tier). Returns the filed Propositio,
        or ``None`` if the proposal was unusable. Records the decision outcome back into
        ``history`` so the next proposal's avoid-list shows what was refuted/decided. The
        decision/soundness is the Observatory's job (reviewed); this only routes to it."""
        prop = self.generate(context)
        if prop is None:
            return None
        out = self.observatory.decide(prop)
        if self.history:  # thread the outcome back so future calls avoid refuted ideas
            self.history[-1]["outcome"] = out.finish_reason.value if out.finish_reason else "unknown"
        return out

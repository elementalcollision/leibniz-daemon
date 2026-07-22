"""The trust policy -- the load-bearing invariant of the system.

This module exists to make "without relying on capricious LLMs" a property the
code can *check*, not a slogan in a README. It encodes two rules:

  R1. LLMs may occupy only proposal roles (``Role``). They never adjudicate.
  R2. A promotion path is valid only if every edge is MECHANICAL, except the
      single faithfulness edge, which may be ADVERSARIAL or (last resort) JUDGED.

``TrustPolicy.validate_path`` is called by the verification gate before any
promotion. If a path tries to rest a proof on a judged verdict, it raises.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from leibniz.types import EdgeEvidence, TrustTier, Verdict


# The proof edge is sacred. Listed explicitly so a future refactor can't quietly
# downgrade it to a judged verdict.
PROOF_EDGE = "proof<->statement"
FAITHFULNESS_EDGE = "enuntiatio<->statement"
NOVELTY_EDGE = "novelty"

# ADR 0013: the only legitimate producer of a proof-edge verdict. A proof edge that
# carries any other producer is a mislabel and is rejected structurally.
KERNEL_PRODUCER = "LeanVerifier.discharge"

# ADR 0013 §2: producers whose output is irreducible LLM judgment. A MECHANICAL or
# ADVERSARIAL edge that names one of these is a mislabel (a judged verdict dressed
# as mechanical) and is rejected.
JUDGE_PRODUCER = "FaithfulnessJudge"
JUDGE_PRODUCERS = frozenset({JUDGE_PRODUCER})

# ADR 0041 (ATTACK 2): the operator-owned allowlist of legitimate producers of a MECHANICAL
# faithfulness edge -- the same pin pattern as PROOF_EDGE/KERNEL_PRODUCER. A mechanical faithfulness
# edge naming a producer outside this set is a mislabel (e.g. a self-built tool's re-checker that was
# never operator-admitted to State 2) and is rejected structurally. Legacy/unstamped edges carry
# producer=None and are unaffected, so the executable invariants stay byte-identical and green. A NEW
# faithfulness producer (a tool admitted per ADR 0041 §2.2) is added HERE by an operator, never
# autonomously -- this constant lives in the PreToolUse-guarded trust core.
FAITHFULNESS_PRODUCERS = frozenset({
    "SMTVerifier.gaming_witness",   # the bounded-Z3 gaming-witness FAIL spine
    "ClaimProbe",                   # the per-ClaimType mechanical probe
    "FaithfulnessGate",             # the gate's own DEFER / refusal (not a judge)
    "walnut/recheck",               # the Walnut sound backend (ADR 0037 / 0038)
    "lean_decided/kernel",          # the Lean-decided faithfulness backend (ADR 0056; reviewed + activated)
    "minmax_identity/kernel",       # the order-split min/max faithfulness backend (ADR 0059; reviewed + activated)
    "boolean_modular/kernel",       # the ZMod-decide same-modulus boolean-combo backend (ADR 0059; reviewed + activated)
    "mixed_modular/kernel",         # the LCM/castHom mixed-modulus backend (ADR 0060; reviewed + activated)
    "power_mod/kernel",             # the order-split symbolic-exponent backend (ADR 0065; reviewed + activated)
    "factgcd/kernel",               # the factorial/gcd two-regime backend (ADR 0070; reviewed + activated)
})


class TrustViolation(Exception):
    """Raised when a promotion path would trust an LLM where it must not."""


@dataclass
class TrustPolicy:
    # Budget for how much judged trust the whole system tolerates, as a fraction
    # of promulgated laws whose faithfulness edge fell back to JUDGED. Tracked so
    # the residual is bounded and visible rather than creeping.
    max_judged_faithfulness_fraction: float = 0.15

    def validate_edge(self, ev: EdgeEvidence) -> None:
        if ev.edge == PROOF_EDGE and ev.tier is not TrustTier.MECHANICAL:
            raise TrustViolation(
                f"proof edge resolved at {ev.tier.value}; only the kernel may "
                f"decide a proof"
            )
        if ev.edge == NOVELTY_EDGE and ev.tier is TrustTier.JUDGED:
            raise TrustViolation(
                "novelty must be settled by retrieval + a decision procedure, "
                "not a judge"
            )
        # ADR 0013: provenance. A proof edge that names a producer must be the
        # kernel's. (Legacy/unstamped edges carry producer=None and are unaffected,
        # so the executable invariants stay byte-identical and green.)
        if (ev.edge == PROOF_EDGE and ev.producer is not None
                and ev.producer != KERNEL_PRODUCER):
            raise TrustViolation(
                f"proof edge produced by {ev.producer!r}; only the Lean kernel "
                f"({KERNEL_PRODUCER}) may decide a proof"
            )
        # ADR 0013 §2: a non-JUDGED edge must not carry a judge producer (a judged
        # verdict mislabeled mechanical/adversarial). The JUDGED tier is where a
        # judge legitimately appears (and only on the faithfulness edge, by tier).
        if ev.tier is not TrustTier.JUDGED and ev.producer in JUDGE_PRODUCERS:
            raise TrustViolation(
                f"{ev.tier.value} edge {ev.edge!r} produced by judge "
                f"{ev.producer!r}; a judged verdict may not be tagged {ev.tier.value}"
            )
        # ADR 0041 (ATTACK 2): a MECHANICAL faithfulness edge must carry a producer from the
        # operator-owned allowlist (mirrors the KERNEL_PRODUCER pin on the proof edge). This blocks a
        # tool/built-checker from laundering a faithfulness PASS with an arbitrary producer string.
        # producer=None (legacy/unstamped) is unaffected, keeping the executable invariants
        # byte-identical.
        if (ev.edge == FAITHFULNESS_EDGE and ev.tier is TrustTier.MECHANICAL
                and ev.producer is not None and ev.producer not in FAITHFULNESS_PRODUCERS):
            raise TrustViolation(
                f"mechanical faithfulness edge produced by {ev.producer!r}, which is not an "
                f"operator-admitted faithfulness producer (ADR 0041); a tool or built checker cannot "
                f"earn a faithfulness edge without operator registration in FAITHFULNESS_PRODUCERS"
            )

    def validate_path(self, edges: Iterable[EdgeEvidence]) -> None:
        """Raise unless this is an admissible promotion path."""
        edges = list(edges)
        by_edge = {e.edge: e for e in edges}

        if PROOF_EDGE not in by_edge:
            raise TrustViolation("no proof edge present; cannot promulgate")
        for ev in edges:
            self.validate_edge(ev)
            if ev.verdict is not Verdict.PASS:
                raise TrustViolation(
                    f"edge {ev.edge!r} did not PASS ({ev.verdict.value})"
                )

        faith = by_edge.get(FAITHFULNESS_EDGE)
        if faith is None:
            raise TrustViolation("no faithfulness edge present; cannot promulgate")
        # JUDGED faithfulness is *allowed* but flagged for the budget tracker.

    @staticmethod
    def is_judged_faithfulness(edges: Iterable[EdgeEvidence]) -> bool:
        for e in edges:
            if e.edge == FAITHFULNESS_EDGE:
                return e.tier is TrustTier.JUDGED
        return False

    def admits_judged_faithfulness(self, judged_count: int, total_count: int) -> bool:
        """Whether admitting ONE more JUDGED-faithfulness promulgation keeps the
        residual within budget (ADR 0001 §5): ``(judged+1)/(total+1) <= max``.

        Pure and separate from ``validate_path`` (which must still admit a lone
        judged edge for invariant 5). Stateful counting lives in
        ``leibniz.budget.TrustBudget``; this is just the policy arithmetic. The
        first judged promulgation on an empty ledger is refused (1/1 > 0.15), so
        judged faithfulness is admitted only once the ledger is large enough to
        keep it under budget."""
        return (judged_count + 1) <= self.max_judged_faithfulness_fraction * (total_count + 1)

"""The discovery frontier (ADR 0018) — steering conjecture toward the band of the
*novel-yet-tractable*.

The daemon runs end-to-end but rarely promulgates: conjectures land trivial (killed
by the novelty / decision-procedure gates) or too hard (the prover exhausts its
budget, UNPROVEN). ADR 0009 closed the learning loop on the *selection* side (KFM
recombines survivors); this closes it on the *proposal* side, where the text is
actually generated.

Everything here is **proposal-side** and writes no trust edge: it shapes what the
conjecturer is asked, scores stepping stones, and proposes weaker reformulations —
but every candidate it influences still runs the full cheap gates and the kernel's
N+1 consensus. The kernel and Z3 still decide; the trust boundary is untouched.

Pieces:
- ``difficulty`` — a mechanical structural proxy in [0,1] (quantifiers, implication
  depth, operators, length). No LLM.
- ``DiscoveryNotebook`` — a bounded, rolling memory of recent *outcomes* distilled
  into a steering block: proven shapes to emulate, trivial/known shapes to avoid,
  too-hard shapes to weaken.
- ``FrontierController`` — a thermostat: it nudges a target difficulty band from the
  recent proof-success rate (a curriculum — ease off when nothing proves, push when
  everything is trivial).
- ``weakening_seeds`` — turn UNPROVEN near-misses into strictly-weaker re-conjecture
  seeds (lemma mining), fed back through the same gated pipeline.
- ``quality`` — a graded stepping-stone score so a near-tractable miss outranks a
  wild one.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from leibniz.propositio import Propositio
from leibniz.types import FinishReason

# Outcomes that mean "do not propose shapes like this again" (dead ends).
_AVOID = frozenset({
    FinishReason.KNOWN, FinishReason.TRIVIAL, FinishReason.REFUTED,
    FinishReason.GAMED, FinishReason.UNFAITHFUL, FinishReason.MALFORMED,
})

_QUANTIFIERS = ("forall", "∀", "exists", "∃")
_IMPLIES = ("->", "→", "↔", "<->")
_OPERATORS = ("+", "*", "^", "<=", "≤", ">=", "≥", "<", ">", "%", "/", "∑", "∏", "∫")


def _statement_src(prop: Propositio) -> str:
    """The most formal text available — the Lean statement if formalized, else the
    human claim (difficulty is well-defined even for early-quarantined candidates)."""
    if prop.expressio and prop.expressio.theorem_src:
        return prop.expressio.theorem_src
    return prop.enuntiatio.statement if prop.enuntiatio else ""


def difficulty(prop: Propositio) -> float:
    """A mechanical, pre-proof structural difficulty proxy in [0, 1].

    Not a truth — a cheap proxy good enough to *target a band* and to *grade*
    stepping stones. Combines quantifier count, implication depth, operator
    density, and length. Deterministic; no LLM."""
    src = _statement_src(prop)
    if not src:
        return 0.0
    quant = sum(src.count(q) for q in _QUANTIFIERS)
    impl = sum(src.count(i) for i in _IMPLIES)
    ops = sum(src.count(o) for o in _OPERATORS)
    length = min(1.0, len(src) / 200.0)
    raw = (
        0.30 * min(1.0, quant / 3.0)
        + 0.25 * min(1.0, impl / 3.0)
        + 0.20 * min(1.0, ops / 8.0)
        + 0.25 * length
    )
    return round(min(0.999, raw), 3)


def quality(prop: Propositio) -> float:
    """Graded archive quality (replaces the coarse {1.0, 0.5, 0.0}).

    A promulgated law is 1.0. A faithful-but-unproven stepping stone is graded by
    how *close to tractable* it looks — a near-miss (low difficulty, yet the prover
    failed) is a more promising parent than a wild open-problem shape, so it scores
    higher. Dead ends are 0.0."""
    if prop.promulgated or prop.finish_reason is FinishReason.PROMULGATED:
        return 1.0
    if prop.finish_reason is FinishReason.UNPROVEN:
        # Peak at a MODERATE (frontier) difficulty, falling off toward both extremes:
        # a genuine near-miss outranks BOTH a vacuous trivially-shaped statement and a
        # wild open-problem shape. (Plain `1 - difficulty` rewarded simpler text, so a
        # near-vacuous statement could outrank a real near-miss — ADR 0018 review.)
        # Always in 0.40–0.60, strictly below a real proof's 1.0.
        peak = 0.45
        closeness = 1.0 - abs(difficulty(prop) - peak) / max(peak, 1.0 - peak)
        return round(0.40 + 0.20 * max(0.0, closeness), 3)
    return 0.0


@dataclass
class DiscoveryNotebook:
    """A bounded, rolling memory of recent outcomes, distilled into a steering block
    the conjecturer is given as context. Proposal-side only."""

    capacity: int = 6
    proven: list[str] = field(default_factory=list)    # emulate these shapes
    too_hard: list[str] = field(default_factory=list)  # weaken these
    avoid: list[str] = field(default_factory=list)     # don't re-propose these

    @staticmethod
    def _push(bucket: list[str], item: str, cap: int) -> None:
        item = (item or "").strip()
        if not item or item in bucket:
            return
        bucket.append(item)
        del bucket[:-cap]  # keep only the most recent `cap`

    def record(self, prop: Propositio, reason: FinishReason | None = None) -> None:
        stmt = prop.enuntiatio.statement if prop.enuntiatio else ""
        if not stmt:
            return
        # The daemon resolves an absent finish_reason to UNPROVEN for the cycle; honour
        # that resolution here so a reached-but-unproven candidate is mined, not lost.
        r = reason if reason is not None else prop.finish_reason
        de = prop.demonstratio
        kernel_proved = bool(de and de.kernel_verified)
        # A kernel-proved shape is a *tractable* shape to emulate — even if it was held
        # back at promotion (OVER_BUDGET): the proof was real, only the judged-
        # faithfulness budget refused it (ADR 0018 review).
        if kernel_proved or prop.promulgated or r is FinishReason.PROMULGATED:
            self._push(self.proven, stmt, self.capacity)
        elif r is FinishReason.UNPROVEN:
            self._push(self.too_hard, stmt, self.capacity)
        elif r in _AVOID:
            self._push(self.avoid, stmt, self.capacity)

    def steering(self) -> str:
        """A compact instruction block for the CONJECTURE prompt. Empty until there
        is something to learn from (so a cold start is unchanged)."""
        lines: list[str] = []
        if self.proven:
            lines.append("Recently PROVEN here (emulate this shape/difficulty): "
                         + "; ".join(self.proven[-3:]))
        if self.avoid:
            lines.append("Recently TRIVIAL or already KNOWN (do NOT re-propose these "
                         "or close variants): " + "; ".join(self.avoid[-3:]))
        if self.too_hard:
            lines.append("Recently TOO HARD to prove (propose something in reach, or a "
                         "weaker cousin): " + "; ".join(self.too_hard[-3:]))
        return ("Lessons from the ledger so far:\n- " + "\n- ".join(lines)) if lines else ""


@dataclass
class FrontierController:
    """A thermostat on conjecture difficulty: a curriculum holding a target proof-
    SUCCESS RATE. It steers the proposal band so the tractable tail of the cloud
    overlaps the prover's (unknown) reach — it does not claim to centre on it.

    Two robustness properties beyond a plain deadband (ADR 0018 review):
    - PROPORTIONAL homing: the step shrinks as the success rate nears the aim, so it
      settles smoothly instead of freezing at the first in-band rate or oscillating.
    - RE-EXPLORATION: if it pins a bound with zero success (a narrow window was
      overshot), it jumps to the opposite half and searches again — it never stays
      stuck at the floor forever.
    Proposal-side only; the band is just context for the conjecturer."""

    target: float = 0.45          # band centre in [0,1]
    window: int = 8               # outcomes considered
    aim: float = 0.35             # desired proof-success rate (exploration setpoint)
    gain: float = 0.30            # proportional gain on the rate error
    floor: float = 0.15
    ceil: float = 0.85
    _recent: list[bool] = field(default_factory=list)
    _jumps: int = 0

    def record(self, proved: bool) -> None:
        self._recent.append(bool(proved))
        del self._recent[:-self.window]

    def success_rate(self) -> float:
        return (sum(self._recent) / len(self._recent)) if self._recent else 0.0

    def update(self) -> None:
        """Retune the target from the recent success rate. Acts only on a full enough
        window so it doesn't lurch on one outcome."""
        if len(self._recent) < max(3, self.window // 2):
            return
        rate = self.success_rate()
        at_floor = self.target <= self.floor + 1e-9
        at_ceil = self.target >= self.ceil - 1e-9
        # Re-exploration: pinned at a bound with nothing proving -> the tractable band
        # was overshot. Jump to the opposite half, nudged by a deterministic offset that
        # varies per jump so successive sweeps probe different alignments and a narrow
        # window is eventually straddled (no permanent pin, no limit cycle).
        if rate == 0.0 and (at_floor or at_ceil):
            self._jumps += 1
            base = 0.65 if at_floor else 0.35
            jitter = (0.0, 0.08, -0.08, 0.04, -0.04)[self._jumps % 5]
            self.target = round(min(self.ceil, max(self.floor, base + jitter)), 3)
            self._recent.clear()
            return
        # Proportional homing: rate below aim (too hard) -> easier; above -> harder.
        err = self.aim - rate
        if abs(err) > 0.05:
            self.target = round(min(self.ceil, max(self.floor, self.target - self.gain * err)), 3)

    def band(self) -> str:
        lo, hi = max(0.0, self.target - 0.12), min(1.0, self.target + 0.12)
        return (f"Aim for difficulty ~{self.target:.2f} (band {lo:.2f}–{hi:.2f}; "
                "0 = decidable triviality, 1 = open problem). Prefer claims provable "
                "by standard Mathlib tactics.")


_WEAKEN_MARK = "STRICTLY WEAKER"


def weakening_seeds(statements: list[str], k: int = 2) -> list[str]:
    """Turn UNPROVEN near-misses into strictly-weaker re-conjecture seeds (lemma
    mining). Each weakened variant still runs the full novelty/faithfulness gates and
    the kernel — a trivial weakening is caught, a provable non-trivial one is a real
    (if modest) discovery and a stepping stone.

    Depth-1 bound (ADR 0018 review): never weaken a statement that already carries the
    weakening instruction. This terminates the chain — a weakening of a weakening is
    not re-weakened — and kills the compounding loop a verbatim-echoing provider could
    otherwise drive."""
    fresh = [s for s in statements if _WEAKEN_MARK not in s]
    return [
        f"Propose a {_WEAKEN_MARK} but still non-trivial and novel variant of this "
        "claim that is more likely provable — add a hypothesis, specialize a "
        f"variable, or bound a quantifier: {s}"
        for s in fresh[:k]
    ]


def steer(seed: str, notebook: DiscoveryNotebook | None, frontier: FrontierController | None) -> str:
    """Compose the conjecture context: the raw seed plus any ledger lessons and the
    target difficulty band. Returns the seed unchanged when there is nothing to add
    (cold start), so behaviour is identical until the daemon has learned something."""
    parts = [p for p in (
        notebook.steering() if notebook else "",
        frontier.band() if frontier else "",
    ) if p]
    if not parts:
        return seed
    return "\n\n".join(parts) + f"\n\nSeed: {seed}"

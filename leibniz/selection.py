"""Selection -- KFM as a quality-diversity operator over the conjecture archive.

KFM's Kill / Fuck / Marry dynamics map onto open-ended discovery:

    Kill   -- refuted/trivial/known conjectures leave the population (quarantined).
    Fuck   -- promising-but-unproven conjectures are recombined into children
              (LLM-as-variation-operator; lineage tracked).
    Marry  -- proven-and-novel conjectures are committed to the Codex.

The archive is MAP-Elites-shaped: it keeps the best conjecture per cell of a
behavior space, so the search retains *diverse* stepping stones. R5 makes the
descriptor real (D8: sub-area x proof technique x statement complexity), biases
parent sampling toward sparse cells (curiosity), and recombines parent features.
"""
from __future__ import annotations

import hashlib
import itertools
from dataclasses import dataclass, field
from enum import Enum

from leibniz.propositio import Propositio
from leibniz.types import FinishReason

# Proof techniques we recognize, ordered so the descriptor axis is stable.
_TACTICS = ("induction", "ring", "omega", "linarith", "nlinarith", "aesop", "simp", "decide")


def _unit_hash(s: str) -> float:
    """Stable mapping of a categorical string into [0, 1)."""
    h = int(hashlib.sha256(s.encode()).hexdigest()[:8], 16)
    return (h % 10_000) / 10_000.0


def descriptor(prop: Propositio) -> tuple[float, float, float]:
    """The 3-axis behavior descriptor (D8): sub-area x technique x complexity.

    Derived from whatever the Propositio carries; safe on early-quarantined
    candidates (no expressio/demonstratio)."""
    en = prop.enuntiatio
    subject = (prop.signature.subject if prop.signature
               else (en.statement.split()[0] if en.statement else "?"))
    sub_area = _unit_hash(f"{en.claim_type.value}:{subject}")

    technique = 0.5  # neutral until a proof is drafted
    proof = prop.demonstratio.proof_src if prop.demonstratio else None
    if proof:
        hit = next((t for t in _TACTICS if t in proof), None)
        technique = ((_TACTICS.index(hit) + 1) / (len(_TACTICS) + 1)) if hit else _unit_hash(proof)

    src = prop.expressio.theorem_src if prop.expressio else en.statement
    complexity = min(0.999, len(src) / 240.0)
    return (sub_area, technique, complexity)


class Disposition(Enum):
    KILL = "kill"
    RECOMBINE = "recombine"   # the 'fuck' edge, named for polite log files
    COMMIT = "commit"         # 'marry'


@dataclass
class Elite:
    """The best Propositio in a cell, with its quality (no dynamic attrs on prop)."""

    prop: Propositio
    quality: float


@dataclass
class Archive:
    """A MAP-Elites grid keyed by discretized behavior descriptor -> Elite."""

    cells: dict[tuple[int, ...], Elite] = field(default_factory=dict)
    resolution: int = 8
    dims: int = 3

    def _cell(self, bd: tuple[float, ...]) -> tuple[int, ...]:
        bd = bd or (0.0,) * self.dims
        return tuple(min(self.resolution - 1, max(0, int(x * self.resolution))) for x in bd)

    def consider(self, prop: Propositio, quality: float) -> bool:
        """Insert if this beats the current elite in its cell. Returns True if kept."""
        key = self._cell(prop.behavior_descriptor)
        cur = self.cells.get(key)
        if cur is None or quality > cur.quality:
            self.cells[key] = Elite(prop, quality)
            return True
        return False

    def elites(self) -> list[Propositio]:
        return [e.prop for e in self.cells.values()]

    def coverage(self) -> float:
        """Fraction of the behavior grid that is occupied (over the FULL grid)."""
        return len(self.cells) / float(self.resolution ** self.dims)

    def neighbor_count(self, key: tuple[int, ...]) -> int:
        """Occupied cells within Chebyshev distance 1 (excluding the cell itself)."""
        ranges = [range(max(0, c - 1), min(self.resolution, c + 2)) for c in key]
        return sum(1 for nb in itertools.product(*ranges) if nb != key and nb in self.cells)


@dataclass
class KFM:
    """Selection policy over the archive."""

    archive: Archive

    def disposition(self, prop: Propositio) -> Disposition:
        if prop.finish_reason in {
            FinishReason.REFUTED,
            FinishReason.TRIVIAL,
            FinishReason.KNOWN,
            FinishReason.GAMED,
            FinishReason.UNFAITHFUL,
            FinishReason.MALFORMED,
            FinishReason.OVER_BUDGET,
        }:
            return Disposition.KILL
        if prop.promulgated:
            return Disposition.COMMIT
        return Disposition.RECOMBINE  # unproven but not dead -> a stepping stone

    def _curiosity(self, key: tuple[int, ...], elite: Elite) -> tuple[float, float]:
        # Sparser neighbourhood first (push the frontier), quality as tie-break.
        return (1.0 / (1.0 + self.archive.neighbor_count(key)), elite.quality)

    def select_parents(self, k: int = 2) -> list[Propositio]:
        """Curiosity-biased parent sampling: prefer elites in sparse regions of the
        archive to push the frontier outward rather than re-mining a crowded cell."""
        ranked = sorted(
            self.archive.cells.items(),
            key=lambda kv: self._curiosity(kv[0], kv[1]),
            reverse=True,
        )
        return [elite.prop for _, elite in ranked[:k]]

    def recombine(self, a: Propositio, b: Propositio) -> str:
        """The 'fuck' edge: a seed/context that genuinely combines two parents'
        features for the next cycle's CONJECTURE. Lineage is tracked by the caller
        via the child's ``parents`` tuple."""
        return (
            "Synthesize a new conjecture combining features of two stepping stones. "
            f"(A) {a.enuntiatio.statement} [{a.enuntiatio.claim_type.value}]; "
            f"(B) {b.enuntiatio.statement} [{b.enuntiatio.claim_type.value}]."
        )

"""Selection -- KFM as a quality-diversity operator over the conjecture archive.

KFM's Kill / Fuck / Marry selection dynamics map onto open-ended discovery:

    Kill   -- refuted, trivial, or already-known conjectures leave the population
              (but are quarantined, not deleted).
    Fuck   -- promising-but-unproven conjectures are recombined/mutated to produce
              children (LLM-as-variation-operator, lineage tracked).
    Marry  -- proven-and-novel conjectures are committed to the Codex.

The archive is MAP-Elites-shaped: rather than optimizing one objective, it keeps
the best conjecture in each cell of a behavior space, so the search retains
*diverse* stepping stones and does not collapse toward a single target. The
behavior descriptor (what makes two conjectures 'different kinds') is the key
design knob; sensible axes for analysis-of-algorithms include the mathematical
sub-area, the proof technique, and the structural complexity of the statement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from leibniz.propositio import Propositio
from leibniz.types import FinishReason


class Disposition(Enum):
    KILL = "kill"
    RECOMBINE = "recombine"   # the 'fuck' edge, named for polite log files
    COMMIT = "commit"         # 'marry'


@dataclass
class Archive:
    """A MAP-Elites grid keyed by discretized behavior descriptor -> best elite."""

    cells: dict[tuple[int, ...], Propositio] = field(default_factory=dict)
    resolution: int = 8

    def _cell(self, bd: tuple[float, ...]) -> tuple[int, ...]:
        return tuple(min(self.resolution - 1, int(x * self.resolution)) for x in bd)

    def consider(self, prop: Propositio, quality: float) -> bool:
        """Insert if this beats the current elite in its cell. Returns True if kept."""
        key = self._cell(prop.behavior_descriptor or (0.0,))
        cur = self.cells.get(key)
        if cur is None or quality > _quality_of(cur):
            prop._quality = quality  # type: ignore[attr-defined]
            self.cells[key] = prop
            return True
        return False

    def elites(self) -> list[Propositio]:
        return list(self.cells.values())

    def coverage(self) -> float:
        return len(self.cells) / float(self.resolution ** 1)


def _quality_of(prop: Propositio) -> float:
    return getattr(prop, "_quality", 0.0)


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
        }:
            return Disposition.KILL
        if prop.promulgated:
            return Disposition.COMMIT
        return Disposition.RECOMBINE  # unproven but not dead -> a stepping stone

    def select_parents(self, k: int = 2) -> list[Propositio]:
        """Curiosity-biased parent sampling: prefer sparse regions of the archive
        to push the frontier outward rather than re-mining a crowded cell."""
        elites = sorted(self.archive.elites(), key=_quality_of, reverse=True)
        return elites[:k]

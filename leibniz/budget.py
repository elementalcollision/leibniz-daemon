"""Judged-faithfulness budget (R2c) — the stateful counter behind ADR 0001 §5.

`TrustPolicy` declares `max_judged_faithfulness_fraction` and the pure arithmetic
(`admits_judged_faithfulness`); this holds the running counts and decides, at
promotion time, whether a JUDGED-faithfulness law may enter the ledger.

- A fully-mechanical promulgation is always admitted.
- A JUDGED-faithfulness promulgation is admitted only while it keeps the residual
  within budget; otherwise it is **refused and not recorded**, and the daemon
  quarantines the candidate `OVER_BUDGET` (never deleted).

This is the enforcement the plan review flagged as missing: the 0.15 bound was
declared but never counted. It is stateful, so it lives here rather than in the
pure `validate_path` (which must still admit a lone judged edge for invariant 5).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from leibniz.trust import TrustPolicy
from leibniz.types import EdgeEvidence


@dataclass
class TrustBudget:
    policy: TrustPolicy
    total: int = 0
    judged: int = 0

    def fraction(self) -> float:
        return (self.judged / self.total) if self.total else 0.0

    def try_admit(self, edges: Iterable[EdgeEvidence]) -> bool:
        """Record a promulgation and return whether it is admitted."""
        edges = list(edges)
        if not TrustPolicy.is_judged_faithfulness(edges):
            self.total += 1
            return True
        if self.policy.admits_judged_faithfulness(self.judged, self.total):
            self.judged += 1
            self.total += 1
            return True
        return False  # refused -> not recorded; caller quarantines OVER_BUDGET

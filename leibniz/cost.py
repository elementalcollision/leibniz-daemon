"""USD budget guard (ADR 0011 — cost governance).

The N+1 consensus + multi-prover + repair path is deliberately costly ("even if
costly"), so a sustained autonomous run needs a ceiling. This is a *coarse* guard:
it estimates spend from per-cycle call counts (the daemon does not yet collect real
token usage from providers — that is the precise follow-up) and stops the loop once
a configured cap is reached. A cap of 0 means unlimited.

Mirrors Leonardo's LEONARDO_DAILY_USD_CAP; configured via LEIBNIZ_DAILY_USD_CAP.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class CostBudget:
    cap_usd: float = 0.0            # 0 -> unlimited
    per_call_usd: float = 0.01      # rough average cost of one LLM call
    spent_usd: float = 0.0
    calls: int = 0

    @classmethod
    def from_env(cls) -> "CostBudget":
        return cls(
            cap_usd=float(os.environ.get("LEIBNIZ_DAILY_USD_CAP", "0") or 0),
            per_call_usd=float(os.environ.get("LEIBNIZ_PER_CALL_USD", "0.01") or 0.01),
        )

    def record_calls(self, n: int) -> None:
        self.calls += n
        self.spent_usd += n * self.per_call_usd

    def exhausted(self) -> bool:
        return self.cap_usd > 0 and self.spent_usd >= self.cap_usd

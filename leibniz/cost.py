"""USD budget guard (ADR 0011 cost governance; ADR 0014 real token accounting).

The N+1 consensus + multi-prover + repair path is deliberately costly ("even if
costly"), so a sustained autonomous run needs a ceiling. Two accounting modes:

- **Real (ADR 0014):** providers meter their actual token usage into
  ``record_usage(model, in, out)``, priced through ``leibniz.pricing``. This is
  exact and is what the live assembly uses.
- **Coarse (ADR 0011 fallback):** ``record_calls(n)`` estimates from a flat
  per-call average. Used only when no real usage is flowing (the deterministic
  fakes / demo). It **no-ops once real usage has been recorded**, so wiring the
  meter never double-counts on top of the daemon's coarse per-cycle estimate.

A cap of 0 means unlimited. Configured via LEIBNIZ_DAILY_USD_CAP (mirrors
Leonardo's LEONARDO_DAILY_USD_CAP). This is cost governance, never a verdict.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from leibniz.pricing import estimate_usd


@dataclass
class CostBudget:
    cap_usd: float = 0.0            # 0 -> unlimited
    per_call_usd: float = 0.01      # rough average cost of one LLM call (coarse mode)
    spent_usd: float = 0.0
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    _real: bool = False             # True once a provider has metered real usage

    @classmethod
    def from_env(cls) -> "CostBudget":
        return cls(
            cap_usd=float(os.environ.get("LEIBNIZ_DAILY_USD_CAP", "0") or 0),
            per_call_usd=float(os.environ.get("LEIBNIZ_PER_CALL_USD", "0.01") or 0.01),
        )

    def record_usage(self, model: str, input_tokens: int, output_tokens: int) -> None:
        """ADR 0014: account one real provider call by its measured token usage."""
        self._real = True
        self.calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.spent_usd += estimate_usd(model, input_tokens, output_tokens)

    def record_calls(self, n: int) -> None:
        """Coarse fallback. No-op once real usage is being metered (avoids
        double-counting the daemon's per-cycle estimate over real provider spend)."""
        if self._real:
            return
        self.calls += n
        self.spent_usd += n * self.per_call_usd

    def exhausted(self) -> bool:
        return self.cap_usd > 0 and self.spent_usd >= self.cap_usd

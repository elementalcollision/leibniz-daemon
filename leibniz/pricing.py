"""Model price table for real (token-based) cost accounting (ADR 0014).

USD per *million* tokens, (input, output), as configured by the operator. The
daemon meters real token usage from the providers (ADR 0014) and converts it to
spend through this table; unknown models fall back to ``DEFAULT_PRICE`` so a new
prover never silently bills at $0. Prices change — keep this table the single
place to edit, or override per-model via ``LEIBNIZ_PRICE_<...>`` (see below).

This is cost *governance* input, not a trust surface: it only sizes the budget
cap, never a verdict.
"""
from __future__ import annotations

import os

# (input_per_mtok, output_per_mtok) in USD. Approximate list prices; operator-tunable.
PRICES: dict[str, tuple[float, float]] = {
    # Anthropic (conjecture / formalize)
    "claude-opus-4-8": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    # OpenRouter prover ensemble (representative ids; extend as the ensemble changes)
    "deepseek/deepseek-prover-v2": (0.5, 2.0),
    "deepseek/deepseek-chat": (0.3, 1.2),
    "anthropic/claude-opus-4": (15.0, 75.0),
    "anthropic/claude-sonnet-4": (3.0, 15.0),
}

# Conservative fallback for an unconfigured model — bills, never free.
DEFAULT_PRICE: tuple[float, float] = (10.0, 30.0)


def _env_override(model: str) -> tuple[float, float] | None:
    """Per-model override via env: LEIBNIZ_PRICE_<SANITIZED>=<in>,<out> ($/Mtok).
    SANITIZED upper-cases the id and replaces non-alnum with '_'."""
    key = "LEIBNIZ_PRICE_" + "".join(c if c.isalnum() else "_" for c in model).upper()
    raw = os.environ.get(key)
    if not raw:
        return None
    try:
        a, b = (float(x) for x in raw.split(",", 1))
        return (a, b)
    except (ValueError, TypeError):
        return None


def price_for(model: str) -> tuple[float, float]:
    return _env_override(model) or PRICES.get(model, DEFAULT_PRICE)


def estimate_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """USD cost of one call given its measured token usage."""
    pin, pout = price_for(model)
    return (input_tokens * pin + output_tokens * pout) / 1_000_000.0

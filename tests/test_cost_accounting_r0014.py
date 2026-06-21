"""ADR 0014: real token-based cost accounting (CI-safe; no network)."""
from __future__ import annotations

from leibniz.cost import CostBudget
from leibniz.pricing import DEFAULT_PRICE, estimate_usd, price_for
from leibniz.providers.anthropic_provider import AnthropicProvider
from leibniz.providers.openrouter_provider import OpenRouterProvider


# --- pricing -----------------------------------------------------------------

def test_estimate_usd_uses_per_mtok_rates():
    # claude-opus-4-8 = (15, 75) $/Mtok -> 1M in + 1M out = 15 + 75
    assert estimate_usd("claude-opus-4-8", 1_000_000, 1_000_000) == 90.0


def test_unknown_model_falls_back_to_default_price():
    assert price_for("totally-unknown-model") == DEFAULT_PRICE  # bills, never free


def test_env_override_beats_table(monkeypatch):
    monkeypatch.setenv("LEIBNIZ_PRICE_CLAUDE_OPUS_4_8", "1.0,2.0")
    assert price_for("claude-opus-4-8") == (1.0, 2.0)


# --- CostBudget real accounting ----------------------------------------------

def test_record_usage_accumulates_real_spend_and_tokens():
    b = CostBudget(cap_usd=0.0)
    b.record_usage("claude-opus-4-8", 1000, 1000)  # 1000*15/1e6 + 1000*75/1e6
    assert b.calls == 1
    assert b.input_tokens == 1000 and b.output_tokens == 1000
    assert round(b.spent_usd, 6) == 0.09


def test_record_calls_noops_once_real_usage_seen():
    """Wiring the meter must not double-count on top of the daemon's coarse
    per-cycle record_calls estimate."""
    b = CostBudget(per_call_usd=0.01)
    b.record_usage("claude-opus-4-8", 1000, 1000)
    before = b.spent_usd
    b.record_calls(100)  # would add 1.0 in coarse mode
    assert b.spent_usd == before  # no-op: real usage is authoritative


def test_record_calls_still_works_without_real_usage():
    b = CostBudget(cap_usd=0.05, per_call_usd=0.01)
    b.record_calls(5)
    assert b.spent_usd == 0.05 and b.exhausted() is True


def test_real_usage_can_exhaust_cap():
    b = CostBudget(cap_usd=0.00005)
    assert b.exhausted() is False
    b.record_usage("claude-opus-4-8", 1000, 1000)  # 0.00009 >= 0.00005
    assert b.exhausted() is True


# --- providers report usage into the meter (no network) ----------------------

class _Usage:
    input_tokens = 200
    output_tokens = 50


class _Msg:
    usage = _Usage()


def test_anthropic_provider_meters_usage():
    b = CostBudget()
    AnthropicProvider(model="claude-opus-4-8", meter=b)._meter(_Msg())
    assert b.calls == 1 and b.input_tokens == 200 and b.output_tokens == 50


def test_openrouter_provider_meters_usage():
    b = CostBudget()
    data = {"usage": {"prompt_tokens": 300, "completion_tokens": 90}}
    OpenRouterProvider(model="deepseek/deepseek-prover-v2", meter=b)._meter(data)
    assert b.calls == 1 and b.input_tokens == 300 and b.output_tokens == 90


def test_metering_is_optional_and_safe_without_meter():
    AnthropicProvider(model="claude-opus-4-8")._meter(_Msg())  # meter=None -> no-op
    OpenRouterProvider(model="x")._meter({})  # missing usage -> no crash

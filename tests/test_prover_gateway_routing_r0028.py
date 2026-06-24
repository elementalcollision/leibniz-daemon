"""Per-model gateway routing for the prover ensemble (ADR 0028 lever 3).

A `LEIBNIZ_PROVER_MODELS` entry may be `model@gateway` to route that one model through a named
gateway (e.g. Goedel-Prover-V2 on Featherless's flat-rate plan) while the rest stay on the
default gateway (OpenRouter). The load-bearing trust property: routing is a transport detail —
N+1 consensus keys identity on the model NAME, so the same model via two gateways is still ONE
voter, and the Lean kernel still re-verifies every draft. CI-safe (no network — providers are
constructed lazily). NOT in test_invariants.py (no trust-edge change).
"""
from __future__ import annotations

import pytest

from leibniz.assembly import _resolve_prover, prover_ensemble
from leibniz.consensus import _prover_identity
from leibniz.providers import ProviderUnavailable
from leibniz.providers.openrouter_provider import OPENROUTER_URL

_DEF_URL = OPENROUTER_URL
_DEF_KEY = "OPENROUTER_API_KEY"


def _resolve(spec):
    return _resolve_prover(spec, _DEF_URL, _DEF_KEY, meter=None, max_tok=2048)


def test_bare_model_uses_default_gateway(monkeypatch):
    monkeypatch.delenv("LEIBNIZ_GATEWAY_FEATHERLESS_URL", raising=False)
    p = _resolve("deepseek/deepseek-prover-v2")
    assert p.model == "deepseek/deepseek-prover-v2"
    assert p.url == _DEF_URL and p.api_key_env == _DEF_KEY


def test_at_gateway_routes_to_named_profile(monkeypatch):
    monkeypatch.setenv("LEIBNIZ_GATEWAY_FEATHERLESS_URL", "https://api.featherless.ai/v1/chat/completions")
    p = _resolve("Goedel-LM/Goedel-Prover-V2-32B@featherless")
    assert p.model == "Goedel-LM/Goedel-Prover-V2-32B"          # the @gateway is stripped from the model id
    assert p.url == "https://api.featherless.ai/v1/chat/completions"
    assert p.api_key_env == "FEATHERLESS_API_KEY"               # default <GATEWAY>_API_KEY


def test_gateway_key_env_is_overridable(monkeypatch):
    monkeypatch.setenv("LEIBNIZ_GATEWAY_FEATHERLESS_URL", "https://x")
    monkeypatch.setenv("LEIBNIZ_GATEWAY_FEATHERLESS_KEY_ENV", "MY_FEATHERLESS_TOKEN")
    assert _resolve("m@featherless").api_key_env == "MY_FEATHERLESS_TOKEN"


def test_unconfigured_gateway_fails_closed(monkeypatch):
    monkeypatch.delenv("LEIBNIZ_GATEWAY_NOPE_URL", raising=False)
    with pytest.raises(ProviderUnavailable, match="LEIBNIZ_GATEWAY_NOPE_URL"):
        _resolve("some/model@nope")        # a typo'd/unset gateway must NOT silently route elsewhere


def test_same_model_via_two_gateways_is_one_voter(monkeypatch):
    # THE trust-critical property: routing is transport, not identity. deepseek on OpenRouter and
    # deepseek on Featherless must still collapse to ONE N+1 voter (cannot self-satisfy consensus).
    monkeypatch.setenv("LEIBNIZ_GATEWAY_FEATHERLESS_URL", "https://x")
    a = _resolve("deepseek/deepseek-prover-v2")
    b = _resolve("deepseek/deepseek-prover-v2@featherless")
    assert _prover_identity(a) == _prover_identity(b) == "model:deepseek/deepseek-prover-v2"


def test_distinct_models_are_distinct_voters(monkeypatch):
    monkeypatch.setenv("LEIBNIZ_GATEWAY_FEATHERLESS_URL", "https://x")
    deepseek = _resolve("deepseek/deepseek-prover-v2")
    goedel = _resolve("Goedel-LM/Goedel-Prover-V2-32B@featherless")
    assert _prover_identity(deepseek) != _prover_identity(goedel)


def test_ensemble_spans_gateways_with_correct_identities(monkeypatch):
    # The A/B arm B: deepseek (OpenRouter) + Goedel (Featherless) + opus (OpenRouter) = 3 distinct.
    monkeypatch.setenv("LEIBNIZ_GATEWAY_FEATHERLESS_URL", "https://api.featherless.ai/v1/chat/completions")
    monkeypatch.delenv("LEIBNIZ_HF_PROVER_MODELS", raising=False)
    monkeypatch.setenv(
        "LEIBNIZ_PROVER_MODELS",
        "deepseek/deepseek-prover-v2,Goedel-LM/Goedel-Prover-V2-32B@featherless,anthropic/claude-opus-4-8",
    )
    monkeypatch.setenv("LEIBNIZ_DECOMPOSE", "0")   # isolate the base ensemble
    monkeypatch.delenv("LEIBNIZ_ARISTOTLE", raising=False)
    ens = prover_ensemble()
    assert len(ens) == 3
    by_model = {p.model: p.url for p in ens}
    assert by_model["Goedel-LM/Goedel-Prover-V2-32B"].endswith("featherless.ai/v1/chat/completions")
    assert by_model["deepseek/deepseek-prover-v2"] == _DEF_URL          # default gateway
    assert by_model["anthropic/claude-opus-4-8"] == _DEF_URL
    assert len({_prover_identity(p) for p in ens}) == 3                  # 3 DISTINCT voters


def test_ab_control_arm_dedups_to_two_voters(monkeypatch):
    # Arm A (control): deepseek twice + opus = 3 attempts but only 2 distinct voters.
    monkeypatch.delenv("LEIBNIZ_HF_PROVER_MODELS", raising=False)
    monkeypatch.setenv(
        "LEIBNIZ_PROVER_MODELS",
        "deepseek/deepseek-prover-v2,deepseek/deepseek-prover-v2,anthropic/claude-opus-4-8",
    )
    monkeypatch.setenv("LEIBNIZ_DECOMPOSE", "0")
    monkeypatch.delenv("LEIBNIZ_ARISTOTLE", raising=False)
    ens = prover_ensemble()
    assert len(ens) == 3                                                 # 3 draft attempts
    assert len({_prover_identity(p) for p in ens}) == 2                  # but 2 distinct voters

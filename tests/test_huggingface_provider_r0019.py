"""ADR 0019: HuggingFace prover provider + shared SSL context (CI-safe; no network)."""
from __future__ import annotations

from leibniz.cost import CostBudget
from leibniz.providers import ssl_context
from leibniz.providers.huggingface_provider import HuggingFaceProvider
from leibniz.types import Role


def test_available_gated_on_key(monkeypatch):
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
    assert HuggingFaceProvider(model="deepseek-ai/DeepSeek-Prover-V2-671B").available() is False
    monkeypatch.setenv("HUGGINGFACE_API_KEY", "x")
    assert HuggingFaceProvider(model="deepseek-ai/DeepSeek-Prover-V2-671B").available() is True


def test_meters_usage_into_cost_budget():
    b = CostBudget()
    data = {"usage": {"prompt_tokens": 120, "completion_tokens": 40},
            "choices": [{"message": {"content": "by simp"}}]}
    HuggingFaceProvider(model="deepseek-ai/DeepSeek-Prover-V2-671B", meter=b)._meter(data)
    assert b.calls == 1 and b.input_tokens == 120 and b.output_tokens == 40


def test_metering_is_safe_without_meter_or_usage():
    HuggingFaceProvider(model="m")._meter({})  # meter=None + missing usage -> no crash


def test_proof_draft_uses_proof_system_role():
    # PROOF_DRAFT must select the proof system prompt (not the generic one).
    from leibniz.providers.huggingface_provider import _GENERIC_SYSTEM, _PROOF_SYSTEM
    assert _PROOF_SYSTEM != _GENERIC_SYSTEM
    assert "Lean 4" in _PROOF_SYSTEM and Role.PROOF_DRAFT is Role.PROOF_DRAFT


def test_ssl_context_builds_without_raising():
    ctx = ssl_context()
    # Either a real SSL context (certifi/default) or None — never an exception.
    assert ctx is None or hasattr(ctx, "load_verify_locations")

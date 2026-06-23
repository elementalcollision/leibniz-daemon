"""R4: the production assembly wires the real stack (CI-safe; no network calls).

build_daemon() only constructs — it must not call out — so this runs in CI without
creds. The live end-to-end run lives in scripts/run_live.py.
"""
from __future__ import annotations

from leibniz.assembly import ConservativeJudge, build_daemon, prover_ensemble
from leibniz.budget import TrustBudget
from leibniz.consensus import ConsensusDemonstrate, NoOpDerive
from leibniz.daemon import Leibniz
from leibniz.gates.verification import VerificationGate
from leibniz.lemma_decomposition import DecomposingDemonstrate
from leibniz.runtime import PersistentRuntime


def test_build_daemon_constructs_real_stack_without_network():
    d = build_daemon(frontier_limit=1, analogy_limit=1)
    assert isinstance(d, Leibniz)
    assert isinstance(d.derive, NoOpDerive)
    # N+1 consensus proving — ADR 0027 wraps it with a decomposition fallback by default
    assert isinstance(d.demonstrate, (ConsensusDemonstrate, DecomposingDemonstrate))
    assert isinstance(d.budget, TrustBudget)                 # judged-faithfulness budget
    assert isinstance(d.runtime, PersistentRuntime)  # ADR 0016: real runtime, not the stub
    assert isinstance(d.verification, VerificationGate)


def test_prover_ensemble_parsed_from_env(monkeypatch):
    monkeypatch.setenv("LEIBNIZ_PROVER_MODELS", "a/b, c/d ,e/f")
    monkeypatch.setenv("LEIBNIZ_DECOMPOSE", "0")  # isolate model parsing (ADR 0024 variants off)
    assert [p.model for p in prover_ensemble()] == ["a/b", "c/d", "e/f"]


def test_prover_ensemble_empty_without_env(monkeypatch):
    monkeypatch.delenv("LEIBNIZ_PROVER_MODELS", raising=False)
    monkeypatch.delenv("LEIBNIZ_HF_PROVER_MODELS", raising=False)
    assert prover_ensemble() == []  # no base provers -> no decomposition variants either


def test_prover_base_url_and_key_env_are_configurable(monkeypatch):
    # harness A / lever 3: point the OpenAI-compatible client at a stronger model's gateway
    monkeypatch.delenv("LEIBNIZ_HF_PROVER_MODELS", raising=False)
    monkeypatch.setenv("LEIBNIZ_PROVER_MODELS", "Goedel-LM/Goedel-Prover-V2-32B")
    monkeypatch.setenv("LEIBNIZ_DECOMPOSE", "0")
    monkeypatch.setenv("LEIBNIZ_PROVER_BASE_URL", "https://api.featherless.ai/v1/chat/completions")
    monkeypatch.setenv("LEIBNIZ_PROVER_KEY_ENV", "FEATHERLESS_API_KEY")
    p = prover_ensemble()[0]
    assert p.model == "Goedel-LM/Goedel-Prover-V2-32B"
    assert p.url == "https://api.featherless.ai/v1/chat/completions"
    assert p.api_key_env == "FEATHERLESS_API_KEY"


def test_aristotle_appended_when_enabled(monkeypatch):
    # ADR 0028 (lever 3): LEIBNIZ_ARISTOTLE appends the Aristotle agent prover
    from leibniz.providers.aristotle_provider import AristotleProver
    monkeypatch.delenv("LEIBNIZ_HF_PROVER_MODELS", raising=False)
    monkeypatch.setenv("LEIBNIZ_PROVER_MODELS", "a/b")
    monkeypatch.setenv("LEIBNIZ_DECOMPOSE", "0")
    monkeypatch.setenv("LEIBNIZ_ARISTOTLE", "1")
    ens = prover_ensemble()
    assert any(isinstance(p, AristotleProver) for p in ens)
    monkeypatch.setenv("LEIBNIZ_ARISTOTLE", "0")  # off by default / explicitly
    assert not any(isinstance(p, AristotleProver) for p in prover_ensemble())


def test_repair_panel_wired_from_env(monkeypatch):
    # ADR 0029 v2: LEIBNIZ_REPAIR_PANEL builds distinct-model repairers, guarded by the key.
    from leibniz.proof_repair import RepairingDemonstrate
    monkeypatch.setenv("LEIBNIZ_PROOF_REPAIR", "1")
    monkeypatch.setenv("LEIBNIZ_REPAIR_PANEL", "openai/gpt-5.5, z-ai/glm-5.2")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")     # panel built only when a key is present
    d = build_daemon(frontier_limit=1, analogy_limit=1)
    assert isinstance(d.demonstrate, RepairingDemonstrate)
    assert [r.identity for r in d.demonstrate.panel] == ["repair:openai/gpt-5.5", "repair:z-ai/glm-5.2"]
    assert [r.provider.model for r in d.demonstrate.panel] == ["openai/gpt-5.5", "z-ai/glm-5.2"]


def test_repair_panel_empty_without_openrouter_key(monkeypatch):
    # no key -> no panel (safe degrade to the single-reasoner v1 path), no crash.
    from leibniz.proof_repair import RepairingDemonstrate
    monkeypatch.setenv("LEIBNIZ_PROOF_REPAIR", "1")
    monkeypatch.setenv("LEIBNIZ_REPAIR_PANEL", "openai/gpt-5.5")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    d = build_daemon(frontier_limit=1, analogy_limit=1)
    assert isinstance(d.demonstrate, RepairingDemonstrate) and d.demonstrate.panel == ()


def test_aristotle_is_a_stable_distinct_consensus_voter():
    # ADR 0028/0029: Aristotle is a real INDEPENDENT N+1 voter with a STABLE, readable
    # identity (not a per-instance obj:<id>), distinct from the base provers' model: ids.
    from leibniz.consensus import _prover_identity
    from leibniz.providers.aristotle_provider import AristotleProver
    from leibniz.providers.openrouter_provider import OpenRouterProvider
    a1, a2 = AristotleProver(), AristotleProver()
    assert _prover_identity(a1) == "model:harmonic-aristotle"     # stable + readable
    assert _prover_identity(a1) == _prover_identity(a2)           # stable across instances
    other = _prover_identity(OpenRouterProvider(model="deepseek/deepseek-prover-v2"))
    assert _prover_identity(a1) != other                          # a genuinely distinct voter


def test_conservative_judge_never_passes():
    assert ConservativeJudge().round_trip_agrees(None) == 0.0

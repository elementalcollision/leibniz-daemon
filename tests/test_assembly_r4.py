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
from leibniz.runtime import PersistentRuntime


def test_build_daemon_constructs_real_stack_without_network():
    d = build_daemon(frontier_limit=1, analogy_limit=1)
    assert isinstance(d, Leibniz)
    assert isinstance(d.derive, NoOpDerive)
    assert isinstance(d.demonstrate, ConsensusDemonstrate)   # N+1 consensus proving
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


def test_conservative_judge_never_passes():
    assert ConservativeJudge().round_trip_agrees(None) == 0.0

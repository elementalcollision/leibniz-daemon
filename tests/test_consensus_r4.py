"""R4.1: cascaded + witness proving with N+1 kernel-verified consensus (ADR 0006).

CI-safe: a fake Lean backend (verifies iff the script says "good") + fake provers.
Confirms consensus STRENGTHENS the proof edge — below threshold fails even with a
real kernel-verified proof — and that discharge stays the sole kernel_verified writer.
"""
from __future__ import annotations

from leibniz.consensus import ProofConsensus
from leibniz.propositio import Expressio
from leibniz.trust import PROOF_EDGE
from leibniz.types import Role, TrustTier, Verdict
from leibniz.verifiers import LeanVerifier


class _FakeLeanBackend:
    def compile_statement(self, expr):
        return True

    def check_proof(self, expr, proof_src):
        return "good" in (proof_src or "")

    def closed_by_decision_procedure(self, expr):
        return False


class _Prover:
    def __init__(self, script):
        self.script = script

    def propose(self, role: Role, context: str) -> str:
        return self.script

    def available(self):
        return True


class _DeadProver:
    def propose(self, role: Role, context: str) -> str:
        raise RuntimeError("prover down")

    def available(self):
        return False


def _expr():
    return Expressio(theorem_src="theorem t : P")


def _lean():
    return LeanVerifier(_FakeLeanBackend())


def test_consensus_reached_records_a_real_mechanical_pass():
    pc = ProofConsensus(
        provers=[_Prover("by good"), _Prover("by good"), _Prover("by bad")],
        lean=_lean(), min_consensus=2,
    )
    r = pc.prove(_expr())
    assert r.count == 2 and r.reached is True
    assert r.edge.edge == PROOF_EDGE
    assert r.edge.tier is TrustTier.MECHANICAL
    assert r.edge.verdict is Verdict.PASS
    assert r.edge.detail["consensus"] == 2
    assert r.proof is not None and r.proof.kernel_verified is True


def test_below_threshold_fails_even_with_one_kernel_verified_proof():
    pc = ProofConsensus(
        provers=[_Prover("by good"), _Prover("by bad")],
        lean=_lean(), min_consensus=2,
    )
    r = pc.prove(_expr())
    assert r.count == 1 and r.reached is False
    assert r.edge.tier is TrustTier.MECHANICAL and r.edge.verdict is Verdict.FAIL
    assert r.proof is None  # conservative: one proof is not enough when N+1=2


def test_dead_prover_is_skipped_not_fatal():
    pc = ProofConsensus(
        provers=[_DeadProver(), _Prover("by good"), _Prover("by good")],
        lean=_lean(), min_consensus=2,
    )
    r = pc.prove(_expr())
    assert r.count == 2 and r.reached is True


def test_all_drafts_rejected_yields_fail():
    pc = ProofConsensus(provers=[_Prover("by bad"), _Prover("by bad")], lean=_lean(), min_consensus=1)
    r = pc.prove(_expr())
    assert r.count == 0 and r.reached is False
    assert r.edge.verdict is Verdict.FAIL


# --- consensus counts DISTINCT models, not raw attempts (ADR 0024 review) ------

class _ModelProver:
    def __init__(self, model, script):
        self.model, self.script = model, script

    def propose(self, role: Role, context: str) -> str:
        return self.script

    def available(self):
        return True


def test_one_model_with_two_strategies_is_one_voter():
    # the exact ADR 0024 amplification: a model + its decomposition wrapper both verify,
    # but they share an identity, so a single model can NOT self-satisfy N+1.
    from leibniz.providers.decomposition_prover import DecompositionProver
    p = _ModelProver("M", "by good")
    pc = ProofConsensus(provers=[p, DecompositionProver(p)], lean=_lean(), min_consensus=2)
    r = pc.prove(_expr())
    assert r.count == 1 and r.reached is False  # one model, two strategies -> one voter
    assert r.proof is None


def test_distinct_models_reach_consensus():
    pc = ProofConsensus(
        provers=[_ModelProver("A", "by good"), _ModelProver("B", "by good")],
        lean=_lean(), min_consensus=2,
    )
    r = pc.prove(_expr())
    assert r.count == 2 and r.reached is True  # two INDEPENDENT models -> genuine consensus


def test_decomposition_adds_a_strategy_not_a_false_vote():
    # a decomposition wrapper of model A + a distinct model B: A (either strategy) and B
    # are two voters -> consensus; the wrapper gave A a second *way* to find a proof.
    from leibniz.providers.decomposition_prover import DecompositionProver
    a = _ModelProver("A", "by good")
    pc = ProofConsensus(
        provers=[a, DecompositionProver(a), _ModelProver("B", "by good")],
        lean=_lean(), min_consensus=2,
    )
    r = pc.prove(_expr())
    assert r.count == 2 and r.reached is True  # {A, B}, not 3

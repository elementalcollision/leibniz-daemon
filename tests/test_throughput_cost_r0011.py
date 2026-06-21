"""ADR 0011: concurrent prover ensemble + USD cost budget (CI-safe; fakes)."""
from __future__ import annotations

from leibniz.consensus import ProofConsensus
from leibniz.cost import CostBudget
from leibniz.daemon import Leibniz
from leibniz.gates.verification import VerificationGate
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.selection import KFM, Archive
from leibniz.trust import TrustPolicy
from leibniz.types import ClaimType, Verdict
from leibniz.verifiers import LeanVerifier


# --- CostBudget --------------------------------------------------------------

def test_cost_budget_unlimited_by_default():
    b = CostBudget()
    b.record_calls(1000)
    assert b.exhausted() is False


def test_cost_budget_exhausts_at_cap():
    b = CostBudget(cap_usd=0.05, per_call_usd=0.01)
    b.record_calls(4)
    assert b.exhausted() is False  # 0.04 < 0.05
    b.record_calls(1)
    assert b.exhausted() is True   # 0.05 >= 0.05


def test_cost_budget_from_env(monkeypatch):
    monkeypatch.setenv("LEIBNIZ_DAILY_USD_CAP", "2.5")
    monkeypatch.setenv("LEIBNIZ_PER_CALL_USD", "0.02")
    b = CostBudget.from_env()
    assert b.cap_usd == 2.5 and b.per_call_usd == 0.02


# --- concurrent consensus ----------------------------------------------------

class _FakeLeanBackend:
    def check_proof(self, expr, proof_src):
        return "good" in (proof_src or "")

    def compile_statement(self, expr):
        return True

    def closed_by_decision_procedure(self, expr):
        return False


class _Prover:
    def __init__(self, script):
        self.script = script

    def propose(self, role, ctx):
        return self.script

    def available(self):
        return True


def test_consensus_concurrent_reaches_threshold():
    pc = ProofConsensus(
        provers=[_Prover("by good"), _Prover("by good"), _Prover("by bad")],
        lean=LeanVerifier(_FakeLeanBackend()), min_consensus=2, max_workers=3,
    )
    r = pc.prove(Expressio(theorem_src="theorem t : P"))
    assert r.count == 2 and r.reached is True and r.edge.verdict is Verdict.PASS


def test_consensus_single_prover_uses_sequential_path():
    pc = ProofConsensus(
        provers=[_Prover("by good")], lean=LeanVerifier(_FakeLeanBackend()),
        min_consensus=1, max_workers=4,
    )
    r = pc.prove(Expressio(theorem_src="theorem t : P"))
    assert r.count == 1 and r.reached is True


# --- daemon honors the cost cap ----------------------------------------------

class _Survey:
    def run(self, domain):
        return ["a", "b"]


class _Conjecture:
    def run(self, seed):
        return Propositio(enuntiatio=Enuntiatio(statement=seed, claim_type=ClaimType.COMPLEXITY_BOUND,
                                                falsifiable_claim="x"))


class _FormalizeNull:
    def run(self, prop):
        return None


class _Runtime:
    def remember(self, p):
        pass


class _Stage:
    def run(self, *a, **k):
        return a[0] if a else None


def test_run_cycles_stops_when_cost_cap_reached():
    d = Leibniz(
        runtime=_Runtime(), survey=_Survey(), conjecture=_Conjecture(), formalize=_FormalizeNull(),
        derive=_Stage(), demonstrate=_Stage(), promulgate=_Stage(),
        verification=VerificationGate(TrustPolicy()), kfm=KFM(Archive()),
        cost_budget=CostBudget(cap_usd=0.03, per_call_usd=0.01),  # ~exhausts after one cycle
    )
    reports = d.run_cycles(5)
    assert len(reports) < 5  # stopped early on the cost cap

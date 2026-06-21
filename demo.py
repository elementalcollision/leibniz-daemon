"""Runnable demo: turn one circadian cycle with deterministic fakes.

This wires fake Lean/SMT/provider/runtime backends so you can watch the loop
move work through the six stages and see the trust boundary do its job -- some
conjectures die at cheap refutation, some as known/trivial, some as gamed, one
survives to a kernel-checked Q.E.D.

Run:  python demo.py
"""

from __future__ import annotations

from leibniz.daemon import Leibniz
from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.gates.novelty import NoveltyGate
from leibniz.gates.verification import VerificationGate
from leibniz.pipeline import (
    Conjecture,
    Demonstrate,
    Derive,
    Formalize,
    Promulgate,
    Survey,
)
from leibniz.propositio import Propositio
from leibniz.selection import KFM, Archive
from leibniz.types import ClaimSignature, ClaimType, Role
from leibniz.trust import TrustPolicy
from leibniz.verifiers import LeanVerifier, SMTVerifier


# --- fakes -------------------------------------------------------------------

class FakeLean:
    """Compiles everything; closes only statements marked AutoClosable; proves
    only the sorting-bound statement."""

    def compile_statement(self, expr):
        return "malformed" not in expr.theorem_src

    def check_proof(self, expr, proof_src):
        return "SortLowerBound" in expr.theorem_src and "by" in (proof_src or "")

    def closed_by_decision_procedure(self, expr):
        return "AutoClosable" in expr.theorem_src


class FakeSMT:
    def find_counterexample(self, claim, bound):
        return {"n": 1} if "refute" in claim else None

    def find_gaming_witness(self, statement, negated_claim, bound):
        return {"impl": "degenerate"} if "UnderSpecified" in statement else None


class FakeProvider:
    """Maps a seed keyword to a (statement, proof) so outcomes are legible.
    Statements are header-only; proofs are separate (the Newton inversion)."""

    _table = {
        "sort":    ("theorem sort_bound : SortLowerBound", "by induction_hammer"),
        "known":   ("theorem known_result : KnownBound", "by simp"),
        "trivial": ("theorem trivial_id : AutoClosable", "by simp"),
        "refute":  ("theorem refute_claim : FalseClaim", "by sorry"),
        "game":    ("theorem game_claim : UnderSpecified", "by sorry"),
    }

    def propose(self, role: Role, context: str) -> str:
        key = next((k for k in self._table if k in context.lower()), "sort")
        stmt, proof = self._table[key]
        if role is Role.CONJECTURE:
            return context
        if role is Role.FORMALIZE:
            return stmt
        if role is Role.PROOF_DRAFT:
            return proof
        return context


class FakeRuntime:
    def __init__(self):
        self.memory: list[Propositio] = []

    def now_phase(self):
        return "WAKE"

    def remember(self, prop):
        self.memory.append(prop)

    def recall_recent(self, n):
        return self.memory[-n:]

    def witness(self, prompt, n_models):
        return ["ok"] * n_models


class FakeLeonardo:
    def survey_frontier(self, domain):
        return [
            "sorting lower bound",   # -> proven
            "known result",          # -> KNOWN
            "trivial identity",      # -> TRIVIAL
            "refute me claim",       # -> REFUTED
            "game me claim",         # -> GAMED
        ]

    def cross_domain_analogies(self, seed):
        return []  # keep the demo's seed count legible


class FakeCorpus:
    def contains_equivalent(self, sig: ClaimSignature) -> bool:
        return sig.subject.startswith("known")

    def nearest(self, sig, k=5):
        return [("nlogn_sort_bound", 0.42)]


class FakeJudge:
    def round_trip_agrees(self, prop) -> float:
        return 0.95


def build() -> Leibniz:
    lean = LeanVerifier(FakeLean())
    smt = SMTVerifier(FakeSMT())
    provider = FakeProvider()
    novelty = NoveltyGate(FakeCorpus(), lean)
    faithfulness = FaithfulnessGate(
        smt=smt,
        probes={ClaimType.COMPLEXITY_BOUND: lambda p: True},  # mechanical PASS
        judge=FakeJudge(),
    )
    policy = TrustPolicy()
    return Leibniz(
        runtime=FakeRuntime(),
        survey=Survey(FakeLeonardo()),
        conjecture=Conjecture(provider),
        formalize=Formalize(provider, lean, smt, novelty, faithfulness),
        derive=Derive(provider),
        demonstrate=Demonstrate(lean),
        promulgate=Promulgate(),
        verification=VerificationGate(policy),
        kfm=KFM(Archive()),
    )


if __name__ == "__main__":
    daemon = build()
    report = daemon.circadian_cycle()
    print("Calculemus -- one circadian cycle")
    print(f"  seeds surveyed:   {report.seeds}")
    print(f"  conjectured:      {report.conjectured}")
    print(f"  reached proof:    {report.reached_proof}")
    print(f"  promulgated:      {report.promulgated}")
    print("  dispositions:")
    for reason, n in sorted(report.by_reason.items()):
        print(f"    {reason:<14} {n}")
    print(f"  archive coverage cells: {len(daemon.kfm.archive.cells)}")
    proven = [p for p in daemon.runtime.memory if p.promulgated]  # type: ignore
    for p in proven:
        assert p.demonstratio is not None
        print(f"  Q.E.D. -> {p.expressio.theorem_src}  [{p.demonstratio.qed}]")

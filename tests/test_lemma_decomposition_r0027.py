"""ADR 0027: independent sub-lemma decomposition (hints design).

Prove helper lemmas independently, then offer them to the prover as `have`-block HINTS.
The kernel only ever checks ONE self-contained declaration (`theorem_src := proof`); the
hints are prover context and NEVER enter the Lean source — so there is no
separate-declaration surface a smuggled `axiom`/`attribute`/`run_cmd` could poison.
"""
from __future__ import annotations

import json

import pytest

from leibniz.backends import lean_repl
from leibniz.consensus import ConsensusResult, ProofConsensus
from leibniz.lemma_decomposition import DecomposingDemonstrate, LemmaDecomposer, _safe_lemma
from leibniz.propositio import Demonstratio, Enuntiatio, Expressio, Propositio
from leibniz.trust import PROOF_EDGE
from leibniz.types import ClaimType, EdgeEvidence, TrustTier, Verdict


# --- hints are prover-context only, never the kernel file (the soundness property) ----

def test_prover_context_offers_hints_but_keeps_them_out_of_the_goal():
    with_hints = Expressio(theorem_src="theorem t : P", proof_hints="have aux : Q := by ring")
    ctx = ProofConsensus._prover_context(with_hints)
    assert "have aux : Q := by ring" in ctx and "theorem t : P" in ctx
    # and with no hints the prover just gets the goal, unchanged
    assert ProofConsensus._prover_context(Expressio(theorem_src="theorem t : P")) == "theorem t : P"


def test_safe_lemma_hygiene():
    assert _safe_lemma("aux1", "(n : Nat) : 2 ∣ n*(n+1)") is True
    assert _safe_lemma("bad name", "(n : Nat) : True") is False  # not an identifier
    assert _safe_lemma("aux", "(n:Nat): True\nextra") is False   # multi-line
    assert _safe_lemma("aux", "(n:Nat): True := by trivial") is False  # premature :=


# --- the decomposer orchestration (CI-safe fakes) ----------------------------

def _pass(proof_src="by ring") -> ConsensusResult:
    demo = Demonstratio(proof_obligation="t", proof_src=proof_src, kernel_verified=True, qed="Q.E.D.")
    edge = EdgeEvidence(edge=PROOF_EDGE, tier=TrustTier.MECHANICAL, verdict=Verdict.PASS,
                        detail={}, cost_units=1.0)
    return ConsensusResult(count=2, required=2, attempts=2, edge=edge, proof=demo)


def _fail() -> ConsensusResult:
    edge = EdgeEvidence(edge=PROOF_EDGE, tier=TrustTier.MECHANICAL, verdict=Verdict.FAIL,
                        detail={}, cost_units=1.0)
    return ConsensusResult(count=0, required=2, attempts=2, edge=edge, proof=None)


class _FakeConsensus:
    obligation = "claim"

    def __init__(self):
        self.calls: list[Expressio] = []

    def prove(self, expr: Expressio) -> ConsensusResult:
        self.calls.append(expr)
        return _pass()


class _Provider:
    def __init__(self, plan):
        self.plan = plan

    def decompose(self, theorem_src: str) -> str:
        return json.dumps(self.plan)


def test_decomposer_proves_sublemmas_then_composes_with_hints():
    plan = {"lemmas": [{"name": "aux1", "statement": "(n : Nat) : 2 ∣ n*(n+1)"}],
            "main_proof": "by exact aux1 n"}
    con = _FakeConsensus()
    result = LemmaDecomposer(_Provider(plan), con).prove(
        Expressio(theorem_src="theorem t (n:Nat) : 2 ∣ n*(n+1)*(n+2)", imports=("Mathlib.Tactic",)))
    assert result is not None and result.reached
    composed = con.calls[-1]  # the composed main attempt
    assert "have aux1 (n : Nat) : 2 ∣ n*(n+1) := by ring" in composed.proof_hints
    assert composed.theorem_src == "theorem t (n:Nat) : 2 ∣ n*(n+1)*(n+2)"


def test_decomposer_drops_all_unsafe_lemmas():
    plan = {"lemmas": [
        {"name": "bad name", "statement": "(n:Nat): True"},
        {"name": "withnewline", "statement": "(n:Nat): True\nextra"},
        {"name": "withassign", "statement": "(n:Nat): True := by trivial"},
    ], "main_proof": "by trivial"}
    con = _FakeConsensus()
    assert LemmaDecomposer(_Provider(plan), con).prove(Expressio(theorem_src="theorem t : True")) is None
    assert con.calls == []  # never paid to prove a malformed lemma


def test_decomposer_handles_missing_hook_and_bad_json():
    con = _FakeConsensus()

    class _NoDecompose:
        pass

    class _BadJson:
        def decompose(self, ts):
            return "not json at all"

    assert LemmaDecomposer(_NoDecompose(), con).prove(Expressio(theorem_src="t")) is None
    assert LemmaDecomposer(_BadJson(), con).prove(Expressio(theorem_src="t")) is None


# --- DecomposingDemonstrate (CI-safe) ----------------------------------------

def _prop(theorem_src: str) -> Propositio:
    return Propositio(
        enuntiatio=Enuntiatio(statement="c", claim_type=ClaimType.INVARIANT, falsifiable_claim="n"),
        expressio=Expressio(theorem_src=theorem_src, imports=("Mathlib.Tactic",)),
    )


class _RoutingConsensus:
    """Original main (a `theorem` with no hints) fails; lemmas + the composed proof pass."""
    obligation = "claim"

    def __init__(self):
        self.calls: list[Expressio] = []

    def prove(self, expr: Expressio) -> ConsensusResult:
        self.calls.append(expr)
        if expr.theorem_src.startswith("theorem") and not expr.proof_hints:
            return _fail()
        return _pass()


def test_demonstrate_falls_back_to_decomposition_and_records_one_edge():
    con = _RoutingConsensus()
    dec = LemmaDecomposer(
        _Provider({"lemmas": [{"name": "aux1", "statement": "(n:Nat): True"}], "main_proof": "by trivial"}),
        con)
    out = DecomposingDemonstrate(con, dec).run(_prop("theorem t (n:Nat) : True"))
    assert out.demonstratio is not None and out.demonstratio.kernel_verified  # decomposition closed it
    proof_edges = [e for e in out.edges if e.edge == PROOF_EDGE]
    assert len(proof_edges) == 1 and proof_edges[0].verdict is Verdict.PASS  # ONE edge, the PASS


def test_demonstrate_skips_decomposition_when_consensus_succeeds():
    class _AlwaysPass:
        obligation = "claim"

        def __init__(self):
            self.calls = 0

        def prove(self, expr):
            self.calls += 1
            return _pass()

    class _Boom:
        def prove(self, expr):
            raise AssertionError("decomposer must not run when consensus already passed")

    con = _AlwaysPass()
    out = DecomposingDemonstrate(con, _Boom()).run(_prop("theorem t : True"))
    assert out.demonstratio.kernel_verified and con.calls == 1


# --- the soundness property, against the real kernel (gated) ------------------

@pytest.mark.skipif(not lean_repl.available(), reason="lean REPL image not available")
def test_proof_hints_never_reach_the_kernel_and_composition_verifies():
    be = lean_repl.LeanReplBackend()
    try:
        # proof_hints carrying `axiom cheat : False` must NOT put `cheat` in scope — the
        # hints are prover context, never the Lean source. The proof `by exact cheat`
        # therefore fails (unknown identifier), so nothing false is provable via hints.
        poisoned = Expressio(theorem_src="theorem t : False", imports=("Mathlib.Tactic",),
                             proof_hints="axiom cheat : False")
        assert be.check_proof(poisoned, "by exact cheat") is False
        # a genuine single-declaration proof that splices a `have` verifies for real.
        ok = Expressio(theorem_src="theorem t (n : Nat) : n + 1 = 1 + n", imports=("Mathlib.Tactic",))
        assert be.check_proof(ok, "by\n  have h : n + 1 = 1 + n := by ring\n  exact h") is True
    finally:
        be.close()

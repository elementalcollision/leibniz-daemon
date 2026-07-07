"""ADR 0058 increment 2 — CI-safe tests for the residue DEMONSTRATE fast-path (promote-on-one).

No Docker/Lean: a fake kernel verifier exercises the fast-path's promotion, its fall-through to the
N+1 ensemble, the A2 canonical-statement rewrite, the A4 axiom gate, and that the promoted edge is a
real MECHANICAL/PASS/KERNEL_PRODUCER proof edge that `TrustPolicy.validate_path` accepts. An opt-in
real-kernel test (`LEIBNIZ_LEAN_E2E=1`) proves-and-promulgates end-to-end.
"""
from __future__ import annotations

import os
import re

import pytest

from leibniz import assembly
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.providers.residue_prover import ResidueDemonstrate
from leibniz.trust import (
    FAITHFULNESS_EDGE,
    KERNEL_PRODUCER,
    NOVELTY_EDGE,
    PROOF_EDGE,
    TrustPolicy,
)
from leibniz.types import ClaimType, EdgeEvidence, TrustTier, Verdict

MODULAR = ("a >= 0 and b >= 0", "((a*b)^2 + a*b) % 6 == 0 or ((a*b)^2 + a*b) % 6 == 2")


class FakeBackend:
    def __init__(self, clean=True):
        self.clean = clean

    def _run(self, src, imports):
        if not self.clean:
            return {"messages": [{"severity": "error", "data": "unclean"}]}
        name = (re.search(r"theorem\s+(\S+)", src) or [None, "x"])[1]
        return {"messages": [{"severity": "info", "data": f"'{name}' depends on axioms: [propext]"}]}


class FakeLean:
    """Stands in for LeanVerifier: discharge sets kernel_verified and returns the kernel proof edge."""

    def __init__(self, accept=True, clean=True):
        self.accept, self.backend = accept, FakeBackend(clean)

    def discharge(self, expr, demo):
        demo.kernel_verified = self.accept and bool(demo.proof_src)
        ok = demo.kernel_verified
        return EdgeEvidence(edge=PROOF_EDGE, tier=TrustTier.MECHANICAL,
                            verdict=Verdict.PASS if ok else Verdict.FAIL,
                            detail={"obligation": demo.proof_obligation}, cost_units=10.0,
                            producer=KERNEL_PRODUCER)


class FakeInner:
    def __init__(self):
        self.called = False

    def run(self, prop):
        self.called = True
        return prop


def mkprop(cd, cp):
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=cd, claim_property=cp)
    return Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem llm (a b : Nat) : True"))


def test_fastpath_promotes_on_one_and_rewrites_theorem_src():
    inner = FakeInner()
    stage = ResidueDemonstrate(inner=inner, lean=FakeLean(accept=True, clean=True))
    prop = mkprop(*MODULAR)
    stage.run(prop)
    assert inner.called is False                                   # fast-path handled it; ensemble skipped
    assert prop.demonstratio is not None and prop.demonstratio.kernel_verified is True
    # A2: the promulgated theorem_src is the gate-rendered canonical ℤ-box law, not the LLM's Nat one
    assert prop.expressio.theorem_src.startswith("theorem residue_law_")
    assert "∀ (a b : ℤ)" in prop.expressio.theorem_src and "Int.emod" in prop.expressio.theorem_src
    proof_edges = [e for e in prop.edges if e.edge == PROOF_EDGE]
    assert len(proof_edges) == 1
    ev = proof_edges[0]
    assert ev.verdict is Verdict.PASS and ev.tier is TrustTier.MECHANICAL
    assert ev.producer == KERNEL_PRODUCER                          # promotion still gated by the kernel
    assert ev.detail.get("decision_procedure") == "residue-poly-zmod" and ev.detail.get("consensus") == 1


def test_the_promoted_edge_passes_validate_path():
    # the fast-path edge, with the faithfulness + novelty edges FORMALIZE records, must promulgate
    stage = ResidueDemonstrate(inner=FakeInner(), lean=FakeLean(accept=True, clean=True))
    prop = mkprop(*MODULAR)
    stage.run(prop)
    edges = list(prop.edges) + [
        EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS),
        EdgeEvidence(NOVELTY_EDGE, TrustTier.MECHANICAL, Verdict.PASS),
    ]
    TrustPolicy().validate_path(edges)                             # must NOT raise


def test_falls_through_when_kernel_rejects():
    inner = FakeInner()
    ResidueDemonstrate(inner=inner, lean=FakeLean(accept=False)).run(mkprop(*MODULAR))
    assert inner.called is True                                    # kernel rejected → N+1 ensemble runs


def test_falls_through_when_axioms_unclean():
    inner = FakeInner()
    ResidueDemonstrate(inner=inner, lean=FakeLean(accept=True, clean=False)).run(mkprop(*MODULAR))
    assert inner.called is True                                    # native_decide/sorry footprint → fall through


@pytest.mark.parametrize("cd,cp", [
    ("a >= 0 and b >= 0", "min(a, b) % 3 == 0"),      # out of fragment
    ("n >= 0", "(n*n) % 4 == 0 or (n*n) % 4 == 1"),   # single variable
    (None, "((a*b)^2 + a*b) % 6 == 0"),               # no claim_domain
])
def test_falls_through_outside_fragment(cd, cp):
    inner = FakeInner()
    ResidueDemonstrate(inner=inner, lean=FakeLean(accept=True)).run(mkprop(cd, cp))
    assert inner.called is True


def test_assembly_wiring_is_default_off():
    inner = FakeInner()
    consensus = type("C", (), {"lean": FakeLean()})()
    # no flag → returned unchanged (not wrapped)
    assert assembly.maybe_wrap_residue(inner, consensus, env={}) is inner
    # flag set → wrapped in the fast-path
    wrapped = assembly.maybe_wrap_residue(inner, consensus, env={"LEIBNIZ_LEAN_DECIDED": "1"})
    assert isinstance(wrapped, ResidueDemonstrate) and wrapped.inner is inner


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_end_to_end():  # pragma: no cover
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.verifiers import LeanVerifier
    if not available():
        pytest.skip("Lean image unavailable")
    be = LeanReplBackend(timeout_s=150)
    try:
        stage = ResidueDemonstrate(inner=FakeInner(), lean=LeanVerifier(be))
        prop = mkprop(*MODULAR)                                    # the live claim
        stage.run(prop)
        assert prop.demonstratio.kernel_verified is True          # the kernel proved the canonical law
        assert prop.expressio.theorem_src.startswith("theorem residue_law_")
    finally:
        be.close()

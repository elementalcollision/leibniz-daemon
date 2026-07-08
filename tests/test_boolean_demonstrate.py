"""ADR 0059 (biconditional path) — CI-safe tests for the boolean-combination DEMONSTRATE fast-path.

No Docker/Lean: a fake kernel verifier exercises promote-on-one, fall-through, the A2 statement rewrite,
the A4 axiom gate, and that the promoted edge is a real MECHANICAL/PASS/KERNEL_PRODUCER proof edge that
`TrustPolicy.validate_path` accepts.
"""
from __future__ import annotations

import os
import re

import pytest

from leibniz import assembly
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.providers.boolean_prover import BooleanDemonstrate
from leibniz.trust import FAITHFULNESS_EDGE, KERNEL_PRODUCER, NOVELTY_EDGE, PROOF_EDGE, TrustPolicy
from leibniz.types import ClaimType, EdgeEvidence, TrustTier, Verdict

BICOND = ("a >= 0 and b >= 0", "((a*b) % 3 == 0) == ((a % 3 == 0) or (b % 3 == 0))")


class FakeBackend:
    def __init__(self, clean=True):
        self.clean = clean

    def _run(self, src, imports):
        if not self.clean:
            return {"messages": [{"severity": "error", "data": "unclean"}]}
        name = (re.search(r"theorem\s+(\S+)", src) or [None, "x"])[1]
        return {"messages": [{"severity": "info", "data": f"'{name}' depends on axioms: [propext]"}]}


class FakeLean:
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


def mkprop(cd, cp, *, boolean_faith=True):
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=cd, claim_property=cp)
    prop = Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem llm (a b : Nat) : True"))
    if boolean_faith:
        prop.record(EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS,
                                 producer="boolean_modular/kernel"))
    return prop


def test_fastpath_promotes_on_one_and_rewrites_theorem_src():
    inner = FakeInner()
    BooleanDemonstrate(inner=inner, lean=FakeLean(accept=True, clean=True)).run(prop := mkprop(*BICOND))
    assert inner.called is False
    assert prop.demonstratio is not None and prop.demonstratio.kernel_verified is True
    assert prop.expressio.theorem_src.startswith("theorem boolean_law_")
    assert "∀ (a b : ℤ)" in prop.expressio.theorem_src and "↔" in prop.expressio.theorem_src
    edges = [e for e in prop.edges if e.edge == PROOF_EDGE]
    assert len(edges) == 1 and edges[0].producer == KERNEL_PRODUCER
    assert edges[0].detail.get("decision_procedure") == "boolean-modular-zmod" and edges[0].detail.get("consensus") == 1


def test_promulgates_end_to_end():
    prop = mkprop(*BICOND)
    BooleanDemonstrate(inner=FakeInner(), lean=FakeLean(accept=True, clean=True)).run(prop)
    TrustPolicy().validate_path(list(prop.edges) + [EdgeEvidence(NOVELTY_EDGE, TrustTier.MECHANICAL, Verdict.PASS)])


def test_producer_admitted():
    from leibniz.trust import FAITHFULNESS_PRODUCERS
    assert "boolean_modular/kernel" in FAITHFULNESS_PRODUCERS


def test_falls_through_when_kernel_rejects_or_unclean():
    for lean in (FakeLean(accept=False), FakeLean(accept=True, clean=False)):
        inner = FakeInner()
        BooleanDemonstrate(inner=inner, lean=lean).run(mkprop(*BICOND))
        assert inner.called is True


@pytest.mark.parametrize("cd,cp", [
    ("a >= 0 and b >= 0", "(a % 4 == 0) == (b % 6 == 0)"),   # mixed modulus → out of fragment
    ("a >= 0 and b >= 0", "max(a,b) + min(a,b) == a + b"),   # min/max identity → the OTHER fast-path
    ("n >= 0", "(n%5==0) or (n%5==1)"),                       # single variable
    (None, "((a*b) % 3 == 0) == ((a % 3 == 0) or (b % 3 == 0))"),  # no claim_domain
])
def test_falls_through_outside_fragment(cd, cp):
    inner = FakeInner()
    BooleanDemonstrate(inner=inner, lean=FakeLean(accept=True)).run(mkprop(cd, cp))
    assert inner.called is True


def test_falls_through_without_boolean_faithfulness_edge():
    inner = FakeInner()
    prop = mkprop(*BICOND, boolean_faith=False)
    BooleanDemonstrate(inner=inner, lean=FakeLean(accept=True, clean=True)).run(prop)
    assert inner.called is True and all(e.edge != PROOF_EDGE for e in prop.edges)


def test_does_not_promote_a_lean_decided_edge_claim():
    inner = FakeInner()
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=BICOND[0], claim_property=BICOND[1])
    prop = Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem llm (a b : Nat) : True"))
    prop.record(EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS, producer="lean_decided/kernel"))
    BooleanDemonstrate(inner=inner, lean=FakeLean(accept=True, clean=True)).run(prop)
    assert inner.called is True and all(e.edge != PROOF_EDGE for e in prop.edges)


def test_hash_refreshed():
    from leibniz.verifiers import normalize_statement
    prop = mkprop(*BICOND)
    BooleanDemonstrate(inner=FakeInner(), lean=FakeLean(accept=True, clean=True)).run(prop)
    assert prop.expressio.normalized_hash == normalize_statement(prop.expressio.theorem_src)


def test_exception_inside_fastpath_falls_through(monkeypatch):
    import leibniz.providers.boolean_prover as bp
    inner = FakeInner()
    monkeypatch.setattr(bp, "boolean_law", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
    BooleanDemonstrate(inner=inner, lean=FakeLean(accept=True)).run(mkprop(*BICOND))
    assert inner.called is True


def test_assembly_wiring_needs_flag_and_repl(monkeypatch):
    from leibniz.backends import lean_repl
    inner = FakeInner()
    consensus = type("C", (), {"lean": FakeLean()})()
    assert assembly.maybe_wrap_boolean(inner, consensus, "img", env={}) is inner
    monkeypatch.setattr(lean_repl, "available", lambda image: False)
    assert assembly.maybe_wrap_boolean(inner, consensus, "img", env={"LEIBNIZ_LEAN_DECIDED": "1"}) is inner
    monkeypatch.setattr(lean_repl, "available", lambda image: True)
    wrapped = assembly.maybe_wrap_boolean(inner, consensus, "img", env={"LEIBNIZ_LEAN_DECIDED": "1"})
    assert isinstance(wrapped, BooleanDemonstrate) and wrapped.inner is inner


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_end_to_end():  # pragma: no cover
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.verifiers import LeanVerifier
    if not available():
        pytest.skip("Lean image unavailable")
    be = LeanReplBackend(timeout_s=150)
    try:
        prop = mkprop(*BICOND)
        BooleanDemonstrate(inner=FakeInner(), lean=LeanVerifier(be)).run(prop)
        assert prop.demonstratio.kernel_verified is True
        assert prop.expressio.theorem_src.startswith("theorem boolean_law_")
    finally:
        be.close()

"""ADR 0060 — CI-safe tests for the mixed-modulus DEMONSTRATE fast-path (promote-on-one).

No Docker/Lean: a fake kernel verifier exercises promotion, fall-through, the A2 statement rewrite, the
A4 axiom gate, and that the promoted edge is a real MECHANICAL/PASS/KERNEL_PRODUCER proof edge that
`TrustPolicy.validate_path` accepts.
"""
from __future__ import annotations

import os
import re

import pytest

from leibniz import assembly
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.providers.mixed_modulus_prover import MixedModulusDemonstrate
from leibniz.trust import FAITHFULNESS_EDGE, KERNEL_PRODUCER, NOVELTY_EDGE, PROOF_EDGE, TrustPolicy
from leibniz.types import ClaimType, EdgeEvidence, TrustTier, Verdict

MIXED = ("a >= 0 and b >= 0", "((a+b)**2 % 4 == 1) == ((a+b) % 2 == 1)")


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


def mkprop(cd, cp, *, mixed_faith=True):
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=cd, claim_property=cp)
    prop = Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem llm (a b : Nat) : True"))
    if mixed_faith:
        prop.record(EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS,
                                 producer="mixed_modular/kernel"))
    return prop


def test_fastpath_promotes_on_one_and_rewrites_theorem_src():
    inner = FakeInner()
    MixedModulusDemonstrate(inner=inner, lean=FakeLean(accept=True, clean=True)).run(prop := mkprop(*MIXED))
    assert inner.called is False
    assert prop.demonstratio is not None and prop.demonstratio.kernel_verified is True
    assert prop.expressio.theorem_src.startswith("theorem mixed_law_")
    assert "∀ (a b : ℤ)" in prop.expressio.theorem_src and "↔" in prop.expressio.theorem_src
    edges = [e for e in prop.edges if e.edge == PROOF_EDGE]
    assert len(edges) == 1 and edges[0].producer == KERNEL_PRODUCER
    assert edges[0].detail.get("decision_procedure") == "mixed-modulus-lcm-casthom" and edges[0].detail.get("consensus") == 1


def test_promulgates_end_to_end():
    prop = mkprop(*MIXED)
    MixedModulusDemonstrate(inner=FakeInner(), lean=FakeLean(accept=True, clean=True)).run(prop)
    TrustPolicy().validate_path(list(prop.edges) + [EdgeEvidence(NOVELTY_EDGE, TrustTier.MECHANICAL, Verdict.PASS)])


def test_producer_admitted():
    from leibniz.trust import FAITHFULNESS_PRODUCERS
    assert "mixed_modular/kernel" in FAITHFULNESS_PRODUCERS


def test_falls_through_when_kernel_rejects_or_unclean():
    for lean in (FakeLean(accept=False), FakeLean(accept=True, clean=False)):
        inner = FakeInner()
        MixedModulusDemonstrate(inner=inner, lean=lean).run(mkprop(*MIXED))
        assert inner.called is True


@pytest.mark.parametrize("cd,cp", [
    ("a >= 0 and b >= 0", "((a*b) % 3 == 0) == ((a % 3 == 0) or (b % 3 == 0))"),   # single modulus → the OTHER path
    ("a >= 0 and b >= 0", "(a % 100 == 0) == (a % 99 == 0)"),                       # lcm too large
    ("n >= 0", "(n**2 % 6 == 1) == (n % 2 == 1)"),                                  # single variable
    (None, "((a+b)**2 % 4 == 1) == ((a+b) % 2 == 1)"),                              # no claim_domain
])
def test_falls_through_outside_fragment(cd, cp):
    inner = FakeInner()
    MixedModulusDemonstrate(inner=inner, lean=FakeLean(accept=True)).run(mkprop(cd, cp))
    assert inner.called is True


def test_falls_through_without_mixed_faithfulness_edge():
    inner = FakeInner()
    prop = mkprop(*MIXED, mixed_faith=False)
    MixedModulusDemonstrate(inner=inner, lean=FakeLean(accept=True, clean=True)).run(prop)
    assert inner.called is True and all(e.edge != PROOF_EDGE for e in prop.edges)


def test_does_not_promote_a_boolean_edge_claim():
    inner = FakeInner()
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=MIXED[0], claim_property=MIXED[1])
    prop = Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem llm (a b : Nat) : True"))
    prop.record(EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS, producer="boolean_modular/kernel"))
    MixedModulusDemonstrate(inner=inner, lean=FakeLean(accept=True, clean=True)).run(prop)
    assert inner.called is True and all(e.edge != PROOF_EDGE for e in prop.edges)


def test_hash_refreshed():
    from leibniz.verifiers import normalize_statement
    prop = mkprop(*MIXED)
    MixedModulusDemonstrate(inner=FakeInner(), lean=FakeLean(accept=True, clean=True)).run(prop)
    assert prop.expressio.normalized_hash == normalize_statement(prop.expressio.theorem_src)


def test_exception_inside_fastpath_falls_through(monkeypatch):
    import leibniz.providers.mixed_modulus_prover as mp
    inner = FakeInner()
    monkeypatch.setattr(mp, "mixed_law", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
    MixedModulusDemonstrate(inner=inner, lean=FakeLean(accept=True)).run(mkprop(*MIXED))
    assert inner.called is True


def test_assembly_wiring_needs_flag_and_repl(monkeypatch):
    from leibniz.backends import lean_repl
    inner = FakeInner()
    consensus = type("C", (), {"lean": FakeLean()})()
    assert assembly.maybe_wrap_mixed_modulus(inner, consensus, "img", env={}) is inner
    monkeypatch.setattr(lean_repl, "available", lambda image: False)
    assert assembly.maybe_wrap_mixed_modulus(inner, consensus, "img", env={"LEIBNIZ_LEAN_DECIDED": "1"}) is inner
    monkeypatch.setattr(lean_repl, "available", lambda image: True)
    wrapped = assembly.maybe_wrap_mixed_modulus(inner, consensus, "img", env={"LEIBNIZ_LEAN_DECIDED": "1"})
    assert isinstance(wrapped, MixedModulusDemonstrate) and wrapped.inner is inner


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_end_to_end():  # pragma: no cover
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.verifiers import LeanVerifier
    if not available():
        pytest.skip("Lean image unavailable")
    be = LeanReplBackend(timeout_s=150)
    try:
        prop = mkprop(*MIXED)
        MixedModulusDemonstrate(inner=FakeInner(), lean=LeanVerifier(be)).run(prop)
        assert prop.demonstratio.kernel_verified is True
        assert prop.expressio.theorem_src.startswith("theorem mixed_law_")
    finally:
        be.close()

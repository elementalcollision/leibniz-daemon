"""ADR 0059 (min/max half) B.1 — CI-safe tests for the min/max DEMONSTRATE fast-path (promote-on-one).

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
from leibniz.providers.minmax_prover import MinMaxDemonstrate
from leibniz.trust import (
    FAITHFULNESS_EDGE,
    KERNEL_PRODUCER,
    NOVELTY_EDGE,
    PROOF_EDGE,
    TrustPolicy,
)
from leibniz.types import ClaimType, EdgeEvidence, TrustTier, Verdict

IDENTITY = ("a >= 0 and b >= 0", "max(a,b)**2 + min(a,b)**2 == a**2 + b**2")


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


def mkprop(cd, cp, *, minmax_faith=True):
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=cd, claim_property=cp)
    prop = Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem llm (a b : Nat) : True"))
    if minmax_faith:   # the statement-binding faithfulness PASS the fast-path requires (A2)
        prop.record(EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS,
                                 producer="minmax_identity/kernel"))
    return prop


def test_fastpath_promotes_on_one_and_rewrites_theorem_src():
    inner = FakeInner()
    MinMaxDemonstrate(inner=inner, lean=FakeLean(accept=True, clean=True)).run(prop := mkprop(*IDENTITY))
    assert inner.called is False
    assert prop.demonstratio is not None and prop.demonstratio.kernel_verified is True
    # A2: the promulgated theorem_src is the gate-rendered canonical ℤ-box identity law, not the LLM's Nat one
    assert prop.expressio.theorem_src.startswith("theorem minmax_law_")
    assert "∀ (a b : ℤ)" in prop.expressio.theorem_src and "max a b" in prop.expressio.theorem_src
    proof_edges = [e for e in prop.edges if e.edge == PROOF_EDGE]
    assert len(proof_edges) == 1
    ev = proof_edges[0]
    assert ev.verdict is Verdict.PASS and ev.tier is TrustTier.MECHANICAL and ev.producer == KERNEL_PRODUCER
    assert ev.detail.get("decision_procedure") == "minmax-order-split" and ev.detail.get("consensus") == 1


def test_the_full_fastpath_path_promulgates_end_to_end():
    prop = mkprop(*IDENTITY)
    MinMaxDemonstrate(inner=FakeInner(), lean=FakeLean(accept=True, clean=True)).run(prop)
    assert any(e.edge == PROOF_EDGE and e.producer == KERNEL_PRODUCER for e in prop.edges)
    assert any(e.edge == FAITHFULNESS_EDGE and e.producer == "minmax_identity/kernel" for e in prop.edges)
    TrustPolicy().validate_path(list(prop.edges) + [
        EdgeEvidence(NOVELTY_EDGE, TrustTier.MECHANICAL, Verdict.PASS),
    ])   # must NOT raise — the min/max lever promulgates


def test_minmax_faithfulness_producer_is_admitted():
    from leibniz.trust import FAITHFULNESS_PRODUCERS
    assert "minmax_identity/kernel" in FAITHFULNESS_PRODUCERS
    TrustPolicy().validate_path([
        EdgeEvidence(PROOF_EDGE, TrustTier.MECHANICAL, Verdict.PASS, producer=KERNEL_PRODUCER),
        EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS, producer="minmax_identity/kernel"),
        EdgeEvidence(NOVELTY_EDGE, TrustTier.MECHANICAL, Verdict.PASS),
    ])   # must NOT raise


def test_falls_through_when_kernel_rejects():
    inner = FakeInner()
    MinMaxDemonstrate(inner=inner, lean=FakeLean(accept=False)).run(mkprop(*IDENTITY))
    assert inner.called is True


def test_falls_through_when_axioms_unclean():
    inner = FakeInner()
    MinMaxDemonstrate(inner=inner, lean=FakeLean(accept=True, clean=False)).run(mkprop(*IDENTITY))
    assert inner.called is True


@pytest.mark.parametrize("cd,cp", [
    ("a >= 0 and b >= 0", "max(a, min(b, c)) == a"),   # nested → out of fragment
    ("a >= 0 and b >= 0", "(a*a + b*b) % 4 != 3"),     # modular → the OTHER fast-path's job
    ("n >= 0", "max(n, n) == n"),                       # single variable / degenerate
    (None, "max(a,b) + min(a,b) == a + b"),            # no claim_domain
])
def test_falls_through_outside_fragment(cd, cp):
    inner = FakeInner()
    MinMaxDemonstrate(inner=inner, lean=FakeLean(accept=True)).run(mkprop(cd, cp))
    assert inner.called is True


def test_falls_through_without_minmax_faithfulness_edge():
    # an identity that passed faithfulness some OTHER way (no minmax_identity/kernel edge) is NOT
    # fast-pathed — its canonical statement was never statement-bound-vetted (A2 gate).
    inner = FakeInner()
    prop = mkprop(*IDENTITY, minmax_faith=False)
    MinMaxDemonstrate(inner=inner, lean=FakeLean(accept=True, clean=True)).run(prop)
    assert inner.called is True and all(e.edge != PROOF_EDGE for e in prop.edges)


def test_does_not_promote_a_residue_edge_claim():
    # a lean_decided/kernel (modular) faithfulness edge must NOT let the min/max fast-path promote —
    # the two producers are distinct; each fast-path owns its own edge.
    inner = FakeInner()
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=IDENTITY[0], claim_property=IDENTITY[1])
    prop = Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem llm (a b : Nat) : True"))
    prop.record(EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS, producer="lean_decided/kernel"))
    MinMaxDemonstrate(inner=inner, lean=FakeLean(accept=True, clean=True)).run(prop)
    assert inner.called is True and all(e.edge != PROOF_EDGE for e in prop.edges)


def test_hash_refreshed_to_the_published_statement():
    from leibniz.verifiers import normalize_statement
    prop = mkprop(*IDENTITY)
    MinMaxDemonstrate(inner=FakeInner(), lean=FakeLean(accept=True, clean=True)).run(prop)
    assert prop.expressio.normalized_hash == normalize_statement(prop.expressio.theorem_src)


def test_exception_inside_fastpath_falls_through(monkeypatch):
    import leibniz.providers.minmax_prover as mp
    inner = FakeInner()
    monkeypatch.setattr(mp, "minmax_law", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
    MinMaxDemonstrate(inner=inner, lean=FakeLean(accept=True)).run(mkprop(*IDENTITY))
    assert inner.called is True


def test_assembly_wiring_needs_flag_AND_repl(monkeypatch):
    from leibniz.backends import lean_repl
    inner = FakeInner()
    consensus = type("C", (), {"lean": FakeLean()})()
    assert assembly.maybe_wrap_minmax(inner, consensus, "img", env={}) is inner
    monkeypatch.setattr(lean_repl, "available", lambda image: False)
    assert assembly.maybe_wrap_minmax(inner, consensus, "img", env={"LEIBNIZ_LEAN_DECIDED": "1"}) is inner
    monkeypatch.setattr(lean_repl, "available", lambda image: True)
    wrapped = assembly.maybe_wrap_minmax(inner, consensus, "img", env={"LEIBNIZ_LEAN_DECIDED": "1"})
    assert isinstance(wrapped, MinMaxDemonstrate) and wrapped.inner is inner


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_end_to_end():  # pragma: no cover
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.verifiers import LeanVerifier
    if not available():
        pytest.skip("Lean image unavailable")
    be = LeanReplBackend(timeout_s=150)
    try:
        prop = mkprop(*IDENTITY)
        MinMaxDemonstrate(inner=FakeInner(), lean=LeanVerifier(be)).run(prop)
        assert prop.demonstratio.kernel_verified is True
        assert prop.expressio.theorem_src.startswith("theorem minmax_law_")
    finally:
        be.close()

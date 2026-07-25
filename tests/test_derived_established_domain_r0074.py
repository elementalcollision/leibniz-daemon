"""ADR 0074 — the mechanically-derived `established_domain`.

CI-safe: no Docker, no Lean, no z3 required — fake sound backends and a fake SMT backend
exercise every guard. The point of these tests is the FAIL-CLOSED set: the derivation must
refuse unless a decided-fragment backend owns the claim AND the claim domain is conclusively
non-empty, and it must never touch claim_property/claim_domain. The live-kernel behaviour
(true tail claims certify, a FALSE claim is still refused) is pinned by the opt-in e2e at the
bottom.
"""
from __future__ import annotations

import os

import pytest

from leibniz.pipeline import Formalize
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimType, Verdict

BOX = "a >= 0 and b >= 0"
CP = "(a^2 + a*b + b^2) % 9 != 6"


class _Backend:
    """decide_unsat: False = conclusively satisfiable, True = unsat/empty, None = unknown."""

    def __init__(self, verdict=False):
        self.verdict = verdict

    def decide_unsat(self, preds, bound=0):
        return self.verdict


class _Smt:
    def __init__(self, backend):
        self.backend = backend


class _Gate:
    def __init__(self, applies=True, boom=False):
        self.sound_backends = (self,) if applies is not None else ()
        self._applies, self._boom = applies, boom
        self.name = "fake-decided"

    def applies(self, prop):
        if self._boom:
            raise RuntimeError("classifier surprise")
        return self._applies


def _formalize(gate, backend=None):
    return Formalize(provider=None, lean=None, smt=_Smt(backend or _Backend()),
                     novelty=None, faithfulness=gate)


def _prop(cd=BOX, cp=CP, ed=CP):
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=cd, claim_property=cp)
    return Propositio(enuntiatio=en,
                      expressio=Expressio(theorem_src="theorem t : True", established_domain=ed))


def test_derives_when_a_decided_backend_owns_the_claim():
    p = _prop()
    _formalize(_Gate(applies=True))._derive_established_domain(p)
    assert p.expressio.established_domain == BOX          # the property-restating ed is replaced
    assert p.enuntiatio.claim_property == CP              # property NEVER touched
    assert p.enuntiatio.claim_domain == BOX               # domain NEVER widened


def test_noop_when_already_canonical():
    p = _prop(ed=BOX)
    _formalize(_Gate(applies=True))._derive_established_domain(p)
    assert p.expressio.established_domain == BOX


def test_fail_closed_without_a_registered_decided_backend():
    p = _prop()
    _formalize(_Gate(applies=None))._derive_established_domain(p)   # sound_backends == ()
    assert p.expressio.established_domain == CP           # untouched -> DEFERs honestly, as today


def test_fail_closed_when_no_backend_owns_the_claim():
    p = _prop()
    _formalize(_Gate(applies=False))._derive_established_domain(p)
    assert p.expressio.established_domain == CP


@pytest.mark.parametrize("verdict", [True, None])
def test_fail_closed_on_empty_or_undecided_claim_domain(verdict):
    # True  = claim_domain is UNSAT: a canonical ed would launder a vacuous PASS
    # None  = Z3 could not decide: no conclusive answer, so no commit
    p = _prop()
    _formalize(_Gate(applies=True), _Backend(verdict))._derive_established_domain(p)
    assert p.expressio.established_domain == CP


def test_fail_closed_without_a_usable_smt_backend():
    for smt in (_Smt(None), _Smt(object())):                # no backend / no decide_unsat
        p = _prop()
        f = Formalize(provider=None, lean=None, smt=smt, novelty=None,
                      faithfulness=_Gate(applies=True))
        f._derive_established_domain(p)
        assert p.expressio.established_domain == CP


def test_a_raising_classifier_never_breaks_the_pipeline():
    p = _prop()
    _formalize(_Gate(applies=True, boom=True))._derive_established_domain(p)
    assert p.expressio.established_domain == CP           # swallowed, contract untouched


def test_prose_only_contract_is_untouched():
    for cd, cp, ed in ((None, CP, CP), (BOX, None, CP), (BOX, CP, None), ("", CP, CP)):
        p = _prop(cd=cd, cp=cp, ed=ed)
        _formalize(_Gate(applies=True))._derive_established_domain(p)
        assert p.expressio.established_domain == ed        # OPEN_FORM path unchanged
    p = Propositio(enuntiatio=Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT,
                                         falsifiable_claim="x"), expressio=None)
    _formalize(_Gate(applies=True))._derive_established_domain(p)   # must not raise


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_certifies_true_tail_claims_and_still_refuses_a_false_one(monkeypatch):  # pragma: no cover
    from leibniz.assembly import maybe_register_lean_decided
    from leibniz.backends import lean_repl
    from leibniz.backends.smt_z3 import Z3Backend
    from leibniz.gates.faithfulness import FaithfulnessGate
    from leibniz.probes import default_probes
    from leibniz.verifiers import SMTVerifier
    monkeypatch.setenv("LEIBNIZ_LEAN_DECIDED", "1")   # the backend is opt-in (assembly gate)
    if not lean_repl.available():
        pytest.skip("Lean image unavailable")
    smt = SMTVerifier(backend=Z3Backend())
    gate = FaithfulnessGate(smt=smt, probes=default_probes(smt),
                            judge=type("J", (), {"round_trip_agrees": lambda self, p: 0.0})())
    assert maybe_register_lean_decided(gate, lean_repl.REPL_IMAGE)
    f = Formalize(provider=None, lean=None, smt=smt, novelty=None, faithfulness=gate)
    for cp, expect_pass in ((CP, True), ("(a^2 + b^2) % 4 != 3", True),
                            ("((4*a+1)*(4*b+3)) % 8 == 3", False)):   # the false control
        p = _prop(cp=cp, ed=cp)                            # ed restates the property (the defect)
        f._derive_established_domain(p)
        assert p.expressio.established_domain == BOX
        # the KERNEL still decides: a false claim fails its property leg and is refused
        assert (gate.check(p).verdict is Verdict.PASS) is expect_pass

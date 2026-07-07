"""ADR 0056 Track A increment 2 — CI-safe unit tests for the Lean-decided faithfulness backend.

No Docker/Lean here: a FAKE kernel exercises the gate-owned classification, proof construction,
statement binding, re-check, and fail-closed wiring. An opt-in real-kernel integration test
(``LEIBNIZ_LEAN_E2E=1``) mirrors ``scratchpad/validate_inc2.py`` and is the ground-truth anchor.
"""
from __future__ import annotations

import os

import pytest

from leibniz.gates import lean_decided as ld
from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.gates.sound_backends import Certificate
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimType, Verdict


# --- a fake kernel: check_proof configurable by theorem-name marker; clean axiom footprint ---------

class FakeKernel:
    def __init__(self, reject_names=()):
        self.reject_names = tuple(reject_names)

    def check_proof(self, expr, proof_src):
        return not any(f"_{n}_" in expr.theorem_src for n in self.reject_names)

    def _run(self, src, imports):
        # axiom_closure parses this: a clean footprint, no error, unless the name is rejected.
        import re
        m = re.search(r"(?:theorem|lemma)\s+(\S+)", src)
        name = m.group(1) if m else "x"
        if any(f"_{n}_" in src for n in self.reject_names):
            return {"messages": [{"severity": "error", "data": "kernel rejected"}]}
        return {"messages": [{"severity": "info",
                              "data": f"'{name}' depends on axioms: [propext, Classical.choice]"}]}


def mkprop(cd, cp, ed):
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=cd, claim_property=cp)
    return Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem t : True", established_domain=ed))


TWO_VAR = ("a >= 0 and b >= 0", "(a*a + b*b) % 4 != 3", "a >= 0 and b >= 0")


# --- classification -------------------------------------------------------------------------------

def test_classify_neq_eq_residueset():
    assert ld.classify_property("(a*a + b*b) % 4 != 3").op == "neq"
    assert ld.classify_property("(a*b*(a*a - b*b)) % 6 == 0").op == "eq"
    s = ld.classify_property("(n*n) % 5 == 0 or (n*n) % 5 == 1")
    assert s.op == "residue_set" and s.modulus == 5 and set(s.residues) == {0, 1}


@pytest.mark.parametrize("bad", [
    "min(a, b) % 3 == 0",              # min is renderable but NOT residue-bridgeable → out of skeleton
    "(a / 2) % 4 == 1",                # division inside the poly
    "(a*a + b*b) % 4 == 3 and a != b",  # not a bare atom
    "(a*a) % 4 == 0 or (a*a) % 6 == 1",  # mixed moduli
    "(a*a) % 4 == 0 or (b*b) % 4 == 1",  # mixed polynomials
    "(a*a + b*b) % 4 < 3",              # comparison other than ==/!=
    "a % b == 0",                       # variable modulus (not a constant)
    "(a*a + b*b) % 1 == 0",             # modulus < 2
])
def test_classify_rejects_out_of_skeleton(bad):
    assert ld.classify_property(bad) is None


def test_is_pure_poly():
    from leibniz.dsl_to_lean import _parse
    assert ld._is_pure_poly(_parse("a*a + b*b - 3*a"))
    assert ld._is_pure_poly(_parse("a^2 + b^2"))
    assert ld._is_pure_poly(_parse("-a + b"))
    assert not ld._is_pure_poly(_parse("a % 4"))       # mod is not a pure polynomial
    assert not ld._is_pure_poly(_parse("min(a, b)"))
    assert not ld._is_pure_poly(_parse("a / 2"))


# --- applies(): the routing / invariant-5 gate ----------------------------------------------------

def test_applies_only_multivar_modular_in_budget():
    be = ld.LeanDecidedFaithfulness(kernel=FakeKernel())
    assert be.applies(mkprop(*TWO_VAR)) is True
    # 1-var stays on the cheap Z3 probe (invariant 5)
    assert be.applies(mkprop("n >= 0", "(n*n) % 4 == 0 or (n*n) % 4 == 1", "n >= 0")) is False
    # min/max not bridgeable
    assert be.applies(mkprop("a >= 0 and b >= 0", "min(a,b) % 3 == 0", "a >= 0 and b >= 0")) is False
    # non-modular property
    assert be.applies(mkprop("a >= 0 and b >= 0", "a*a >= a", "a >= 0 and b >= 0")) is False
    # missing established_domain
    assert be.applies(mkprop("a >= 0 and b >= 0", "(a*a+b*b) % 4 != 3", None)) is False
    # residue budget: modulus**nvars over cap
    assert be.applies(mkprop("a >= 0 and b >= 0", "(a*a + b*b) % 97 != 3", "a >= 0 and b >= 0")) is False


# --- decide_certificate with the fake kernel (structural: builds + checks all four) ---------------

def test_decide_certificate_pass_when_kernel_accepts_all():
    ok, detail = ld.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], TWO_VAR)),
                                       FakeKernel())
    assert ok and "witness_claim" in detail and detail["property"]["axioms"]


def test_decide_certificate_defers_when_property_rejected():
    ok, detail = ld.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], TWO_VAR)),
                                       FakeKernel(reject_names=["property"]))
    assert not ok and "property" in detail["reason"]


def test_decide_certificate_defers_on_bad_data_shape():
    for bad in [{"claim_domain": "a>=0"}, {"claim_domain": 1, "claim_property": "x", "established_domain": "y"},
                "notadict", {"a": "b", "c": "d", "e": "f"}]:
        ok, _ = ld.decide_certificate(bad, FakeKernel())
        assert not ok


def test_decide_certificate_defers_on_vacuous_domain_without_touching_kernel():
    class BoomKernel:
        def check_proof(self, *a):
            raise AssertionError("kernel must not be reached for a vacuous domain")
        def _run(self, *a):
            raise AssertionError("kernel must not be reached")
    # unsatisfiable claim_domain over the non-negative box → no ∃-witness → DEFER before any kernel call
    ok, detail = ld.decide_certificate(
        {"claim_domain": "(a*a + b*b) % 4 == 3", "claim_property": "a*b % 5 == 0",
         "established_domain": "a >= 0 and b >= 0"}, BoomKernel())
    assert not ok and "witness" in detail["reason"]


# --- find_witness ---------------------------------------------------------------------------------

def test_find_witness():
    assert ld.find_witness(["a >= 0 and b >= 0"], ["a", "b"]) == (0, 0)
    assert ld.find_witness(["(a*a + b*b) % 4 == 3"], ["a", "b"]) is None   # unsat over the box


# --- statement binding (obligation 5) -------------------------------------------------------------

def test_template_renders_from_prop_and_binds():
    tmpl = ld.prop_statement_template
    p = mkprop(*TWO_VAR)
    expected = tmpl(p)
    assert expected is not None and "∀" in expected and "∃" in expected
    assert tmpl(mkprop("a >= 0 and b >= 0", "(a*a+b*b) % 4 != 3", None)) is None   # unbindable


def test_gate_refuses_tampered_certificate_statement():
    gate = _gate_with_backend(FakeKernel())
    p = mkprop(*TWO_VAR)
    v = gate.sound_backends[-1].check(p)
    assert v.verdict is Verdict.PASS
    # honest → accepted
    assert gate.check(p).verdict is Verdict.PASS
    # tamper the statement the certificate claims → binding refuses → not a PASS (falls through)
    orig_check = gate.sound_backends[-1].check
    def tampered_check(prop):
        vv = orig_check(prop)
        if vv.certificate is not None:
            vv.certificate.detail["statement"] = "theorem evil : True"
        return vv
    gate.sound_backends[-1].check = tampered_check
    assert gate.check(p).verdict is not Verdict.PASS


# --- make_rechecker -------------------------------------------------------------------------------

def test_rechecker_redereives_and_rejects_tampering():
    recheck = ld.make_rechecker(FakeKernel())
    data = dict(zip(["claim_domain", "claim_property", "established_domain"], TWO_VAR))
    good = Certificate(kind=ld.KIND, rechecked=True, data=data,
                       detail={"statement": ld.canonical_statement(**data)})
    assert recheck(good) is True
    # tampered statement string (does not match template(cert.data)) → False
    bad_stmt = Certificate(kind=ld.KIND, rechecked=True, data=data, detail={"statement": "nope"})
    assert recheck(bad_stmt) is False
    # a str-subclass statement (spoof attempt) → False (builtin-str pin)
    class S(str):
        pass
    spoof = Certificate(kind=ld.KIND, rechecked=True, data=data,
                        detail={"statement": S(ld.canonical_statement(**data))})
    assert recheck(spoof) is False
    # bad data shape → False
    assert recheck(Certificate(kind=ld.KIND, rechecked=True, data={"x": 1}, detail={"statement": "y"})) is False


def test_rechecker_defers_when_kernel_rejects_property():
    recheck = ld.make_rechecker(FakeKernel(reject_names=["property"]))
    data = dict(zip(["claim_domain", "claim_property", "established_domain"], TWO_VAR))
    cert = Certificate(kind=ld.KIND, rechecked=True, data=data,
                       detail={"statement": ld.canonical_statement(**data)})
    assert recheck(cert) is False


# --- fail-closed wiring ---------------------------------------------------------------------------

def _bare_gate():
    from leibniz.probes import default_probes
    from leibniz.verifiers import SMTVerifier
    from leibniz.backends.smt_z3 import Z3Backend
    smt = SMTVerifier(backend=Z3Backend())
    return FaithfulnessGate(smt=smt, probes=default_probes(smt),
                            judge=type("J", (), {"round_trip_agrees": lambda self, p: 0.0})())


def _gate_with_backend(kernel):
    gate = _bare_gate()
    ld.register(gate, kernel)
    return gate


def test_failclosed_bare_gate_has_no_lean_decided_backend():
    gate = _bare_gate()
    assert ld.KIND not in gate.recheckers and ld.KIND not in gate.templates
    assert all(getattr(b, "name", "") != "lean-decided" for b in gate.sound_backends)


def test_failclosed_backend_present_but_no_rechecker_is_not_accepted():
    # simulate a mis-wire: backend added but re-checker/template NOT registered → PASS not accepted
    gate = _bare_gate()
    gate.sound_backends = (ld.LeanDecidedFaithfulness(kernel=FakeKernel()),)
    # no recheckers[KIND] → the accept path cannot accept it
    assert gate.check(mkprop(*TWO_VAR)).verdict is not Verdict.PASS


def test_register_wires_all_three():
    gate = _gate_with_backend(FakeKernel())
    assert ld.KIND in gate.recheckers and ld.KIND in gate.templates
    assert any(getattr(b, "name", "") == "lean-decided" for b in gate.sound_backends)


# --- opt-in real-kernel integration (ground truth) ------------------------------------------------

@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_end_to_end():  # pragma: no cover
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean image unavailable")
    be = LeanReplBackend(timeout_s=150)
    try:
        d = dict(zip(["claim_domain", "claim_property", "established_domain"], TWO_VAR))
        assert ld.decide_certificate(d, be)[0] is True                       # true claim → PASS
        d_false = {**d, "claim_property": "(a*a + b*b) % 4 != 2"}
        assert ld.decide_certificate(d_false, be)[0] is False                 # false claim → DEFER
    finally:
        be.close()

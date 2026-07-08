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


@pytest.mark.parametrize("bad", [
    "(2*a) % 2 == 2",                    # c == m: 2 ≡ 0 in ZMod 2 → key vacuously true, ℤ stmt false
    "a*3 % 3 == 3",                      # c == m
    "(a*a + b*b) % 4 == 5",              # c > m
    "(a*a) % 2 == 0 or (a*a) % 2 == 2",  # residue_set with an out-of-range residue → whole thing DEFERs
])
def test_classify_rejects_out_of_range_residues(bad):
    # STATIC guard: soundness must not depend on the `simpa` bridge failing in the kernel.
    assert ld.classify_property(bad) is None


# --- ADR 0059 conjunctions ------------------------------------------------------------------------

def test_classify_conjunction_accepts_single_modulus():
    s = ld.classify_property("(a*a) % 4 != 3 and (b*b) % 4 != 3")
    assert s.op == "conjunction" and s.modulus == 4 and len(s.atoms) == 2
    assert [op for (op, _poly, _c) in s.atoms] == ["neq", "neq"]
    # mixed ops, same poly, same modulus
    s2 = ld.classify_property("(a*b*(a*a - b*b)) % 6 == 0 and (a*b*(a*a - b*b)) % 6 != 1")
    assert s2.op == "conjunction" and s2.modulus == 6
    assert [op for (op, _poly, _c) in s2.atoms] == ["eq", "neq"] and [c for (*_x, c) in s2.atoms] == [0, 1]
    # three conjuncts
    s3 = ld.classify_property("(a*a) % 3 == 0 and (b*b) % 3 == 1 and (a*b) % 3 != 2")
    assert s3.op == "conjunction" and len(s3.atoms) == 3


@pytest.mark.parametrize("bad", [
    "(a*a) % 4 == 0 and (b*b) % 6 == 1",        # mixed moduli → DEFER (no LCM machinery)
    "(a*a) % 4 == 0 and (a*a) % 4 == 1 and a != b",   # a non-atom conjunct
    "(a*a) % 4 == 0 and min(a,b) % 4 == 1",     # min not residue-bridgeable
    "(a*a) % 4 == 0 and (a / 2) % 4 == 1",      # division inside a conjunct poly
    "((a*a) % 4 == 0 and (b*b) % 4 == 1) and (a*b) % 4 == 2",  # nested And (grouped) → inner And not an atom
    "(a*a) % 4 == 0 and (b*b) % 4 == 4",        # out-of-range residue in a conjunct (c == m)
    "(a*a) % 4 == 0 or (b*b) % 4 == 1 and (a*b) % 4 == 2",  # top-level is Or, mixed connective
])
def test_classify_conjunction_rejects(bad):
    assert ld.classify_property(bad) is None


def test_classify_conjunction_respects_conjunct_cap():
    over = " and ".join(f"(a*a + b*b) % 8 != {c}" for c in range(ld.MAX_CONJUNCTS + 1))
    assert ld.classify_property(over) is None                       # over MAX_CONJUNCTS → DEFER
    at_cap = " and ".join(f"(a*a + b*b) % 16 != {c}" for c in range(ld.MAX_CONJUNCTS))
    assert ld.classify_property(at_cap).op == "conjunction"         # exactly MAX_CONJUNCTS → OK


def test_conjunction_proof_structure_splits_and_keys_each_atom():
    s = ld.classify_property("(a*a) % 4 != 3 and (b*b) % 4 == 0")
    body = ld.conjunction_proof(s, ["a", "b"], n_domain=2)
    assert body.startswith("by\n  intro a b _ _ _ _")   # 2 vars + 2 box + 2 domain
    assert "refine ⟨?_, ?_⟩" in body
    assert body.count("by decide") == 2                 # one per-atom ZMod key
    assert "ZMod.intCast_eq_intCast_iff'" in body
    # LAW leg introduces one fewer domain antecedent
    assert ld.conjunction_proof(s, ["a", "b"], n_domain=1).startswith("by\n  intro a b _ _ _\n")


def test_applies_and_decide_certificate_accept_conjunction_with_fake_kernel():
    conj = ("a >= 0 and b >= 0",
            "(a*a + b*b) % 4 != 3 and (a*a + b*b) % 4 != 2",
            "a >= 0 and b >= 0")
    assert ld.LeanDecidedFaithfulness(kernel=FakeKernel()).applies(mkprop(*conj)) is True
    ok, detail = ld.decide_certificate(
        dict(zip(["claim_domain", "claim_property", "established_domain"], conj)), FakeKernel())
    assert ok and detail["property"]["axioms"]           # the conjunction property leg built + checked
    # a rejected property leg (false conjunct in the real kernel) → DEFER
    ok2, _ = ld.decide_certificate(
        dict(zip(["claim_domain", "claim_property", "established_domain"], conj)),
        FakeKernel(reject_names=["property"]))
    assert not ok2


def test_is_pure_poly_bounds_exponent_by_max_pow():
    from leibniz.dsl_to_lean import _parse
    from leibniz.backends.smt_z3 import MAX_POW
    assert ld._is_pure_poly(_parse(f"a ** {MAX_POW}"))
    assert not ld._is_pure_poly(_parse(f"a ** {MAX_POW + 1}"))   # over cap → not a renderable poly


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


# --- the assembly opt-in guard (default OFF; on only with flag AND a real image) ------------------

def test_maybe_register_lean_decided_is_default_off():
    from leibniz import assembly
    gate = _bare_gate()
    # no flag → not registered, even if the image were available
    assert assembly.maybe_register_lean_decided(gate, "img", env={}) is False
    assert ld.KIND not in gate.recheckers


def test_maybe_register_lean_decided_needs_flag_AND_image(monkeypatch):
    from leibniz import assembly
    from leibniz.backends import lean_repl
    # flag set but image unavailable → still fail-closed
    monkeypatch.setattr(lean_repl, "available", lambda image: False)
    gate = _bare_gate()
    assert assembly.maybe_register_lean_decided(gate, "img", env={"LEIBNIZ_LEAN_DECIDED": "1"}) is False
    assert ld.KIND not in gate.recheckers
    # flag set AND image available → registers (backend construction stubbed to avoid Docker)
    monkeypatch.setattr(lean_repl, "available", lambda image: True)
    monkeypatch.setattr(lean_repl, "LeanReplBackend", lambda image=None: FakeKernel())
    gate2 = _bare_gate()
    assert assembly.maybe_register_lean_decided(gate2, "img", env={"LEIBNIZ_LEAN_DECIDED": "1"}) is True
    assert ld.KIND in gate2.recheckers and ld.KIND in gate2.templates


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

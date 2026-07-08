"""ADR 0060 — CI-safe unit tests for the LCM/castHom mixed-modulus faithfulness backend.

No Docker/Lean: a FAKE kernel exercises classification (≥2-modulus fragment, LCM bound, disjointness
from boolean_decided, non-triviality), proof construction, statement binding, re-check, and fail-closed
wiring. An opt-in real-kernel test (``LEIBNIZ_LEAN_E2E=1``) mirrors ``scratchpad/validate_mixed_e2e.py``.
"""
from __future__ import annotations

import os

import pytest

from leibniz.gates import mixed_modulus_decided as mm
from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.gates.sound_backends import Certificate
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimType, Verdict


class FakeKernel:
    def __init__(self, reject_names=()):
        self.reject_names = tuple(reject_names)

    def check_proof(self, expr, proof_src):
        return not any(f"_{n}_" in expr.theorem_src for n in self.reject_names)

    def _run(self, src, imports):
        import re
        m = re.search(r"(?:theorem|lemma)\s+(\S+)", src)
        name = m.group(1) if m else "x"
        if any(f"_{n}_" in src for n in self.reject_names):
            return {"messages": [{"severity": "error", "data": "kernel rejected"}]}
        return {"messages": [{"severity": "info", "data": f"'{name}' depends on axioms: [propext]"}]}


def mkprop(cd, cp, ed):
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=cd, claim_property=cp)
    return Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem t : True", established_domain=ed))


MIXED = ("a >= 0 and b >= 0", "((a+b)**2 % 4 == 1) == ((a+b) % 2 == 1)", "a >= 0 and b >= 0")


def _bare_gate():
    from leibniz.backends.smt_z3 import Z3Backend
    from leibniz.probes import default_probes
    from leibniz.verifiers import SMTVerifier
    smt = SMTVerifier(backend=Z3Backend())
    return FaithfulnessGate(smt=smt, probes=default_probes(smt),
                            judge=type("J", (), {"round_trip_agrees": lambda self, p: 0.0})())


def _gate_with_backend(kernel):
    gate = _bare_gate()
    mm.register(gate, kernel)
    return gate


# --- classification ------------------------------------------------------------------------------

def test_classify_accepts_mixed_modulus():
    assert mm.classify_mixed("((a+b)**2 % 4 == 1) == ((a+b) % 2 == 1)").M == 4
    assert mm.classify_mixed("((a*a+b*b) % 4 == 2) == ((a % 2 == 1) and (b % 2 == 1))").M == 4
    # lcm(2,3) = 6 with three distinct moduli {6,2,3}
    s = mm.classify_mixed("(a**2 % 6 == 1) == ((b % 2 == 1) and ((a % 3 == 1) or (b % 3 == 2)))")
    assert s is not None and s.M == 6


@pytest.mark.parametrize("bad", [
    "((a*b) % 3 == 0) == ((a % 3 == 0) or (b % 3 == 0))",   # single modulus (3) → boolean_decided's job
    "(a*a + b*b) % 4 != 3",                                  # single atom, single modulus
    "(a % 4 == 0) and (b % 4 == 1)",                         # single modulus (4)
    "(a % 100 == 0) == (a % 99 == 0)",                       # lcm(100,99)=9900 > MAX_LCM
    "(a % 2 == 0) == (a % 2 == 0)",                          # content-free tautology
    "(a % 2 == 0) == (a % 4 < 3)",                           # a non-eq/neq comparison atom
    "(min(a,b) % 2 == 0) == (a % 4 == 0)",                   # min not a pure poly
])
def test_classify_rejects_out_of_fragment(bad):
    assert mm.classify_mixed(bad) is None


def test_content_free_guard_keys_by_modulus():
    # ADR 0060 review (#content-free): a content-BEARING law whose atoms share the same (poly, residue)
    # but differ in MODULUS must NOT be spuriously rejected as content-free. `(a+b)%4==1 → (a+b)%2==1`
    # (rendered `¬((a+b)%4==1) ∨ ((a+b)%2==1)`) is a genuine modular implication; a modulus-blind key
    # would merge the two atoms into one boolean var and see the tautology `¬V ∨ V`.
    s = mm.classify_mixed("(not ((a+b) % 4 == 1)) or ((a+b) % 2 == 1)")
    assert s is not None and s.M == 4 and sorted(mj for _p, mj, _c in s.atoms) == [2, 4]
    # a REAL content-free mixed tautology (each modulus's atom is complemented) is still rejected
    assert mm.classify_mixed(
        "((a % 4 == 1) or (not (a % 4 == 1))) and ((a % 3 == 0) or (not (a % 3 == 0)))") is None


def test_classify_lcm_and_dedup():
    s = mm.classify_mixed("((a+b)**2 % 4 == 1) == ((a+b) % 2 == 1)")
    assert s.M == 4 and len(s.atoms) == 2               # {(a+b)^2 %4, (a+b) %2}
    # atoms carry their individual moduli
    assert sorted(mj for _poly, mj, _c in s.atoms) == [2, 4]


# --- proof construction --------------------------------------------------------------------------

def test_mixed_proof_structure():
    s = mm.classify_mixed("((a+b)**2 % 4 == 1) == ((a+b) % 2 == 1)")
    body = mm.mixed_proof(s, ["a", "b"], n_domain=2)
    assert body.startswith("by\n  intro a b _ _ _ _")   # 2 vars + 2 box + 2 domain
    assert "∀ (a b : ZMod 4)" in body and "ZMod.castHom (show (2:ℕ) ∣ 4 by decide)" in body
    assert body.count("ZMod.intCast_eq_intCast_iff'") == len(s.atoms)
    assert "push_cast" in body and "simp only [map_add" in body and body.rstrip().endswith("exact hk")
    # the M-modulus atom is NOT wrapped in a castHom (only sub-M atoms are)
    assert "ZMod.castHom (show (4:ℕ) ∣ 4" not in body


def test_neq_sets_ne_eq_and_negation_rendering():
    s = mm.classify_mixed("((a+b)**2 % 4 != 1) == ((a+b) % 2 == 1)")
    assert s.has_neq is True
    body = mm.mixed_proof(s, ["a", "b"], n_domain=1)
    assert "simp only [ne_eq]" in body and "(¬ (" in body


# --- applies + decide_certificate ----------------------------------------------------------------

def test_applies_multivar_mixed_in_budget():
    be = mm.MixedModulusFaithfulness(kernel=FakeKernel())
    assert be.applies(mkprop(*MIXED)) is True
    assert be.applies(mkprop("a>=0 and b>=0", "((a*b)%3==0)==((a%3==0) or (b%3==0))", "a>=0 and b>=0")) is False  # single mod
    assert be.applies(mkprop("n >= 0", "(n**2 % 6 == 1) == (n % 2 == 1)", "n >= 0")) is False                     # 1-var


def test_decide_certificate_pass_and_defer():
    data = dict(zip(["claim_domain", "claim_property", "established_domain"], MIXED))
    ok, detail = mm.decide_certificate(data, FakeKernel())
    assert ok and detail["lcm"] == 4 and detail["property"]["axioms"]
    ok2, d2 = mm.decide_certificate(data, FakeKernel(reject_names=["property"]))   # false formula in real kernel
    assert not ok2 and "property" in d2["reason"]


def test_decide_certificate_bad_shape_and_fragment():
    for bad in [{"claim_domain": "a>=0"}, "notadict", {"a": "b", "c": "d", "e": "f"}]:
        assert not mm.decide_certificate(bad, FakeKernel())[0]

    class Boom:
        def check_proof(self, *a):
            raise AssertionError("kernel must not be reached outside the fragment")
        def _run(self, *a):
            raise AssertionError("nope")
    ok, d = mm.decide_certificate(
        {"claim_domain": "a>=0 and b>=0", "claim_property": "((a*b)%3==0)==((a%3==0) or (b%3==0))",
         "established_domain": "a>=0 and b>=0"}, Boom())
    assert not ok and "fragment" in d["reason"]


# --- statement binding + rechecker + fail-closed -------------------------------------------------

def test_register_installs_both_and_binds():
    gate = _gate_with_backend(FakeKernel())
    assert mm.KIND in gate.recheckers and mm.KIND in gate.templates
    assert gate.check(mkprop(*MIXED)).verdict is Verdict.PASS


def test_gate_refuses_tampered_statement():
    gate = _gate_with_backend(FakeKernel())
    p = mkprop(*MIXED)
    orig = gate.sound_backends[-1].check
    def tampered(prop):
        vv = orig(prop)
        if vv.certificate is not None:
            vv.certificate.detail["statement"] = "theorem evil : True"
        return vv
    gate.sound_backends[-1].check = tampered
    assert gate.check(p).verdict is not Verdict.PASS


def test_rechecker_rederives_and_rejects_tampering():
    recheck = mm.make_rechecker(FakeKernel())
    data = dict(zip(["claim_domain", "claim_property", "established_domain"], MIXED))
    good = Certificate(kind=mm.KIND, rechecked=True, data=data,
                       detail={"statement": mm.canonical_statement(**data)})
    assert recheck(good) is True
    assert recheck(Certificate(kind=mm.KIND, rechecked=True, data=data, detail={"statement": "nope"})) is False

    class S(str):
        pass
    spoof = Certificate(kind=mm.KIND, rechecked=True, data=data,
                        detail={"statement": S(mm.canonical_statement(**data))})
    assert recheck(spoof) is False
    assert recheck(Certificate(kind=mm.KIND, rechecked=True, data={"x": 1}, detail={"statement": "y"})) is False


def test_rechecker_defers_when_kernel_rejects_property():
    recheck = mm.make_rechecker(FakeKernel(reject_names=["property"]))
    data = dict(zip(["claim_domain", "claim_property", "established_domain"], MIXED))
    cert = Certificate(kind=mm.KIND, rechecked=True, data=data,
                       detail={"statement": mm.canonical_statement(**data)})
    assert recheck(cert) is False


def test_fail_closed_without_registration():
    assert mm.KIND not in _bare_gate().recheckers


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_certifies_true_and_defers_false():  # pragma: no cover
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.verifiers import LeanVerifier
    if not available():
        pytest.skip("Lean image unavailable")
    be = LeanReplBackend(timeout_s=150)
    try:
        kernel = LeanVerifier(be)
        assert mm.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], MIXED)), kernel)[0]
        false_m = ("a >= 0 and b >= 0", "((a+b)**2 % 4 == 1) == ((a+b) % 2 == 0)", "a >= 0 and b >= 0")
        assert not mm.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], false_m)), kernel)[0]
    finally:
        be.close()

"""ADR 0059 (biconditional path) — CI-safe unit tests for the ZMod-decide boolean-combination backend.

No Docker/Lean: a FAKE kernel exercises classification (the fragment gate), proof construction, statement
binding, re-check, and fail-closed wiring. An opt-in real-kernel test (``LEIBNIZ_LEAN_E2E=1``) mirrors
``scratchpad/validate_boolean_e2e.py``.
"""
from __future__ import annotations

import os

import pytest

from leibniz.gates import boolean_decided as bd
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
        return {"messages": [{"severity": "info",
                              "data": f"'{name}' depends on axioms: [propext, Classical.choice]"}]}


def mkprop(cd, cp, ed):
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=cd, claim_property=cp)
    return Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem t : True", established_domain=ed))


BICOND = ("a >= 0 and b >= 0", "((a*b) % 3 == 0) == ((a % 3 == 0) or (b % 3 == 0))", "a >= 0 and b >= 0")


def _bare_gate():
    from leibniz.backends.smt_z3 import Z3Backend
    from leibniz.probes import default_probes
    from leibniz.verifiers import SMTVerifier
    smt = SMTVerifier(backend=Z3Backend())
    return FaithfulnessGate(smt=smt, probes=default_probes(smt),
                            judge=type("J", (), {"round_trip_agrees": lambda self, p: 0.0})())


def _gate_with_backend(kernel):
    gate = _bare_gate()
    bd.register(gate, kernel)
    return gate


# --- classification (the fragment gate lives at the classifier) -----------------------------------

def test_classify_accepts_boolean_combinations():
    assert bd.classify_boolean("((a*b) % 3 == 0) == ((a % 3 == 0) or (b % 3 == 0))").modulus == 3
    assert bd.classify_boolean("(a % 5 == 0) or (b % 5 == 0)").modulus == 5      # ∨ of different polys
    assert bd.classify_boolean("not (a**2 % 4 == 2)").modulus == 4                # negation
    s = bd.classify_boolean("(a % 2 == 0) == (b % 2 == 1)")                       # bare biconditional
    assert s is not None and len(s.atoms) == 2
    # xor: `(P) != (Q)` → ¬(P ↔ Q)
    assert bd.classify_boolean("(a % 2 == 0) != (b % 2 == 0)") is not None


@pytest.mark.parametrize("bad", [
    "(a % 4 == 0) == (b % 6 == 0)",       # MIXED moduli → DEFER (needs LCM machinery)
    "(a*a) % 4 == 0 and (b*b) % 6 == 1",  # mixed moduli in a conjunction
    "a % 4 < 3",                           # comparison other than ==/!=
    "(a % 4 == 0) or (a < b)",             # a non-modular comparison atom
    "min(a, b) % 3 == 0",                  # min is not a pure polynomial
    "(a / 2) % 4 == 1",                    # division in the poly
    "(a % 5 == 5) or (b % 5 == 0)",        # out-of-range residue (c == m) via _atom guard
])
def test_classify_rejects_out_of_fragment(bad):
    assert bd.classify_boolean(bad) is None


def test_classify_declines_lean_decided_fragment():
    # disjoint-by-construction (review #5): the shapes lean_decided owns are DEFERred here
    for owned in ["(a*a + b*b) % 4 != 3",                    # bare atom
                  "(a*a) % 5 == 0 or (a*a) % 5 == 1",        # single-poly residue-set
                  "(a*a) % 4 != 3 and (b*b) % 4 != 3"]:      # plain conjunction (lean_decided's Path A? no — modular conj)
        assert bd.classify_boolean(owned) is None


def test_classify_declines_content_free_tautologies():
    # non-triviality (review #1): propositional tautologies/contradictions carry no modular content
    for triv in ["(a % 2 == 0) == (a % 2 == 0)",             # P ↔ P
                 "(a % 3 == 0) or (not (a % 3 == 0))",        # P ∨ ¬P (excluded middle, via not)
                 "(a % 3 == 0) or (a % 3 != 0)",              # P ∨ ¬P (via !=)
                 "(a % 2 == 0) == (not (a % 2 != 0))",        # P ↔ ¬¬P
                 "(a % 2 == 0) and (a % 2 != 0)"]:            # P ∧ ¬P (contradiction)
        assert bd.classify_boolean(triv) is None
    # a GENUINE modular biconditional is NOT content-free → accepted
    assert bd.classify_boolean("((a*b) % 3 == 0) == ((a % 3 == 0) or (b % 3 == 0))") is not None


def test_classify_dedups_atoms_for_bridges():
    # the same atom appearing twice yields ONE bridge (one rw rewrites all occurrences)
    s = bd.classify_boolean("(a % 3 == 0) or ((a % 3 == 0) and (b % 3 == 1))")
    keys = {(str(p), c) for p, c in s.atoms}
    assert len(keys) == len(s.atoms) and len(s.atoms) == 2      # {a%3=0, b%3=1}, deduped


# --- proof construction ---------------------------------------------------------------------------

def test_boolean_proof_structure():
    s = bd.classify_boolean("((a*b) % 3 == 0) == ((a % 3 == 0) or (b % 3 == 0))")
    body = bd.boolean_proof(s, ["a", "b"], n_domain=2)
    assert body.startswith("by\n  intro a b _ _ _ _")           # 2 vars + 2 box + 2 domain
    assert "have key : ∀ (a b : ZMod 3)" in body and ":= by decide" in body
    assert body.count("ZMod.intCast_eq_intCast_iff'") == len(s.atoms)   # one bridge per distinct atom
    assert "push_cast" in body and body.rstrip().endswith("exact key a b")
    # LAW leg has one fewer domain antecedent
    assert bd.boolean_proof(s, ["a", "b"], n_domain=1).startswith("by\n  intro a b _ _ _\n")


def test_hyp_base_avoids_collision():
    assert bd._hyp_base(["a", "b"], "hb") == "hb"
    assert bd._hyp_base(["a", "hb0"], "hb") == "hbhb"           # a variable named hb0 → escalate


def test_neq_atoms_normalized_and_rendered_as_not_eq():
    # a `!=` atom sets has_neq → the proof `simp only [ne_eq]` (a `≠`/Ne hides its `=` from `rw`), and
    # _zmod_prop renders it as `¬ (…=…)` so the key matches the ne_eq-normalized goal.
    s = bd.classify_boolean("((a*b) % 2 != 1) == ((a % 2 == 0) or (b % 2 == 0))")
    assert s.has_neq is True
    body = bd.boolean_proof(s, ["a", "b"], n_domain=1)
    assert "simp only [ne_eq]" in body and "(¬ ((a * b) = 1))" in body
    # a formula with no neq atom does NOT emit ne_eq (simp only would otherwise fail "no progress")
    s2 = bd.classify_boolean("((a*b) % 3 == 0) == ((a % 3 == 0) or (b % 3 == 0))")
    assert s2.has_neq is False and "ne_eq" not in bd.boolean_proof(s2, ["a", "b"], n_domain=1)


# --- applies() + decide_certificate ---------------------------------------------------------------

def test_applies_multivar_boolean_in_budget():
    be = bd.BooleanDecidedFaithfulness(kernel=FakeKernel())
    assert be.applies(mkprop(*BICOND)) is True
    assert be.applies(mkprop("a>=0 and b>=0", "(a%4==0)==(b%6==0)", "a>=0 and b>=0")) is False   # mixed mod
    assert be.applies(mkprop("n >= 0", "(n%5==0) or (n%5==1)", "n >= 0")) is False               # 1-var
    assert be.applies(mkprop("a>=0 and b>=0", "(a*a+b*b)%97==3", "a>=0 and b>=0")) is False       # budget


def test_decide_certificate_pass_and_defer():
    data = dict(zip(["claim_domain", "claim_property", "established_domain"], BICOND))
    ok, detail = bd.decide_certificate(data, FakeKernel())
    assert ok and detail["property"]["axioms"] and detail["n_atoms"] == 3
    ok2, d2 = bd.decide_certificate(data, FakeKernel(reject_names=["property"]))   # false formula in real kernel
    assert not ok2 and "property" in d2["reason"]


def test_decide_certificate_bad_shape_and_vacuous():
    for bad in [{"claim_domain": "a>=0"}, "notadict", {"a": "b", "c": "d", "e": "f"}]:
        assert not bd.decide_certificate(bad, FakeKernel())[0]

    class Boom:
        def check_proof(self, *a):
            raise AssertionError("kernel must not be reached outside the fragment")
        def _run(self, *a):
            raise AssertionError("nope")
    ok, d = bd.decide_certificate(
        {"claim_domain": "a>=0 and b>=0", "claim_property": "(a%4==0)==(b%6==0)",
         "established_domain": "a>=0 and b>=0"}, Boom())
    assert not ok and "fragment" in d["reason"]


# --- statement binding + rechecker + fail-closed --------------------------------------------------

def test_register_installs_both_and_binds():
    gate = _gate_with_backend(FakeKernel())
    assert bd.KIND in gate.recheckers and bd.KIND in gate.templates
    p = mkprop(*BICOND)
    assert gate.check(p).verdict is Verdict.PASS


def test_gate_refuses_tampered_statement():
    gate = _gate_with_backend(FakeKernel())
    p = mkprop(*BICOND)
    orig = gate.sound_backends[-1].check
    def tampered(prop):
        vv = orig(prop)
        if vv.certificate is not None:
            vv.certificate.detail["statement"] = "theorem evil : True"
        return vv
    gate.sound_backends[-1].check = tampered
    assert gate.check(p).verdict is not Verdict.PASS


def test_rechecker_rederives_and_rejects_tampering():
    recheck = bd.make_rechecker(FakeKernel())
    data = dict(zip(["claim_domain", "claim_property", "established_domain"], BICOND))
    good = Certificate(kind=bd.KIND, rechecked=True, data=data,
                       detail={"statement": bd.canonical_statement(**data)})
    assert recheck(good) is True
    assert recheck(Certificate(kind=bd.KIND, rechecked=True, data=data, detail={"statement": "nope"})) is False

    class S(str):
        pass
    spoof = Certificate(kind=bd.KIND, rechecked=True, data=data,
                        detail={"statement": S(bd.canonical_statement(**data))})
    assert recheck(spoof) is False
    assert recheck(Certificate(kind=bd.KIND, rechecked=True, data={"x": 1}, detail={"statement": "y"})) is False


def test_rechecker_defers_when_kernel_rejects_property():
    recheck = bd.make_rechecker(FakeKernel(reject_names=["property"]))
    data = dict(zip(["claim_domain", "claim_property", "established_domain"], BICOND))
    cert = Certificate(kind=bd.KIND, rechecked=True, data=data,
                       detail={"statement": bd.canonical_statement(**data)})
    assert recheck(cert) is False


def test_fail_closed_without_registration():
    assert bd.KIND not in _bare_gate().recheckers


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_certifies_true_and_defers_false():  # pragma: no cover
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.verifiers import LeanVerifier
    if not available():
        pytest.skip("Lean image unavailable")
    be = LeanReplBackend(timeout_s=150)
    try:
        kernel = LeanVerifier(be)
        assert bd.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], BICOND)), kernel)[0]
        false_b = ("a >= 0 and b >= 0", "((a*b) % 3 == 0) == (a % 3 == 0)", "a >= 0 and b >= 0")
        assert not bd.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], false_b)), kernel)[0]
    finally:
        be.close()

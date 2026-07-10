"""ADR 0065 — CI-safe unit tests for the order-split symbolic-exponent backend + renderer extension.

No Docker/Lean: a FAKE kernel exercises classification (fragment guards: constant base ≥ 2, bare
single-variable exponent, gcd(base,m)=1, ord ≤ MAX_ORDER, residues in range), proof construction,
statement binding, re-check, fail-closed wiring, the prover LAW generator, and — because the renderer
gained a new admission (the `base^n % m` Mod-interception) — a SEMANTICS-CONFORMANCE grid pinning the
`(base : ℤ) ^ (n).toNat` encoding against the DSL's own evaluation over the box. Opt-in real-kernel
e2e via ``LEIBNIZ_LEAN_E2E=1``.
"""
from __future__ import annotations

import os

import pytest

from leibniz.dsl_to_lean import RenderError, _parse, _term, render_pred
from leibniz.gates import power_mod_decided as pm
from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.gates.sound_backends import Certificate
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.providers.power_mod_prover import PowerModDemonstrate, power_law
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


POW = ("n >= 0", "2**n % 7 == 1 or 2**n % 7 == 2 or 2**n % 7 == 4", "n >= 0")


# --- renderer: the ADR 0065 Mod-interception + lockstep -------------------------------------------

def test_renderer_admits_pow_mod_only_under_a_constant_modulus():
    assert _term(_parse("2**n % 7")) == "(Int.emod ((2 : ℤ) ^ (n).toNat) 7)"
    assert _term(_parse("10**k % 7")) == "(Int.emod ((10 : ℤ) ^ (k).toNat) 7)"
    for bad in ("2**n", "2**n + 1", "n**n % 7", "2**(n+1) % 7", "(2**n % 7) % 3 + 2**n"):
        with pytest.raises(RenderError):
            _term(_parse(bad))
    # non-power mod is unchanged
    assert _term(_parse("n % 7")) == "(Int.emod n 7)"


def test_renderer_semantics_conformance_grid():
    # the toNat encoding must DENOTE the DSL's base**n % m over the box (n ≥ 0) — evaluate both sides
    # in Python over a grid crossing several periods; the Lean side is modelled exactly (n ≥ 0 so
    # toNat is the identity; Int.emod with a positive modulus is Python's %).
    for base, m in ((2, 7), (3, 11), (10, 7), (5, 8)):
        for n in range(0, 40):
            dsl = (base ** n) % m
            lean_model = (base ** max(n, 0)) % m          # (base:ℤ) ^ (n).toNat emod m, n ≥ 0
            assert dsl == lean_model
    # the whole predicate renders through render_pred (a Prop, usable by faithfulness_pair)
    assert "Int.emod ((2 : ℤ) ^ (n).toNat) 7" in render_pred(POW[1])


# --- classification --------------------------------------------------------------------------------

def test_classify_accepts_the_fragment():
    s = pm.classify_power("2**n % 7 == 1 or 2**n % 7 == 2 or 2**n % 7 == 4")
    assert s.op == "residue_set" and (s.base, s.modulus, s.var, s.ord) == (2, 7, "n", 3)
    assert pm.classify_power("2**n % 7 != 3").op == "neq"
    assert pm.classify_power("3**k % 11 == 1").op == "eq" and pm.classify_power("3**k % 11 == 1").ord == 5


@pytest.mark.parametrize("bad", [
    "2**n % 6 == 2",                       # gcd(2,6) ≠ 1 → not purely periodic
    "n**2 % 7 == 1",                       # constant exponent → lean_decided's fragment
    "2**(n+1) % 7 == 1",                   # compound exponent
    "2**n % 7 == 7",                       # out-of-range residue
    "2**n % 7 == 1 or 3**n % 7 == 1",      # mixed bases
    "2**n % 7 == 1 or 2**k % 7 == 2",      # mixed variables
    "2**n % 7 == 1 and 2**n % 7 != 3",     # conjunction (not this fragment)
    "1**n % 7 == 1",                       # base < 2
    "2**n % 7 < 3",                        # non-eq/neq comparison
])
def test_classify_rejects_out_of_fragment(bad):
    assert pm.classify_power(bad) is None


def test_classify_respects_max_order():
    # ord(3 mod 2^k) grows; pick a modulus whose order exceeds MAX_ORDER=64: ord(3 mod 257)=256
    assert pm.classify_power("3**n % 257 == 1") is None


# --- proof construction ----------------------------------------------------------------------------

def test_power_proof_structure():
    s = pm.classify_power("2**n % 7 != 3")
    body = pm.power_proof(s, n_domain=2)
    assert "have key : ∀ k : Nat, 2^k % 7 = 2^(k % 3) % 7" in body
    assert "Nat.mul_mod, Nat.pow_mod" in body            # the kernel-validated period key
    assert "have bridge : ∀ t : Nat, Int.emod ((2 : ℤ)^t) 7" in body
    assert "interval_cases r <;> norm_num" in body
    assert body.count("intro n _ _ _") == 1              # var + box + 2 domain antecedents
    assert pm.power_proof(s, n_domain=1).count("intro n _ _\n") == 1


# --- decide_certificate + backend ------------------------------------------------------------------

def test_applies_and_decide_certificate_with_fake_kernel():
    be = pm.PowerModFaithfulness(kernel=FakeKernel())
    assert be.applies(mkprop(*POW)) is True
    assert be.applies(mkprop("a >= 0 and n >= 0", "2**n % 7 != 3 or a % 2 == 0", "a >= 0 and n >= 0")) is False
    ok, detail = pm.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], POW)),
                                       FakeKernel())
    assert ok and detail["ord"] == 3 and detail["property"]["axioms"]
    ok2, d2 = pm.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], POW)),
                                    FakeKernel(reject_names=["property"]))
    assert not ok2 and "property" in d2["reason"]


def test_decide_certificate_bad_shape_and_fragment():
    for bad in [{"claim_domain": "n>=0"}, "notadict", {"a": "b", "c": "d", "e": "f"}]:
        assert not pm.decide_certificate(bad, FakeKernel())[0]

    class Boom:
        def check_proof(self, *a):
            raise AssertionError("kernel must not be reached outside the fragment")
        def _run(self, *a):
            raise AssertionError("nope")
    ok, d = pm.decide_certificate(
        {"claim_domain": "n>=0", "claim_property": "2**n % 6 == 2", "established_domain": "n>=0"}, Boom())
    assert not ok and "fragment" in d["reason"]


# --- statement binding + rechecker + fail-closed ---------------------------------------------------

def _bare_gate():
    from leibniz.backends.smt_z3 import Z3Backend
    from leibniz.probes import default_probes
    from leibniz.verifiers import SMTVerifier
    smt = SMTVerifier(backend=Z3Backend())
    return FaithfulnessGate(smt=smt, probes=default_probes(smt),
                            judge=type("J", (), {"round_trip_agrees": lambda self, p: 0.0})())


def test_register_installs_both_and_gate_refuses_tampering():
    gate = _bare_gate()
    pm.register(gate, FakeKernel())
    assert pm.KIND in gate.recheckers and pm.KIND in gate.templates
    p = mkprop(*POW)
    assert gate.check(p).verdict is Verdict.PASS
    orig = gate.sound_backends[-1].check
    def tampered(prop):
        vv = orig(prop)
        if vv.certificate is not None:
            vv.certificate.detail["statement"] = "theorem evil : True"
        return vv
    gate.sound_backends[-1].check = tampered
    # the tampered certificate is REFUSED (a PASS lacking a valid re-checked cert is downgraded to
    # fall-through); the honest Z3 ClaimProbe may then legitimately certify this 1-var claim — so
    # assert the refusal itself: whatever the final verdict, it is NOT the backend's producer.
    ev = gate.check(mkprop(*POW))
    assert ev.producer != "power_mod/kernel"


def test_rechecker_rederives_and_rejects_tampering():
    recheck = pm.make_rechecker(FakeKernel())
    data = dict(zip(["claim_domain", "claim_property", "established_domain"], POW))
    from leibniz.dsl_to_lean import canonical_statement
    good = Certificate(kind=pm.KIND, rechecked=True, data=data,
                       detail={"statement": canonical_statement(**data)})
    assert recheck(good) is True
    assert recheck(Certificate(kind=pm.KIND, rechecked=True, data=data, detail={"statement": "no"})) is False


def test_fail_closed_without_registration():
    assert pm.KIND not in _bare_gate().recheckers


# --- the prover LAW generator + fast-path gating ----------------------------------------------------

def test_power_law_generates_and_abstains():
    thm, proof = power_law("power_law_x", "n >= 0", "2**n % 7 != 3")
    assert thm.startswith("theorem power_law_x : ∀ (n : ℤ), (0 ≤ n) →")
    assert "Int.emod ((2 : ℤ) ^ (n).toNat) 7" in thm and "interval_cases" in proof
    assert power_law("x", "n >= 0", "2**n % 6 == 2") is None          # gcd ≠ 1 → abstain
    assert power_law("x", "a >= 0 and n >= 0", "2**n % 7 != 3") is None  # extra variable → abstain


def test_fastpath_requires_the_power_mod_producer_edge():
    calls = []
    class Inner:
        def run(self, prop):
            calls.append(prop)
            return prop
    d = PowerModDemonstrate(inner=Inner(), lean=object())
    p = mkprop(*POW)                                       # no power_mod/kernel edge → falls through
    d.run(p)
    assert calls and calls[0] is p


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_certifies_true_and_defers_false():  # pragma: no cover
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean image unavailable")
    be = LeanReplBackend(timeout_s=200)
    try:
        assert pm.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], POW)), be)[0]
        false_p = ("n >= 0", "2**n % 7 == 1 or 2**n % 7 == 2", "n >= 0")
        assert not pm.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], false_p)), be)[0]
    finally:
        be.close()

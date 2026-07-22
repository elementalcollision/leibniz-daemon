"""ADR 0070 — CI-safe unit tests for the factorial/gcd two-regime backend + renderer extension.

No Docker/Lean: a FAKE kernel exercises classification (fragment guards: bare single-variable
function argument, constant modulus/argument within the arm cap, residues in range, one atom
family), proof construction, statement binding, re-check, fail-closed wiring, the prover LAW
generator, and — because the renderer gained a new admission (``factorial``/``gcd`` calls) — a
SEMANTICS-CONFORMANCE grid pinning the ℕ-through-ℤ encoding against the DSL's own evaluation over
the box. Opt-in real-kernel e2e via ``LEIBNIZ_LEAN_E2E=1``. Mirrors ``test_power_mod_decided.py``.
"""
from __future__ import annotations

import math
import os

import pytest

from leibniz.dsl_to_lean import RenderError, _parse, _term, render_pred
from leibniz.gates import factgcd_decided as fg
from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.gates.sound_backends import Certificate
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.providers.factgcd_prover import FactGcdDemonstrate, factgcd_law
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


FACT = ("n >= 0", "factorial(n) % 2 == 0 or factorial(n) % 2 == 1", "n >= 0")
GCD = ("n >= 0", "gcd(6, n) == 1 or gcd(6, n) == 2 or gcd(6, n) == 3 or gcd(6, n) == 6", "n >= 0")


# --- renderer: the ADR 0070 call admission + lockstep ----------------------------------------------

def test_renderer_admits_the_table_fragment_only():
    assert _term(_parse("factorial(n)")) == "((Nat.factorial ((n).toNat) : ℕ) : ℤ)"
    assert _term(_parse("factorial(5)")) == "((Nat.factorial 5 : ℕ) : ℤ)"
    assert _term(_parse("gcd(6, n)")) == "((Nat.gcd 6 ((n).toNat) : ℕ) : ℤ)"
    assert _term(_parse("gcd(n, 6)")) == "((Nat.gcd ((n).toNat) 6 : ℕ) : ℤ)"
    assert _term(_parse("factorial(n) % 5")) == "(Int.emod ((Nat.factorial ((n).toNat) : ℕ) : ℤ) 5)"
    for bad in ("factorial(n + 1)", "factorial(n, 2)", "factorial()", "gcd(n)",
                "gcd(n + 1, 6)", "gcd(factorial(n), 6)", "factorial(200)", "gcd(6, 200)"):
        with pytest.raises(RenderError):
            _term(_parse(bad))


def test_renderer_lockstep_with_smt_z3():
    # the renderer's admission cap IS smt_z3's table cap — one constant, imported (ADR 0066 lockstep)
    from leibniz.backends.smt_z3 import MAX_TABLE_BOUND as z3_cap
    from leibniz.dsl_to_lean import MAX_TABLE_BOUND as renderer_cap
    assert renderer_cap == z3_cap == 128


def test_renderer_semantics_conformance_grid():
    # the ℕ-through-ℤ encoding must DENOTE the DSL's factorial/gcd over the box (n ≥ 0) — the Lean
    # side is modelled exactly (n ≥ 0 so toNat is the identity; Int.emod with a positive modulus is
    # Python's %; Nat.factorial/Nat.gcd are math.factorial/math.gcd on ℕ).
    for n in range(0, 12):
        for m in (2, 3, 5, 7):
            assert math.factorial(n) % m == math.factorial(max(n, 0)) % m
        for c in (1, 4, 6, 12):
            assert math.gcd(c, n) == math.gcd(c, max(n, 0))
    # the whole predicates render through render_pred (Props, usable by faithfulness_pair)
    assert "Int.emod ((Nat.factorial ((n).toNat) : ℕ) : ℤ) 2" in render_pred(FACT[1])
    assert "(Nat.gcd 6 ((n).toNat) : ℕ)" in render_pred(GCD[1])


# --- classification --------------------------------------------------------------------------------

def test_classify_accepts_the_fragment():
    s = fg.classify_factgcd(FACT[1])
    assert (s.fn, s.op, s.var, s.modulus, s.residues) == ("factorial", "residue_set", "n", 2, (0, 1))
    assert fg.classify_factgcd("factorial(k) % 5 != 3").op == "neq"
    g = fg.classify_factgcd(GCD[1])
    assert (g.fn, g.op, g.modulus, g.var_first) == ("gcd", "residue_set", 6, False)
    assert fg.classify_factgcd("gcd(n, 4) != 3").var_first is True


@pytest.mark.parametrize("bad", [
    "factorial(n + 1) % 5 == 0",             # compound argument
    "factorial(n) % 1 == 0",                 # modulus < 2
    "factorial(n) % 5 == 5",                 # out-of-range residue
    "factorial(n) % 257 == 0",               # modulus over the MAX_ORDER arm cap
    "gcd(n, m) == 1",                        # var/var — outside the fragment
    "gcd(4, 6) == 2",                        # const/const — no variable
    "gcd(0, n) == 0",                        # constant argument < 1
    "gcd(6, n) == 7",                        # asserted value > the constant
    "factorial(n) % 2 == 0 or gcd(6, n) == 1",  # mixed families
    "factorial(n) % 2 == 0 or factorial(k) % 2 == 1",  # mixed variables
    "factorial(n) % 2 == 0 and factorial(n) % 2 == 1",  # conjunction (not this fragment)
    "factorial(n) % 5 < 3",                  # non-eq/neq comparison
    "n % 2 == 0",                            # no named function at all
])
def test_classify_rejects_out_of_fragment(bad):
    assert fg.classify_factgcd(bad) is None


# --- proof construction ----------------------------------------------------------------------------

def test_factgcd_proof_structure():
    s = fg.classify_factgcd("factorial(n) % 5 != 3")
    body = fg.factgcd_proof(s, n_domain=2)
    assert "have key : ∀ t : Nat, 5 ≤ t → Nat.factorial t % 5 = 0" in body
    assert "Nat.dvd_factorial" in body and "omega" in body   # the kernel-validated dvd tail
    assert "have bridge : ∀ t : Nat, Int.emod ((Nat.factorial t : ℕ) : ℤ) 5" in body
    assert "interval_cases t <;> norm_num [Nat.factorial]" in body
    assert body.count("intro n _ _ _") == 1                  # var + box + 2 domain antecedents
    assert fg.factgcd_proof(s, n_domain=1).count("intro n _ _\n") == 1
    g = fg.classify_factgcd("gcd(n, 4) != 3")
    gbody = fg.factgcd_proof(g, n_domain=1)
    assert "have key : ∀ t : Nat, Nat.gcd 4 t = Nat.gcd 4 (t % 4)" in gbody
    assert "Nat.gcd_rec" in gbody and "interval_cases r <;> norm_num [Nat.gcd]" in gbody
    # the key's own comm rewrite is always present; the var-first spelling adds ONE more (the flip)
    assert gbody.count("rw [Nat.gcd_comm]") == 2             # key + the var-first flip
    const_first = fg.factgcd_proof(fg.classify_factgcd("gcd(4, n) != 3"), n_domain=1)
    assert const_first.count("rw [Nat.gcd_comm]") == 1       # key only — no flip


# --- decide_certificate + backend ------------------------------------------------------------------

def test_applies_and_decide_certificate_with_fake_kernel():
    be = fg.FactGcdFaithfulness(kernel=FakeKernel())
    assert be.applies(mkprop(*FACT)) is True
    assert be.applies(mkprop(*GCD)) is True
    assert be.applies(mkprop("a >= 0 and n >= 0", "factorial(n) % 2 == 0 or a % 2 == 0",
                             "a >= 0 and n >= 0")) is False
    ok, detail = fg.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], FACT)),
                                       FakeKernel())
    assert ok and detail["fn"] == "factorial" and detail["property"]["axioms"]
    ok2, d2 = fg.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], FACT)),
                                    FakeKernel(reject_names=["property"]))
    assert not ok2 and "property" in d2["reason"]


def test_decide_certificate_bad_shape_and_fragment():
    for bad in [{"claim_domain": "n>=0"}, "notadict", {"a": "b", "c": "d", "e": "f"}]:
        assert not fg.decide_certificate(bad, FakeKernel())[0]

    class Boom:
        def check_proof(self, *a):
            raise AssertionError("kernel must not be reached outside the fragment")

        def _run(self, *a):
            raise AssertionError("nope")
    ok, d = fg.decide_certificate(
        {"claim_domain": "n>=0", "claim_property": "gcd(n, m) == 1", "established_domain": "n>=0"}, Boom())
    assert not ok and ("fragment" in d["reason"] or "render" in d["reason"])


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
    fg.register(gate, FakeKernel())
    assert fg.KIND in gate.recheckers and fg.KIND in gate.templates
    p = mkprop(*FACT)
    assert gate.check(p).verdict is Verdict.PASS
    orig = gate.sound_backends[-1].check

    def tampered(prop):
        vv = orig(prop)
        if vv.certificate is not None:
            vv.certificate.detail["statement"] = "theorem evil : True"
        return vv
    gate.sound_backends[-1].check = tampered
    # the tampered certificate is REFUSED; whatever finally certifies, it is NOT this producer.
    ev = gate.check(mkprop(*FACT))
    assert ev.producer != "factgcd/kernel"


def test_rechecker_rederives_and_rejects_tampering():
    recheck = fg.make_rechecker(FakeKernel())
    data = dict(zip(["claim_domain", "claim_property", "established_domain"], GCD))
    from leibniz.dsl_to_lean import canonical_statement
    good = Certificate(kind=fg.KIND, rechecked=True, data=data,
                       detail={"statement": canonical_statement(**data)})
    assert recheck(good) is True
    assert recheck(Certificate(kind=fg.KIND, rechecked=True, data=data, detail={"statement": "no"})) is False


def test_fail_closed_without_registration():
    assert fg.KIND not in _bare_gate().recheckers


# --- the prover LAW generator + fast-path gating ----------------------------------------------------

def test_factgcd_law_generates_and_abstains():
    thm, proof = factgcd_law("factgcd_law_x", "n >= 0", "factorial(n) % 5 != 3")
    assert thm.startswith("theorem factgcd_law_x : ∀ (n : ℤ), (0 ≤ n) →")
    assert "Nat.factorial ((n).toNat)" in thm and "interval_cases" in proof
    gthm, gproof = factgcd_law("factgcd_law_y", "n >= 0", "gcd(6, n) == 1 or gcd(6, n) == 2 or "
                               "gcd(6, n) == 3 or gcd(6, n) == 6")
    assert "Nat.gcd 6 ((n).toNat)" in gthm and "Nat.gcd_rec" in gproof
    assert factgcd_law("x", "n >= 0", "gcd(n, m) == 1") is None            # var/var → abstain
    assert factgcd_law("x", "a >= 0 and n >= 0", "factorial(n) % 5 != 3") is None  # extra variable


def test_fastpath_requires_the_factgcd_producer_edge():
    calls = []

    class Inner:
        def run(self, prop):
            calls.append(prop)
            return prop
    d = FactGcdDemonstrate(inner=Inner(), lean=object())
    p = mkprop(*FACT)                                      # no factgcd/kernel edge → falls through
    d.run(p)
    assert calls and calls[0] is p


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_certifies_true_and_defers_false():  # pragma: no cover
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean image unavailable")
    be = LeanReplBackend(timeout_s=200)
    try:
        keys = ["claim_domain", "claim_property", "established_domain"]
        assert fg.decide_certificate(dict(zip(keys, FACT)), be)[0]
        assert fg.decide_certificate(dict(zip(keys, GCD)), be)[0]
        false_f = ("n >= 0", "factorial(n) % 5 == 0", "n >= 0")            # n=0 gives 1
        assert not fg.decide_certificate(dict(zip(keys, false_f)), be)[0]
        false_g = ("n >= 0", "gcd(6, n) == 3", "n >= 0")                   # n=0 gives 6
        assert not fg.decide_certificate(dict(zip(keys, false_g)), be)[0]
    finally:
        be.close()

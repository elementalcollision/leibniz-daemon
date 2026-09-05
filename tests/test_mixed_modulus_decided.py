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
    "(a % 1000 == 0) == (a % 999 == 0)",                     # lcm=999000 > MAX_LCM (ADR 0088)
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
    # ADR 0076: 1-var is now in-fragment; pin the arity guard with 4 vars instead.
    assert be.applies(mkprop("a >= 0 and b >= 0 and c >= 0 and d >= 0",
                             "(a*b*c*d % 6 == 1) == (a % 2 == 1)", "a >= 0 and b >= 0 and c >= 0 and d >= 0")) is False


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
    if not available():
        pytest.skip("Lean image unavailable")
    be = LeanReplBackend(timeout_s=150)
    try:
        kernel = be                      # decide_certificate wants the BACKEND's check_proof
        assert mm.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], MIXED)), kernel)[0]
        false_m = ("a >= 0 and b >= 0", "((a+b)**2 % 4 == 1) == ((a+b) % 2 == 0)", "a >= 0 and b >= 0")
        assert not mm.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], false_m)), kernel)[0]
    finally:
        be.close()



# --- ADR 0088: the widened caps, what they must NOT widen, and where they stop -------------------

#: A genuine covering system with lcm 2520 (chain construction; verified below). 18 atoms, 147 AST
#: nodes — inside `smt_z3.MAX_NODES`, so this one is reachable through the DSL today. Its lcm is
#: 39x the pre-ADR-0088 `MAX_LCM` of 64, so it exercises the widening rather than assuming it.
COVERING_2520 = [
    (7, 1), (7, 2), (7, 3), (7, 4), (7, 5), (7, 6),
    (35, 7), (35, 14), (35, 21), (35, 28), (105, 35), (105, 70),
    (315, 105), (315, 210), (630, 315), (1260, 630), (2520, 1260), (2520, 0),
]

#: arXiv 2607.19029 §7 — the distinct covering system with minimum modulus 7 and lcm 10080. 66
#: congruences; the moduli are exactly the 66 divisors of 10080 that are >= 7. Transcribed from the
#: paper's PDF and verified exhaustively (0 uncovered residues). Kernel-verified standalone in
#: Lean 4.31 (16s, clean axioms) — but NOT reachable through the DSL: see the blocker test below.
COVERING_10080 = [
    (7, 6), (8, 7), (9, 8), (10, 6), (12, 9), (14, 8), (15, 12), (16, 3),
    (18, 14), (20, 0), (21, 4), (24, 13), (28, 26), (30, 24), (32, 27), (35, 33),
    (36, 5), (40, 11), (42, 16), (45, 2), (48, 1), (56, 52), (60, 30), (63, 7),
    (70, 28), (72, 29), (80, 59), (84, 10), (90, 74), (96, 43), (105, 93), (112, 73),
    (120, 64), (126, 112), (140, 38), (144, 65), (160, 43), (168, 121), (180, 110), (210, 18),
    (224, 169), (240, 185), (252, 154), (280, 248), (288, 203), (315, 128), (336, 313), (360, 209),
    (420, 292), (480, 75), (504, 217), (560, 404), (630, 578), (672, 505), (720, 281), (840, 472),
    (1008, 553), (1120, 233), (1260, 532), (1440, 875), (1680, 124), (2016, 281), (2520, 2044),
    (3360, 2153), (5040, 5033), (10080, 7193),
]


def _covering_property(system):
    return " or ".join(f"(n % {m} == {a})" for m, a in system)


def _covers(system, M):
    hit = [False] * M
    for m, a in system:
        for x in range(a % m, M, m):
            hit[x] = True
    return all(hit)


def test_covering_fixtures_actually_cover():
    """The fixtures are only meaningful if they cover Z. Verified, not assumed — a mistranscribed
    residue would otherwise turn every test below into a test of the wrong object."""
    assert _covers(COVERING_2520, 2520)
    assert _covers(COVERING_10080, 10080)
    mods = [m for m, _ in COVERING_10080]
    assert len(COVERING_10080) == 66 and len(set(mods)) == 66 and min(mods) == 7
    assert sorted(mods) == sorted(d for d in range(7, 10081) if 10080 % d == 0)


def test_widened_caps_admit_a_real_covering_system():
    """ADR 0088's point, exercised end-to-end through the DSL: lcm 2520 classifies. Under the old
    caps (MAX_LCM 64) every covering system was excluded from the fragment."""
    skel = mm.classify_mixed(_covering_property(COVERING_2520))
    assert skel is not None and skel.M == 2520 and len(skel.atoms) == 18


def test_covering_10080_is_blocked_at_the_dsl_parse_boundary():
    """KNOWN BLOCKER, pinned so it is documented rather than mysterious.

    The paper's 66-congruence system is 531 AST nodes against `smt_z3.MAX_NODES = 200`, so it is
    refused by `dsl_to_lean._parse` before the classifier ever sees it. That cap is NOT one of
    ADR 0088's compute budgets: it guards recursion on untrusted input and is imported by BOTH the
    Z3 backend and the Lean renderer to keep their admitted grammars in lockstep. Raising it is a
    separate decision with its own review, so it was deliberately left alone.

    Consequence: `MIXED_MAX_ATOMS = 72` is currently unreachable — MAX_NODES binds first, at 24
    congruences. Update this test when that cap is decided."""
    import ast as _ast
    from leibniz.backends.smt_z3 import MAX_NODES
    from leibniz.dsl_to_lean import RenderError, _parse
    prop = _covering_property(COVERING_10080)
    assert sum(1 for _ in _ast.walk(_ast.parse(prop, mode="eval"))) > MAX_NODES
    with pytest.raises(RenderError, match="too large"):
        _parse(prop)
    assert mm.classify_mixed(prop) is None
    # the effective ceiling today, so a later widening has a number to move
    assert mm.classify_mixed(_covering_property(COVERING_10080[:24])) is not None
    assert mm.classify_mixed(_covering_property(COVERING_10080[:25])) is None


def test_widening_did_not_touch_the_shared_budgets():
    """The mixed fragment carries its OWN budgets. Raising the shared constants in place would
    silently widen the single-modulus and boolean procedures too — `modulus ** nvars` at 20160
    admits 2-var claims at M~142 and 3-var at M~27, cells nobody measured. Mutation guard: point
    the mixed classifier back at the shared constants and this goes red."""
    from leibniz.gates import boolean_decided, lean_decided
    assert lean_decided.MAX_RESIDUE_CELLS == 4096
    assert boolean_decided.MAX_ATOMS == 8
    assert mm.MAX_LCM == 20160 and mm.MIXED_MAX_CELLS == 20160 and mm.MIXED_MAX_ATOMS == 72


def test_max_lcm_still_binds():
    assert mm.classify_mixed("(a % 1000 == 0) == (a % 999 == 0)") is None      # lcm 999000
    assert mm.classify_mixed("(a % 160 == 0) == (a % 126 == 0)") is not None   # lcm 10080, in


def test_cell_budget_is_widened_for_ONE_variable_only():
    """Adversarial review killed the first version of this test twice over.

    (1) Its negative case was `(a % 143 == 0) == (b % 143 == 0)` — ONE distinct modulus, so
        `classify_mixed` refuses it at `len(moduli) < 2` and the budget is never reached. The
        test passed with the budget effectively removed.
    (2) Its positive case asserted that `(a % 140 == 0) == (b % 20 == 0)` (2 vars, 19600 cells)
        was admitted — pinning as correct exactly the multi-variable widening that nothing in
        ADR 0088 measured.

    The budget is now `_cell_budget(nvars)`: widened at one variable, shared 4096 above."""
    assert mm._cell_budget(1) == 20160
    assert mm._cell_budget(2) == mm._cell_budget(3) == 4096      # NOT widened

    be = mm.MixedModulusFaithfulness(kernel=FakeKernel())

    # 1 var: above the old shared 4096, inside the measured widening -> admitted
    assert be.applies(mkprop("a >= 0", "(a % 160 == 0) == (a % 126 == 0)", "a >= 0"))   # M=10080

    # 2 vars: reaches the budget (two distinct moduli, M**2 > 4096) -> refused
    assert mm.classify_mixed("(a % 13 == 0) == (b % 11 == 0)") is not None              # M=143, in fragment
    assert not be.applies(mkprop("a >= 0 and b >= 0",
                                 "(a % 13 == 0) == (b % 11 == 0)", "a >= 0 and b >= 0"))  # 20449 cells

    # the case the review flagged: 2 vars at M=140 must NOT ride in on the 1-var widening
    assert not be.applies(mkprop("a >= 0 and b >= 0",
                                 "(a % 140 == 0) == (b % 20 == 0)", "a >= 0 and b >= 0"))  # 19600 cells

    # 2 vars inside the shared budget still works
    assert be.applies(mkprop("a >= 0 and b >= 0",
                             "(a % 9 == 0) == (b % 7 == 0)", "a >= 0 and b >= 0"))         # M=63, 3969


def test_non_triviality_guard_is_not_exponential():
    """Raising the atom cap without this branch does not merely slow the classifier, it HANGS it:
    `boolean_decided._content_free` enumerates 2**n assignments (256 at MAX_ATOMS = 8). Above that
    cap the mixed fragment admits only a flat disjunction, where constancy is exact and O(n)."""
    big = COVERING_10080[:20]
    prop = _covering_property(big)
    assert mm.classify_mixed(prop) is not None                       # content-bearing, admitted
    taut = prop + " or (n % 7 != 6)"                                 # p or not-p at the same scale
    assert mm.classify_mixed(taut) is None
    # a large NON-flat shape is refused rather than waved through on an unchecked guard
    assert mm.classify_mixed("(" + prop + ") and (n % 11 == 0)") is None


def test_key_decide_carries_its_options_and_kernel_reduction():
    """All three `set_option`s are load-bearing and each was found by a kernel run: without
    maxRecDepth `decide` dies at M~120; without the synthInstance limits a 66-atom disjunction
    fails to synthesize `Decidable`. They are scoped to the tactic, so the gate-owned proof stays
    self-contained — no file preamble for a caller to forget."""
    skel = mm.classify_mixed(_covering_property(COVERING_2520))
    proof = mm.mixed_proof(skel, ["n"], n_domain=1)
    assert "decide +kernel" in proof
    for opt in ("set_option maxRecDepth", "set_option synthInstance.maxSize",
                "set_option synthInstance.maxHeartbeats"):
        assert opt in proof, opt
    assert proof.index("have key") < proof.index("set_option maxRecDepth") < proof.index("decide +kernel")


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_decides_a_covering_system():  # pragma: no cover
    """ADR 0088 end-to-end: a genuine covering system CHECKS, and one with a residue class left
    uncovered does NOT. At this scale Lean may abort (stack overflow) on a near-miss rather than
    reject; `kernel_ok` requires returncode == 0, so either way the answer is not-verified. The
    kernel decides; the template never does."""
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean image unavailable")
    be = LeanReplBackend(timeout_s=600)
    try:
        kernel = be                      # decide_certificate wants the BACKEND's check_proof
        keys = ["claim_domain", "claim_property", "established_domain"]
        good = ("n >= 0", _covering_property(COVERING_2520), "n >= 0")
        assert mm.decide_certificate(dict(zip(keys, good)), kernel)[0]
        near_miss = ("n >= 0", _covering_property(COVERING_2520[:-1]), "n >= 0")
        assert not _covers(COVERING_2520[:-1], 2520)
        assert not mm.decide_certificate(dict(zip(keys, near_miss)), kernel)[0]
    finally:
        be.close()

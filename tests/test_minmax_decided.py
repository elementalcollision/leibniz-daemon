"""ADR 0059 (min/max half) — CI-safe unit tests for the order-split faithfulness backend.

No Docker/Lean: a FAKE kernel exercises the gate-owned classification (B.3 fragment guards), proof
construction, statement binding (B.2), re-check, and fail-closed wiring. An opt-in real-kernel test
(``LEIBNIZ_LEAN_E2E=1``) mirrors ``scratchpad/validate_minmax_e2e.py`` and is the ground-truth anchor.
"""
from __future__ import annotations

import os

import pytest

from leibniz.gates import minmax_decided as mm
from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.gates.sound_backends import Certificate
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimType, Verdict


class FakeKernel:
    """check_proof configurable by theorem-name marker; clean axiom footprint via _run."""

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


IDENTITY = ("a >= 0 and b >= 0", "max(a,b)**2 + min(a,b)**2 == a**2 + b**2", "a >= 0 and b >= 0")


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


# --- classification (B.3: the fragment gate lives at the classifier) ------------------------------

def test_classify_accepts_minmax_identities():
    s = mm.classify_identity("max(a,b)**2 + min(a,b)**2 == a**2 + b**2")
    assert s is not None and s.pairs == (("a", "b"),)
    s2 = mm.classify_identity("(max(a,b)+min(a,b)) + (max(b,c)+min(b,c)) == a + 2*b + c")
    assert s2 is not None and s2.pairs == (("a", "b"), ("b", "c"))


@pytest.mark.parametrize("bad", [
    "max(a, b, c) == a",              # ≥3-ary min/max (renderer admits it; classifier must reject)
    "max(a, min(b, c)) == a",         # nested min/max
    "max(a + 1, b) == a",             # compound (non-variable) argument
    "min(a, a) == a",                 # degenerate min(a,a)
    "max(a, b) < a + b",              # not an equality
    "min(a, b) != 0",                 # not an equality (NotEq)
    "a + b == b + a",                 # a pure-poly identity (no min/max) — not this backend's job
    "(a / 2) + max(a, b) == b",       # division in a side
    "(a % 2) + max(a, b) == b",       # modulo in a side
])
def test_classify_rejects_out_of_fragment(bad):
    assert mm.classify_identity(bad) is None


# --- ADR 0059 Path A: conjunction of Eq min/max identities ----------------------------------------

def test_classify_accepts_conjunction_of_eq_identities():
    s = mm.classify_identity("max(a,b)**2 + min(a,b)**2 == a**2 + b**2 and max(a,b)*min(a,b) == a*b")
    assert s is not None and s.n_eqs == 2 and s.pairs == (("a", "b"),)
    # union of pairs across conjuncts
    s2 = mm.classify_identity("max(a,b) + min(a,b) == a + b and max(b,c) + min(b,c) == b + c")
    assert s2 is not None and s2.n_eqs == 2 and s2.pairs == (("a", "b"), ("b", "c"))
    # a single Eq still classifies with n_eqs == 1
    assert mm.classify_identity("max(a,b) + min(a,b) == a + b").n_eqs == 1


@pytest.mark.parametrize("bad", [
    "max(a,b) == a and max(a, b, c) == b",       # a ≥3-ary conjunct
    "max(a,b) == a and (a % 2 == 0)",            # a non-min/max (modular) conjunct
    "max(a,b) == a and min(a,b) != b",           # a NotEq conjunct (only Eq admitted)
    "max(a,b) == a or min(a,b) == b",            # top-level Or, not And
    "max(a,b) == a and (min(a,b) == b and min(b,c) == c)",  # nested And conjunct (not a bare Eq)
])
def test_classify_rejects_bad_conjunctions(bad):
    assert mm.classify_identity(bad) is None


def test_classify_conjunction_respects_eq_cap():
    over = " and ".join([f"max(a,b) + min(a,b) == a + b"] * (mm.MAX_MINMAX_EQS + 1))
    assert mm.classify_identity(over) is None            # over MAX_MINMAX_EQS → DEFER


def test_conjunction_proof_splits_and_order_splits_each():
    s = mm.classify_identity("max(a,b)**2 + min(a,b)**2 == a**2 + b**2 and max(a,b)*min(a,b) == a*b")
    body = mm.identity_proof(s, ["a", "b"], n_domain=1)
    assert "refine ⟨?_, ?_⟩ <;>" in body and body.count("rcases le_total") == 1 and body.rstrip().endswith("ring)")


def test_classify_respects_branch_budget():
    # 3 vars → C(3,2)=3 pairs → 2^3 = 8 branches = MAX_MINMAX_BRANCHES (accepted); a 4th pair would exceed.
    ok = "(max(a,b)+min(a,b)) + (max(b,c)+min(b,c)) + (max(a,c)+min(a,c)) == 2*a + 2*b + 2*c"
    s = mm.classify_identity(ok)
    assert s is not None and len(s.pairs) == 3 and 2 ** len(s.pairs) == mm.MAX_MINMAX_BRANCHES


# --- proof construction ---------------------------------------------------------------------------

def test_identity_proof_splits_every_pair_and_references_only_existing_hyps():
    s = mm.classify_identity("(max(a,b)+min(a,b)) + (max(b,c)+min(b,c)) == a + 2*b + c")
    body = mm.identity_proof(s, ["a", "b", "c"], n_domain=2)
    assert body.startswith("by\n  intro a b c _ _ _ _ _")   # 3 vars + 3 box + 2 domain
    assert body.count("rcases le_total") == 2               # one per appearing pair
    assert "simp only [max_eq_left, max_eq_right, min_eq_left, min_eq_right, h0, h1]" in body
    assert body.rstrip().endswith("ring")
    # LAW leg introduces one fewer domain antecedent
    assert mm.identity_proof(s, ["a", "b", "c"], n_domain=1).startswith("by\n  intro a b c _ _ _ _\n")


def test_hyp_base_avoids_variable_name_collision():
    # ordinary variables → base "h"
    assert mm._hyp_base(["a", "b"]) == "h"
    # a variable literally named h0/h1 would be shadowed by the ordering hyp → base escalates
    assert mm._hyp_base(["a", "h0"]) == "hh"
    assert mm._hyp_base(["h0", "hh0"]) == "hhh"
    # the generated proof for such a claim uses the non-colliding base (no `with h0 | h0` over var h0)
    s = mm.classify_identity("max(a, h0) + min(a, h0) == a + h0")
    assert s is not None
    body = mm.identity_proof(s, ["a", "h0"], n_domain=1)
    assert "rcases le_total a h0 with hh0 | hh0" in body and "with h0 | h0" not in body


# --- applies(): routing / invariant-5 gate --------------------------------------------------------

def test_applies_only_multivar_minmax_identities():
    be = mm.MinMaxDecidedFaithfulness(kernel=FakeKernel())
    assert be.applies(mkprop(*IDENTITY)) is True
    # single variable → not applicable (MIN_VARS)
    assert be.applies(mkprop("n >= 0", "max(n, n) == n", "n >= 0")) is False
    # modular claim (lean_decided's fragment, not this one)
    assert be.applies(mkprop("a >= 0 and b >= 0", "(a*a + b*b) % 4 != 3", "a >= 0 and b >= 0")) is False
    # missing established_domain
    assert be.applies(mkprop("a >= 0 and b >= 0", "max(a,b) + min(a,b) == a + b", None)) is False


# --- decide_certificate (structural: builds + checks all four with the fake kernel) ---------------

def test_decide_certificate_pass_when_kernel_accepts_all():
    ok, detail = mm.decide_certificate(
        dict(zip(["claim_domain", "claim_property", "established_domain"], IDENTITY)), FakeKernel())
    assert ok and detail["property"]["axioms"] and detail["pairs"] == (("a", "b"),)


def test_decide_certificate_defers_when_property_rejected():
    # the false-identity / non-identity case in the real kernel: the property leg's `ring` fails → DEFER
    ok, detail = mm.decide_certificate(
        dict(zip(["claim_domain", "claim_property", "established_domain"], IDENTITY)),
        FakeKernel(reject_names=["property"]))
    assert not ok and "property" in detail["reason"]


def test_decide_certificate_defers_on_bad_data_shape():
    for bad in [{"claim_domain": "a>=0"}, {"claim_domain": 1, "claim_property": "x", "established_domain": "y"},
                "notadict", {"a": "b", "c": "d", "e": "f"}]:
        ok, _ = mm.decide_certificate(bad, FakeKernel())
        assert not ok


def test_decide_certificate_defers_outside_fragment_without_touching_kernel():
    class BoomKernel:
        def check_proof(self, *a):
            raise AssertionError("kernel must not be reached outside the fragment")
        def _run(self, *a):
            raise AssertionError("kernel must not be reached")
    ok, detail = mm.decide_certificate(
        {"claim_domain": "a >= 0 and b >= 0", "claim_property": "max(a, min(b, c)) == a",
         "established_domain": "a >= 0 and b >= 0"}, BoomKernel())
    assert not ok and "fragment" in detail["reason"]


# --- statement binding (B.2 / obligation 5) -------------------------------------------------------

def test_template_renders_from_prop_and_binds():
    tmpl = mm.prop_statement_template
    expected = tmpl(mkprop(*IDENTITY))
    assert expected is not None and "∀" in expected and "∃" in expected
    assert tmpl(mkprop("a >= 0 and b >= 0", "max(a,b) + min(a,b) == a + b", None)) is None


def test_register_installs_both_rechecker_and_template():
    gate = _gate_with_backend(FakeKernel())
    assert mm.KIND in gate.recheckers and mm.KIND in gate.templates      # B.2: BOTH


def test_gate_refuses_tampered_certificate_statement():
    gate = _gate_with_backend(FakeKernel())
    p = mkprop(*IDENTITY)
    assert gate.sound_backends[-1].check(p).verdict is Verdict.PASS
    assert gate.check(p).verdict is Verdict.PASS
    orig = gate.sound_backends[-1].check
    def tampered(prop):
        vv = orig(prop)
        if vv.certificate is not None:
            vv.certificate.detail["statement"] = "theorem evil : True"
        return vv
    gate.sound_backends[-1].check = tampered
    assert gate.check(p).verdict is not Verdict.PASS      # binding refuses → falls through


# --- make_rechecker -------------------------------------------------------------------------------

def test_rechecker_rederives_and_rejects_tampering():
    recheck = mm.make_rechecker(FakeKernel())
    data = dict(zip(["claim_domain", "claim_property", "established_domain"], IDENTITY))
    good = Certificate(kind=mm.KIND, rechecked=True, data=data,
                       detail={"statement": mm.canonical_statement(**data)})
    assert recheck(good) is True
    assert recheck(Certificate(kind=mm.KIND, rechecked=True, data=data, detail={"statement": "nope"})) is False
    class S(str):
        pass
    spoof = Certificate(kind=mm.KIND, rechecked=True, data=data,
                        detail={"statement": S(mm.canonical_statement(**data))})
    assert recheck(spoof) is False                        # builtin-str pin
    assert recheck(Certificate(kind=mm.KIND, rechecked=True, data={"x": 1}, detail={"statement": "y"})) is False


def test_rechecker_defers_when_kernel_rejects_property():
    recheck = mm.make_rechecker(FakeKernel(reject_names=["property"]))
    data = dict(zip(["claim_domain", "claim_property", "established_domain"], IDENTITY))
    cert = Certificate(kind=mm.KIND, rechecked=True, data=data,
                       detail={"statement": mm.canonical_statement(**data)})
    assert recheck(cert) is False


# --- fail-closed default (no registration → no PASS of this kind) ----------------------------------

def test_fail_closed_without_registration():
    # a gate that never registered the min/max kind cannot accept its certificate (no rechecker)
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
        ok, _ = mm.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], IDENTITY)), kernel)
        assert ok
        bad = ("a >= 0 and b >= 0", "max(a,b) + min(a,b) == a", "a >= 0 and b >= 0")   # false identity
        ok2, _ = mm.decide_certificate(dict(zip(["claim_domain", "claim_property", "established_domain"], bad)), kernel)
        assert not ok2
    finally:
        be.close()

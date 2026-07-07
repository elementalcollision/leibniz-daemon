"""ADR 0058 increment 1 — CI-safe tests for the deterministic modular-polynomial proof generator.

No Docker/Lean: structural + fragment-guard + determinism checks. An opt-in real-kernel test
(`LEIBNIZ_LEAN_E2E=1`) mirrors `scratchpad/validate_residue.py` (true laws proved, a false claim
rejected) and is the ground-truth anchor.
"""
from __future__ import annotations

import os

import pytest

from leibniz.providers import residue_prover as rp

D = "a >= 0 and b >= 0"

TRUE = [
    "(a*a + b*b) % 4 != 3",
    "(a*b*(a*a - b*b)) % 6 == 0",
    "((a*b)^2 + a*b) % 6 == 0 or ((a*b)^2 + a*b) % 6 == 2",   # the live claim
    "(a*a + a*b + b*b) % 3 != 2",
    "(a*a + b*b) % 4 == 0 or (a*a + b*b) % 4 == 1 or (a*a + b*b) % 4 == 2",
]


@pytest.mark.parametrize("cp", TRUE)
def test_generates_canonical_theorem_and_zmod_proof(cp):
    gen = rp.residue_law("law", D, cp)
    assert gen is not None
    thm, proof = gen
    assert thm.startswith("theorem law : ∀ (a b : ℤ),") and "0 ≤ a" in thm   # canonical ℤ-box form
    assert "Int.emod" in thm and " % " not in thm                            # Euclidean, from dsl_to_lean
    # the proof is the ZMod bridge over the kernel (never native_decide)
    assert "ZMod" in proof and "by decide" in proof and "native_decide" not in proof
    assert "ZMod.intCast_eq_intCast_iff'" in proof


@pytest.mark.parametrize("bad_domain,bad_prop", [
    ("n >= 0", "(n*n) % 4 == 0 or (n*n) % 4 == 1"),   # single variable → below MIN_VARS
    (D, "min(a, b) % 3 == 0"),                          # min/max not ZMod-bridgeable
    (D, "(a / 2) % 4 == 1"),                            # division in the poly
    (D, "a*a >= a"),                                    # non-modular
    (D, "(a*a + b*b) % 4 == 5"),                        # out-of-range residue (inherits lean_decided guard)
    (D, "(a*a + b*b) % 97 != 3"),                       # residue budget (97^2 > cap)
    ("", "(a*a + b*b) % 4 != 3"),                       # empty domain
])
def test_abstains_outside_fragment(bad_domain, bad_prop):
    assert rp.residue_law("law", bad_domain, bad_prop) is None


def test_law_statement_is_the_canonical_boxed_integer_claim():
    from leibniz.dsl_to_lean import free_vars
    vs = free_vars(D, "(a*a + b*b) % 4 != 3")
    s = rp.law_statement(D, "(a*a + b*b) % 4 != 3", vs)
    assert s.startswith("∀ (a b : ℤ),")
    assert s.count("→") >= 2                 # box(a) → box(b) → domain → property (≥2 shown; ≥3 total)
    assert "ℕ" not in s and "Nat.sub" not in s


def test_generator_is_deterministic():
    a = rp.residue_law("law", D, TRUE[2])
    b = rp.residue_law("law", D, TRUE[2])
    assert a == b and a is not None


def test_never_raises_on_garbage():
    for junk in ["", ")(", "import os", "a and", "%%%", "min(", "a ** b % 4 == 0"]:
        assert rp.residue_law("law", D, junk) is None       # total-or-abstain, never an exception


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_proves_true_rejects_false():  # pragma: no cover
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.propositio import Expressio
    if not available():
        pytest.skip("Lean image unavailable")
    be = LeanReplBackend(timeout_s=150)
    try:
        thm, proof = rp.residue_law("live", D, TRUE[2])                       # true → proved
        assert be.check_proof(Expressio(theorem_src=thm, imports=rp.IMPORTS), proof) is True
        thm2, proof2 = rp.residue_law("bad", D, "(a*a + b*b) % 4 != 2")       # false → rejected
        assert be.check_proof(Expressio(theorem_src=thm2, imports=rp.IMPORTS), proof2) is False
    finally:
        be.close()

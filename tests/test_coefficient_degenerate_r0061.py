"""ADR 0061 — coefficient-degenerate non-triviality guard.

A modular claim whose every congruence atom's polynomial reduces to a CONSTANT mod its modulus
(all non-constant monomial coefficients ≡ 0 mod m) is vacuous — its truth is variable-independent —
yet `is_trivial`'s tactic ladder misses it in the modular fragment (Phase 3 finding). This tests the
pure decision function `structural.is_coefficient_degenerate` (decides on FORM, never truth, so it
flags ONLY variable-independent claims and never a genuine residue fact) and its wiring into the
NoveltyGate (`check` + `revalidate`), which quarantines TRIVIAL before the Lean `is_trivial` call.
No Docker.
"""
from __future__ import annotations

import pytest

from leibniz.gates.novelty import NoveltyGate
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.structural import is_coefficient_degenerate as deg
from leibniz.trust import NOVELTY_EDGE
from leibniz.types import ClaimSignature, ClaimType, FinishReason, Verdict


# --- the pure decision function -------------------------------------------------------------------

@pytest.mark.parametrize("cp", [
    "(2*a*b) % 2 == 0",                    # coeff 2 ≡ 0 mod 2 on the nonlinear term
    "(3*a*b) % 3 == 0",
    "(2*a*b + 1) % 2 == 1",                # poly−c = 2ab → constant mod 2
    "(4*a + 2*b) % 2 == 0",                # linear-degenerate that omega still misses on the ℤ statement
    "(6*a*b) % 3 != 1",
    "(2*a) % 2 == (2*b) % 2",              # P1 % m == P2 % m, both reduce to 0
    "(2*a*b) % 2 == 0 and (4*a*b) % 4 == 0",   # conjunction: EVERY atom degenerate
    "(2*a*b) % 2 == 0 or (3*a) % 3 == 1",
    "not ((2*a*b) % 2 == 1)",
    "(4*a*b) % 2 in {0}",                  # membership over a constant-reducing poly
])
def test_flags_variable_independent_claims(cp):
    assert deg(cp) is True


@pytest.mark.parametrize("cp", [
    "(a*a + b*b) % 4 != 3",                # coeffs 1,1 ≢ 0 mod 4 → genuine fact about squares
    "(a*a + a) % 2 == 0",                  # consecutive-integer parity: a real residue fact, coeff 1
    "(a*b) % 3 == 0",
    "(a + b) % 2 == 1",
    "((a*b) % 3 == 0) == ((a % 3 == 0) or (b % 3 == 0))",   # genuine biconditional
    "(a % 2 == 0) == (a % 2 == 0)",        # P↔P: caught by the content-free guard, NOT this check
    "(a**3 - a) % 3 == 0 and (b**3 - b) % 3 == 0",          # Fermat congruence
    "(2*a*b) % 2 == 0 and (a*a + b*b) % 4 != 3",           # one degenerate + one genuine → NOT all-degen
    "max(a,b) == max(b,a)",                # non-modular (no congruence atom) → cannot conclude
    "a*a + b*b >= 0",                      # not a modular claim at all
])
def test_does_not_flag_genuine_or_non_modular(cp):
    assert deg(cp) is False


def test_total_on_adversarial_input():
    for bad in [None, "", "(((", "a % 0 == 0", "min(a, b) % 2 == 0", "a / 2 % 2 == 0", "1 == 1"]:
        assert deg(bad) is False


# --- NoveltyGate wiring ---------------------------------------------------------------------------

class FakeLean:
    """is_trivial configurable; the coefficient-degenerate check must fire BEFORE this is consulted."""

    def __init__(self, trivial=False):
        self._trivial = trivial
        self.calls = 0

    def is_trivial(self, expressio):
        self.calls += 1
        return self._trivial


class FakeCorpus:
    def contains_equivalent(self, sig):
        return False

    def nearest(self, sig):
        return []

    def structural_known(self, claim_property):
        return None


def mkprop(cp):
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain="a >= 0 and b >= 0", claim_property=cp)
    ex = Expressio(theorem_src="theorem t : True", normalized_hash="h")
    sig = ClaimSignature(claim_type=ClaimType.INVARIANT, subject="s", relation="r", formal_hash="h")
    return Propositio(enuntiatio=en, expressio=ex, signature=sig)


def test_check_quarantines_degenerate_before_calling_is_trivial():
    lean = FakeLean(trivial=False)
    prop = mkprop("(2*a*b) % 2 == 0")
    ev = NoveltyGate(corpus=FakeCorpus(), lean=lean).check(prop)
    assert ev.edge == NOVELTY_EDGE and ev.verdict is Verdict.FAIL
    assert ev.producer == "structural.coefficient_degenerate"
    assert prop.finish_reason is FinishReason.TRIVIAL
    assert lean.calls == 0                 # the cheap DSL check short-circuits before any Lean call


def test_check_passes_a_genuine_modular_claim():
    lean = FakeLean(trivial=False)
    prop = mkprop("(a*a + b*b) % 4 != 3")
    ev = NoveltyGate(corpus=FakeCorpus(), lean=lean).check(prop)
    assert ev.verdict is Verdict.PASS and ev.producer == "NoveltyGate"
    assert prop.finish_reason is None
    assert lean.calls == 1                 # genuine → falls through to the is_trivial ladder


def test_revalidate_fails_a_degenerate_canonical_law():
    lean = FakeLean(trivial=False)
    prop = mkprop("(2*a*b) % 2 == 0")
    ev = NoveltyGate(corpus=FakeCorpus(), lean=lean).revalidate(prop)
    assert ev is not None and ev.verdict is Verdict.FAIL
    assert ev.producer == "structural.coefficient_degenerate"
    assert prop.finish_reason is FinishReason.TRIVIAL
    assert lean.calls == 0


def test_revalidate_keeps_a_genuine_canonical_law():
    prop = mkprop("(a*a + b*b) % 4 != 3")
    assert NoveltyGate(corpus=FakeCorpus(), lean=FakeLean(trivial=False)).revalidate(prop) is None
    assert prop.finish_reason is None

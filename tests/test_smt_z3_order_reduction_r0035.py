"""ADR 0035 Stage A — multiplicative-order reduction for `base^n % m` (CI-safe; needs z3).

This widens the faithfulness DSL to symbolic-exponent MODULAR claims by encoding `base^n % m`
over its multiplicative-order period (the sound-and-active repair of ADR 0030's inert Tier B).
It touches the faithfulness *encoding* layer — the one place a bug becomes a wrong-UNSAT =
vacuous PASS — so these tests are the soundness bar ADR 0035 §3 mandates:

  • EXHAUSTIVE order-oracle correctness over [0,64]^2 (vs Python `pow`);
  • EXACTNESS of the encoding (encoded residue == pow(base,n,m)) over the whole box;
  • a per-construct WRONG-UNSAT regression (a false symbolic-exp claim ALWAYS yields a witness,
    never UNSAT — so a wrong oracle cannot silently certify a gamed claim);
  • the exact-or-DEFER cases (non-coprime, compound/out-of-mod exponent, non-constant base,
    order over the search bound / cap) all DEFER, never encode.
"""
from __future__ import annotations

import ast
from math import gcd

import pytest

from leibniz.backends import smt_z3 as S
from leibniz.backends.smt_z3 import MAX_ORDER, Z3Backend, _multiplicative_order, _order_reduction

if not S.available():  # pragma: no cover
    pytest.skip("z3 not installed", allow_module_level=True)

import z3  # noqa: E402  (only reached when available)


# --- the order oracle: exhaustive correctness over the box --------------------

def test_multiplicative_order_is_correct_over_the_box():
    for m in range(2, 65):
        for base in range(0, 65):
            ordv = _multiplicative_order(base, m)
            if gcd(base, m) != 1:
                assert ordv is None, f"non-coprime ({base},{m}) must have no order"
                continue
            assert ordv is not None and 1 <= ordv <= m - 1
            assert pow(base, ordv, m) == 1 % m            # base^ord ≡ 1
            assert all(pow(base, k, m) != 1 % m for k in range(1, ordv))  # and it is the SMALLEST


# --- the encoding: exact over the whole box ----------------------------------

def _residue_expr(base: int, m: int, bound: int = 64):
    node = ast.parse(f"({base}**n) % {m}", mode="eval").body
    env: dict = {}
    red = _order_reduction(node, env, bound)
    return red, env.get("n")


def test_encoding_equals_pow_over_the_box():
    for base, m in [(2, 7), (2, 13), (3, 7), (2, 9), (5, 11), (10, 3), (1, 5), (3, 16), (7, 12)]:
        red, var = _residue_expr(base, m)
        assert red is not None, f"({base},{m}) should reduce"
        for k in range(65):  # the box is [0, 64] inclusive
            got = z3.simplify(z3.substitute(red, (var, z3.IntVal(k)))).as_long()
            assert got == pow(base, k, m), f"{base}^{k} % {m}: encoded {got} != {pow(base,k,m)}"


def test_n0_arm_is_pinned():
    # n=0 is a real point in the box; base^0 % m must be 1 (the index-0 residue), never dropped.
    for base, m in [(2, 7), (3, 13), (5, 16)]:
        red, var = _residue_expr(base, m)
        assert z3.simplify(z3.substitute(red, (var, z3.IntVal(0)))).as_long() == 1


# --- soundness through the gate path -----------------------------------------

def test_true_full_cycle_claim_is_faithful():
    b = Z3Backend()
    # 2^n mod 7 cycles through exactly {1,2,4}; asserting membership is faithful (negation UNSAT).
    assert b.decide_unsat(["(2^n)%7 != 1 and (2^n)%7 != 2 and (2^n)%7 != 4"]) is True


def test_false_symbolic_exp_claim_always_yields_a_witness_not_unsat():
    # WRONG-UNSAT REGRESSION (the trust-critical one): for every coprime (base,m), pick a residue
    # the cycle ACTUALLY hits and a residue it MISSES; '!= hit' must be SAT (a real witness) and
    # never UNSAT. A bug in the oracle/encoding (wrong residues) would surface as a spurious UNSAT
    # here — i.e. it would let a gamed claim pass faithfulness. It must not.
    b = Z3Backend()
    for base, m in [(2, 7), (3, 7), (2, 13), (5, 11), (2, 9)]:
        cycle = {pow(base, k, m) for k in range(_multiplicative_order(base, m))}
        hit = min(cycle)
        # the value base^n takes at n=1 is `base % m` (in the cycle) -> '!= that' is violated there
        assert b.decide_unsat([f"({base}^n)%{m} != {hit}"]) is False, (base, m, hit)
        # and a residue OUTSIDE the cycle is never hit -> '== missing' has NO witness (UNSAT)
        missing = next((r for r in range(m) if r not in cycle), None)
        if missing is not None:
            assert b.decide_unsat([f"({base}^n)%{m} == {missing}"]) is True, (base, m, missing)


# --- exact-or-DEFER: everything that cannot be soundly encoded DEFERs ---------

@pytest.mark.parametrize("pred", [
    "(2^n)%4==0",        # non-coprime gcd(2,4)=2 -> a pre-period, not purely periodic
    "(6^n)%9==0",        # non-coprime gcd(6,9)=3
    "(2^(n+1))%7==1",    # compound exponent
    "(2^(2*n))%7==1",    # compound exponent
    "(2^n)+1==3",        # base^n OUTSIDE a mod context -> unbounded
    "(2^n)==1",          # ditto, compared directly
    "(k^n)%7==1",        # non-constant base
    # NON-MOD operators with a base^n left child must DEFER, never be mis-read as periodic
    # (the order reduction self-guards on op=ast.Mod; these hit Add/Sub/Mult/Div/Pow -> Pow DEFER):
    "(2^n)+7==8",
    "(2^n)-7==0",
    "(2^n)*7==14",
    "(2^n)/7==0",
    "(2^n)^7==1",
])
def test_unencodable_shapes_defer(pred):
    assert Z3Backend().encodable(pred) is False


def test_order_reduction_self_guards_on_mod_op():
    # defense-in-depth: called directly with a NON-Mod node, _order_reduction returns None
    # (it must not encode a `base^n + c` / `base^n * c` as if it were periodic).
    for src in ("(2**n) + 7", "(2**n) * 7", "(2**n) - 7"):
        node = ast.parse(src, mode="eval").body
        assert _order_reduction(node, {}, 64) is None


def test_coprime_symbolic_exp_is_now_encodable():
    # the whole point of Stage A: this DEFERred before (ADR 0030 Tier B inert), now it encodes.
    assert Z3Backend().encodable("(2^n)%7==1") is True


def test_order_over_search_bound_defers():
    # ord_11(2)=10; if the box does not cover a full period (bound < ord), UNSAT would not be
    # genuine -> must DEFER, never encode (the bound-robustness guard).
    node = ast.parse("(2**n) % 11", mode="eval").body
    with pytest.raises(S.PredicateError):
        _order_reduction(node, {}, bound=5)
    # and with no bound at all (a bound-less caller) it also DEFERs
    with pytest.raises(S.PredicateError):
        _order_reduction(node, {}, bound=None)


def test_max_order_cap_is_within_box():
    # the cap must not exceed the default search box, or a passed period could exceed the box.
    assert MAX_ORDER <= Z3Backend().default_bound


def test_constant_exponent_still_uses_the_normal_pow_path():
    # base^CONST % m is not the order-reduction shape; it still works (regression: don't intercept it).
    assert Z3Backend().decide_unsat(["(2^3)%7 != 1"]) is True   # 8 % 7 == 1 always -> faithful

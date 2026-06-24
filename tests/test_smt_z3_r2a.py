"""R2a: the Z3 gaming-witness mechanism (ADR 0004).

Requires the `verify` extra (z3-solver); skips where absent (e.g. CI runs `dev`).
These exercise the backend's search directly; R2b wires it into the gate.
"""
from __future__ import annotations

import pytest

from leibniz.backends.smt_z3 import Z3Backend, available

pytestmark = [
    pytest.mark.z3,
    pytest.mark.skipif(not available(), reason="z3-solver (verify extra) not installed"),
]


def _backend() -> Z3Backend:
    return Z3Backend()


# --- the domain-narrowing gaming pattern (ADR 0004) ---------------------------

def test_domain_narrowing_is_caught_as_a_gaming_witness():
    # Claim: forall n>=0, 2n >= n+1 (false at n=0). Proof only covered n>=1.
    #   statement     = ¬established_domain = "n < 1"
    #   negated_claim = claim_domain ∧ ¬property = "n >= 0 and 2*n < n + 1"
    witness = _backend().find_gaming_witness("n < 1", "n >= 0 and 2*n < n + 1")
    assert witness == {"n": 0}


def test_faithful_statement_yields_no_witness():
    # Proof covered the full claim domain (n>=0) -> ¬established_domain = "n < 0".
    witness = _backend().find_gaming_witness("n < 0", "n >= 0 and 2*n < n + 1")
    assert witness is None


# --- cheap refutation ---------------------------------------------------------

def test_counterexample_found_when_one_exists():
    assert _backend().find_counterexample("n > 5") == {"n": 6}


def test_no_counterexample_when_claim_holds():
    # n*n >= n for all naturals -> the refutation predicate n*n < n is UNSAT.
    assert _backend().find_counterexample("n * n < n") is None


# --- DSL robustness -----------------------------------------------------------

def test_chained_comparison():
    # 10 <= n <= 12 -> a model exists in [0,64]
    assert _backend().find_counterexample("10 <= n and n <= 12") is not None


def test_unsafe_predicate_degrades_to_no_witness():
    # Must never eval arbitrary Python; outside the DSL -> None, no crash.
    assert _backend().find_counterexample("__import__('os').system('echo pwned')") is None
    assert _backend().find_gaming_witness("open('x')", "n >= 0") is None


# --- ADR 0021: widened DSL (multi-variable, constant power, constant mod/div) -----

def test_multivariable_search_is_sound():
    assert _backend().find_counterexample("a + b != b + a") is None       # commutativity holds
    m = _backend().find_counterexample("a * b < a + b")                    # e.g. a=0, b=1
    assert m is not None and {"a", "b"} <= set(m)
    assert m["a"] * m["b"] < m["a"] + m["b"]                              # model genuinely satisfies


def test_caret_gets_exponentiation_precedence():
    # ADR 0021 soundness review (CRITICAL): `^` must bind like power, not BitXor.
    # n * 2 ^ 0 means n*(2^0)=n; the refutation n<1 has a witness at n=0.
    assert _backend().find_counterexample("n * 2 ^ 0 < 1") == {"n": 0}
    assert _backend().find_counterexample("2 ^ 3 != 8") is None           # 2^3 == 8


def test_non_boolean_predicate_degrades_to_no_witness():
    # A bare arithmetic term is not a predicate -> degrade to None, never crash the gate.
    assert _backend().find_counterexample("n + 1") is None
    assert _backend().find_gaming_witness("n + 1", "n >= 0") is None
    assert _backend().encodable("n + 1") is False


def test_deeply_nested_predicate_degrades_safely():
    huge = " + ".join(["n"] * 300) + " >= 0"  # exceeds the AST node cap
    assert _backend().encodable(huge) is False
    assert _backend().find_counterexample(huge) is None  # no RecursionError escapes


def test_constant_power_and_modulo_encode_soundly():
    assert _backend().find_counterexample("n ^ 2 < 0") is None             # n*n >= 0 always
    assert _backend().find_counterexample("n % 2 == 1") is not None        # an odd n exists
    assert _backend().find_counterexample("(n * (n + 1)) % 2 != 0") is None  # n(n+1) is even


def test_symbolic_exponent_and_other_functions_stay_unencodable():
    # No vacuous certification of what Z3 cannot decide -> degrade to no witness.
    assert _backend().find_counterexample("n < 2 ^ n") is None             # symbolic exponent
    assert _backend().find_counterexample("Nat.log(2, n) > n") is None     # function call (not whitelisted)


# --- ADR 0030 Tier A: min / max (exact via z3.If) --------------------------------

def test_min_max_encode_exactly():
    b = _backend()
    # min/max are bounded by their args, in both directions -> these refutations are UNSAT.
    assert b.find_counterexample("min(a, b) > a") is None      # min <= a always
    assert b.find_counterexample("min(a, b) > b") is None      # min <= b always
    assert b.find_counterexample("max(a, b) < a") is None      # max >= a always
    assert b.find_counterexample("min(a, b) > max(a, b)") is None
    # min/max is ALWAYS one of the arguments (no spurious third value):
    assert b.find_counterexample("min(a, b) != a and min(a, b) != b") is None
    assert b.find_counterexample("max(a, b) != a and max(a, b) != b") is None


def test_min_max_identities_pin_exactness():
    b = _backend()
    # max+min == a+b and max*min == a*b hold IFF the encoding is exactly min/max — a strong
    # exactness cross-check over the whole bounded box (UNSAT = identity holds everywhere).
    assert b.find_counterexample("max(a, b) + min(a, b) != a + b") is None
    assert b.find_counterexample("max(a, b) * min(a, b) != a * b") is None
    # n-ary: min/max of three is bounded by each argument.
    assert b.find_counterexample("min(a, b, c) > a") is None
    assert b.find_counterexample("max(a, b, c) < c") is None


def test_min_max_not_vacuous_a_false_claim_yields_a_witness():
    # Guard against a wrong-UNSAT: "min(a,b) == a" is FALSE when a>b, so its negation MUST
    # be SAT (a real witness), not vacuously UNSAT.
    m = _backend().find_counterexample("min(a, b) != a")
    assert m is not None and min(m.get("a", 0), m.get("b", 0)) != m.get("a", 0)
    assert _backend().encodable("min(a, b) >= 0") is True       # genuinely encodable now


def test_equivalent_tri_state_over_the_box():
    b = _backend()
    # a true restatement: (n^5+4n)%5==0 <-> Fermat n^5%5==n%5 (both <=> n^5 ≡ n mod 5)
    assert b.equivalent("(n^5 + 4*n) % 5 == 0", "n^5 % 5 == n % 5") is True
    assert b.equivalent("n^3 % 6 == n % 6", "(n^3 - n) % 6 == 0") is True
    # genuinely different claims differ somewhere -> False (NOT wrongly merged)
    assert b.equivalent("n^4 % 7 == n % 7", "n^7 % 7 == n % 7") is False
    assert b.equivalent("n % 2 == 0", "n % 3 == 0") is False
    # un-encodable -> None (inconclusive; a caller must NOT treat this as equivalent)
    assert b.equivalent("Nat.log(2, n) > 0", "n > 0") is None


def test_unsafe_or_unwhitelisted_calls_still_degrade_to_no_witness():
    b = _backend()
    assert b.find_counterexample("gcd(a, b) > 0") is None            # not whitelisted
    assert b.find_counterexample("math.min(a, b) < 0") is None       # attribute call -> rejected
    assert b.find_counterexample("min(a, key=b) > 0") is None        # keyword arg -> rejected
    assert b.find_counterexample("min(a) > 0") is None               # arity < 2 -> rejected
    assert b.encodable("gcd(a, b) == 1") is False

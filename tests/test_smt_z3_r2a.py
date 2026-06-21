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

"""ADR 0020: the faithfulness coverage probe refuses vacuous passes.

The probe certifies faithfulness mechanically only when the structured contract is
actually searchable in the SMT DSL. A richer predicate (^, a second variable, a
function) is un-encodable; the search then degrades to None, which read as "no gap"
would be a VACUOUS pass. The probe must DEFER instead — the gate never launders a
check it could not perform.
"""
from __future__ import annotations

import pytest

from leibniz.backends.smt_z3 import Z3Backend, available
from leibniz.probes import coverage_probe
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimType
from leibniz.verifiers import SMTVerifier

# These exercise the real Z3 DSL; skip where z3 (the `verify` extra) is absent — e.g.
# the stdlib-only CI `invariants` job — so the universal gate stays the invariant suite.
pytestmark = pytest.mark.skipif(not available(), reason="z3 not installed (verify extra)")


def _prop(claim_domain, claim_property, established_domain):
    return Propositio(
        enuntiatio=Enuntiatio(
            statement="x", claim_type=ClaimType.COMPLEXITY_BOUND, falsifiable_claim="y",
            claim_domain=claim_domain, claim_property=claim_property,
        ),
        expressio=Expressio(theorem_src="theorem t : P", established_domain=established_domain),
    )


def _probe():
    return coverage_probe(SMTVerifier(Z3Backend()))


def test_encodable_contract_with_full_coverage_passes():
    # established covers the claim domain; every part encodable -> genuine PASS.
    assert _probe()(_prop("n >= 1", "n < 2 * n", "n >= 1")) is True


def test_unencodable_contract_defers_not_vacuous_pass():
    # exponent / function predicates are outside the DSL -> DEFER, never a vacuous True.
    assert _probe()(_prop("n >= 1", "n < 2 ^ n", "n >= 1")) is None
    assert _probe()(_prop("n >= 1", "Nat.log 2 n <= n", "n >= 1")) is None


def test_incomplete_contract_defers():
    assert _probe()(_prop(None, "n < 2 * n", "n >= 1")) is None
    assert _probe()(_prop("n >= 1", None, "n >= 1")) is None
    assert _probe()(_prop("n >= 1", "n < 2 * n", None)) is None


def test_genuine_coverage_gap_defers():
    # established only n>=5 leaves the claim's n in [1,4] uncovered -> a real gap -> DEFER.
    assert _probe()(_prop("n >= 1", "n < 2 * n", "n >= 5")) is None


def test_backend_encodable_distinguishes_dsl_from_rich():
    be = Z3Backend()
    # widened DSL (ADR 0021): multi-variable, constant powers, constant mod/div
    assert be.encodable("n >= 1") is True
    assert be.encodable("a + b == b + a") is True            # multiple variables
    assert be.encodable("n ^ 2 <= n * n + 1") is True        # constant exponent
    assert be.encodable("(n * (n + 1)) / 2 >= n") is True    # constant divisor
    assert be.encodable("n % 2 == 0") is True                # constant modulus
    # still outside the sound DSL -> DEFER (honest)
    assert be.encodable("n < 2 ^ n") is False                # symbolic exponent
    assert be.encodable("Nat.log 2 n <= n") is False         # function / syntax
    assert be.encodable("n / m == 1") is False               # variable divisor


def test_multivariable_contract_now_certifies():
    # A two-variable contract that ADR 0020 would DEFER (un-encodable) is now
    # genuinely checked and PASSes when covered (ADR 0021 widening).
    p = _prop("a >= 0 and b >= 0", "a + b == b + a", "a >= 0 and b >= 0")
    assert _probe()(p) is True


def test_caret_power_no_longer_vacuously_passes():
    # ADR 0021 soundness-review CRITICAL: "n * 2 ^ 0 >= 1" once mis-parsed as (2n)^0=1
    # (true everywhere) -> vacuous PASS. With ^->** it is n*1>=1 = n>=1, which does NOT
    # cover claim_domain n>=0 (real gap at n=0) -> the probe DEFERs (catches it).
    p = _prop("n >= 0", "n >= 1", "n * 2 ^ 0 >= 1")
    assert _probe()(p) is None


def test_probe_defers_on_domain_narrowing():
    # The proof's established_domain (n>=1) is narrower than the claim_domain (n>=0) —
    # exactly the region where the property "2n>=n+1" fails (n=0). A real coverage gap
    # at n=0 -> the probe DEFERs (refuses to certify the narrowed statement).
    p = _prop("n >= 0", "2 * n >= n + 1", "n >= 1")
    assert _probe()(p) is None

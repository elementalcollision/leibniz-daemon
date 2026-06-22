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
    assert be.encodable("n >= 1") is True and be.encodable("n < 2 * n") is True
    assert be.encodable("n < 2 ^ n") is False and be.encodable("a + b == b + a") is False

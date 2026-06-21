"""ADR 0010: expanded faithfulness probe table.

CI-safe part: the table now covers the four ∀-over-domain claim types and excludes
EXISTENCE/STRUCTURAL (which stay DEFER). z3-gated part: an OPTIMALITY claim is
adjudicated mechanically (PASS on full coverage, DEFER on a gap), end-to-end.
"""
from __future__ import annotations

import pytest

from leibniz.probes import default_probes
from leibniz.types import ClaimType


def test_probe_table_covers_the_forall_domain_types():
    probes = default_probes(object())  # smt unused for the key check
    assert set(probes) == {
        ClaimType.COMPLEXITY_BOUND,
        ClaimType.CORRECTNESS_OVER_DOMAIN,
        ClaimType.OPTIMALITY,
        ClaimType.INVARIANT,
    }
    # not laundered: existence/structural/open_form have no mechanical probe
    assert ClaimType.EXISTENCE not in probes
    assert ClaimType.STRUCTURAL not in probes
    assert ClaimType.OPEN_FORM not in probes


# --- z3-gated end-to-end through the gate ------------------------------------

try:
    from leibniz.backends.smt_z3 import Z3Backend, available
except Exception:  # pragma: no cover
    available = lambda: False  # noqa: E731

z3mark = [pytest.mark.z3, pytest.mark.skipif(not available(), reason="z3 not installed")]


def _gate():
    from leibniz.gates.faithfulness import FaithfulnessGate
    from leibniz.verifiers import SMTVerifier
    smt = SMTVerifier(Z3Backend())

    class _Judge:
        def round_trip_agrees(self, prop):
            return 0.0

    return FaithfulnessGate(smt=smt, probes=default_probes(smt), judge=_Judge())


def _prop(claim_domain, claim_property, established_domain):
    from leibniz.propositio import Enuntiatio, Expressio, Propositio
    en = Enuntiatio(statement="an optimality claim", claim_type=ClaimType.OPTIMALITY,
                    falsifiable_claim="prose", claim_domain=claim_domain, claim_property=claim_property)
    return Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem t : P",
                                                         established_domain=established_domain))


@pytest.mark.z3
@pytest.mark.skipif(not available(), reason="z3 not installed")
def test_optimality_full_coverage_passes_mechanically():
    from leibniz.types import TrustTier, Verdict
    ev = _gate().check(_prop("n >= 1", "n >= 1", "n >= 1"))
    assert ev.tier is TrustTier.MECHANICAL and ev.verdict is Verdict.PASS


@pytest.mark.z3
@pytest.mark.skipif(not available(), reason="z3 not installed")
def test_optimality_coverage_gap_defers():
    from leibniz.types import Verdict
    ev = _gate().check(_prop("n >= 1", "n >= 1", "n >= 5"))
    assert ev.verdict is Verdict.DEFER

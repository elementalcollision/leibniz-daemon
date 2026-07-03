"""Guard the MCR whitepaper audit artifacts (docs/audits/mcr_audit_artifacts.py). z3-gated (operator-local;
CI-skips). Locks the verified verdicts: Thm 1 is the free theorem (naturality holds for the real counter AND
a no-op stub); Cor 1's syllogism is invalid (z3 SAT); the P3 error floor min(q,1-q)>0 is z3-proven; E>log2 N;
the union-bound identity holds. The Lean P4 proof (mcr_p4_not_derivable.lean) is verified separately."""
from __future__ import annotations

import importlib.util
from fractions import Fraction as Fr
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_HAS_Z3 = importlib.util.find_spec("z3") is not None
_needs = pytest.mark.skipif(not _HAS_Z3, reason="z3 is operator-local; MCR audit artifacts skipped in CI")


def _load():
    spec = importlib.util.spec_from_file_location("mcr_audit_artifacts",
                                                  _ROOT / "docs" / "audits" / "mcr_audit_artifacts.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@_needs
def test_p1_theorem1_is_the_free_theorem_vacuous():
    m = _load()
    r = m.p1_parametricity_witness()
    assert r["real_square"] is True and r["stub_square"] is True    # holds even for a no-op stub => VACUOUS


@_needs
def test_p2_universality_syllogism_invalid():
    m = _load()
    r = m.p2_syllogism_invalid()
    assert r["honest_P1P2_notC_is_SAT"] is True                     # entailment invalid under the honest reading
    assert r["equivocated_is_UNSAT"] is True                        # only the equivocated P2 rescues it


@_needs
def test_p3_error_floor_positive_and_argmax_pinned():
    m = _load()
    for q in (Fr(1, 10), Fr(3, 10), Fr(7, 10), Fr(9, 10)):
        r = m.p3_error_floor(q)
        assert r["floor_positive"] is True
        assert r["argmax_a"] == ("b" if q > Fr(1, 2) else "c")      # fixed symbol, independent of sample size
    assert m.p3_z3_floor_proven() is True                           # z3: floor>0 negation UNSAT


@_needs
def test_p5_entropy_exceeds_logN():
    m = _load()
    r = m.p5_entropy_exceeds_logN()
    assert r["E_exceeds_logN"] is True and r["margin_bits"] > 10    # ~13.29-bit violation of E in [0,log2 N]


@_needs
def test_p6_union_bound_identity_and_total_survives():
    m = _load()
    r = m.p6_hoeffding_constant()
    assert r["two_sided_constant"] == "ln(2/delta)"
    assert r["union_identity_holds"] is True                        # ln(2N/δ)=ln(2/δ)+ln N => O(N ln N) survives

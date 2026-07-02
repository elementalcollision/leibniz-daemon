"""Guard Phase 2a — the Terwilliger SDP solve + Table I reproduction (scripts/terwilliger_sdp.py). Needs cvxpy
+ numpy (operator-local, like ortools), so it SKIPS cleanly in CI. The trust-relevant assertions are the
SOUNDNESS ones: a solved bound never floors below a known lower bound on A(n,d), and the formulation is
faithful (record cells reproduce Schrijver Table I; the A(8,4) regression for the phantom-variable fix)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_HAS = importlib.util.find_spec("cvxpy") is not None and importlib.util.find_spec("numpy") is not None
_needs = pytest.mark.skipif(not _HAS, reason="cvxpy/numpy are operator-local; SDP solve skipped in CI")
_HAS_SDPA = _HAS and importlib.util.find_spec("sdpap") is not None
_needs_sdpa = pytest.mark.skipif(
    not _HAS_SDPA, reason="sdpap (sdpa-multiprecision) is operator-local; solve-leg-fix tests skipped in CI")


def _load():
    spec = importlib.util.spec_from_file_location("terwilliger_sdp", _ROOT / "scripts" / "terwilliger_sdp.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ts = _load()


@_needs
def test_small_cells_reproduce_known_A():
    # SDP=LP=A(n,d) at these small cells (three-point doesn't beat the LP until n≈19, per Table I).
    for (n, d), expected in (((4, 2), 8), ((6, 4), 4), ((7, 4), 8)):
        r = ts.run_numerical(n, d)
        assert r["sdp_floor"] == expected


@_needs
def test_a8_4_regression_not_below_16():
    # The phantom-variable bug made this floor to 13 (< A(8,4)=16), an INVALID upper bound. The possible()/
    # binom≠0 fix restores the valid 16.
    r = ts.run_numerical(8, 4)
    assert r["sdp_floor"] == 16
    assert r["valid_bound"] is True


@_needs
def test_record_cell_a19_6_reproduces_table_I():
    # The formulation-faithfulness headline: A(19,6) 1289 (Delsarte) -> 1280 (Schrijver SDP).
    r = ts.run_numerical(19, 6)
    assert r["table_I"] == 1280
    assert r["sdp_floor"] == 1280
    assert r["reproduces_table_I"] is True
    assert r["valid_bound"] is True                 # 1280 >= 1024 lower bound


@_needs
def test_no_bound_floors_below_known_lower_bound():
    # SOUNDNESS sweep: across the LOWER-known cells, no solved bound floors below the true code size.
    for (n, d) in ts.LOWER:
        r = ts.run_numerical(n, d)
        if r.get("sdp_floor") is not None and "valid_bound" in r:
            assert r["valid_bound"] is True, f"A({n},{d}) floored below lower bound: {r}"


# ---- D6 / Q-pit-2 solve-leg fix (eq.(8) normalization + SDPA-GMP) ------------------------------------------

@_needs
def test_normalization_is_optimum_preserving():
    # The eq.(8) rescale is a positive diagonal congruence: exact PSD-equivalence, so the optimum must be
    # UNCHANGED (only conditioning differs). Checked mechanically on a small cell with the same solver.
    a = ts.solve_primal(7, 4, solver="CLARABEL", normalize=False)["value"]
    b = ts.solve_primal(7, 4, solver="CLARABEL", normalize=True)["value"]
    assert abs(a - b) < 1e-4


@_needs
def test_solver_defaults_pairing():
    # solver=None must resolve to the measured pairing: SDPA -> normalized + SDPA_TIGHT; CLARABEL -> raw
    # (byte-compatible pre-fix behavior when sdpap is absent).
    solver, normalize, opts = ts._solver_defaults(None, None, None)
    if _HAS_SDPA:
        assert (solver, normalize, opts) == ("SDPA", True, ts.SDPA_TIGHT)
    else:
        assert (solver, normalize, opts) == ("CLARABEL", False, {})
    assert ts._solver_defaults("CLARABEL", None, None) == ("CLARABEL", False, {})


@_needs_sdpa
def test_solve_leg_fix_crash_cell_23_6():
    # The reach probe's CLARABEL crash-onset cell (~4600 free vars). The fixed leg must return a stable
    # optimal that floors to Schrijver's Table I 13766 (and cuts the Delsarte value 13775.9).
    r = ts.solve_primal(23, 6)
    assert r["status"] == "optimal"
    assert int(r["value"] + 1e-6) == 13766


@_needs_sdpa
def test_d10_faithfulness_25_10():
    # d>=10 formulation faithfulness (previously UNVALIDATED — every d>=10 cell with n>=20 failed both float
    # solvers except (21,10)): the fixed leg reproduces Table I's A(25,10)=503 at true 'optimal' status.
    r = ts.solve_primal(25, 10)
    assert r["status"] == "optimal"
    assert int(r["value"] + 1e-6) == 503

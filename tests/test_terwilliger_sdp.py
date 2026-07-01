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

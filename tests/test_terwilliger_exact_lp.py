"""Guard Path C option (a) — the exact rational LP dual certificate (scripts/terwilliger_exact_lp.py). Needs
cvxpy/numpy (operator-local), so SKIPS in CI. The exact simplex + dual_check legs are exact-rational and
sound; the headline is that A(19,6) ≤ 1280 (Schrijver's record) is reproduced as a genuine exact certificate."""
from __future__ import annotations

import importlib.util
from fractions import Fraction as Fr
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_HAS = importlib.util.find_spec("cvxpy") is not None and importlib.util.find_spec("numpy") is not None
_needs = pytest.mark.skipif(not _HAS, reason="cvxpy/numpy are operator-local; exact-LP cert skipped in CI")


def _load():
    spec = importlib.util.spec_from_file_location("terwilliger_exact_lp", _ROOT / "scripts" / "terwilliger_exact_lp.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


lp = _load()


def test_exact_simplex_basic():
    # min x0+x1 s.t. x0+x1=1, x>=0 -> opt 1; and an equality forcing a value.
    x, opt = lp.exact_simplex([[Fr(1), Fr(1)]], [Fr(1)], [Fr(1), Fr(1)])
    assert x is not None and opt == 1
    x2, opt2 = lp.exact_simplex([[Fr(1), Fr(0)], [Fr(0), Fr(1)]], [Fr(2), Fr(3)], [Fr(1), Fr(1)])
    assert x2 == [Fr(2), Fr(3)] and opt2 == 5


@_needs
@pytest.mark.parametrize("n,d,target", [(4, 2, 8), (6, 4, 4), (8, 4, 16)])
def test_exact_lp_certifies_small_cells(n, d, target):
    r = lp.certify_lp(n, d, target=target)
    assert r["certified"] is True
    assert r["feasible"] and r["residual_zero"] and r["psd_ok"] and r["nonneg_ok"]
    assert r["floor"] == target


@_needs
def test_exact_lp_certifies_a19_6_record_bound():
    # THE record cell: A(19,6) 1289 (Delsarte) -> 1280 (Schrijver SDP), reproduced as an exact audit-tier
    # certificate (exact-PSD blocks, exactly-zero stationarity residuals, α,β1,γ≥0, ⌊Σγ−ν⌋=1280). ~20s.
    r = lp.certify_lp(19, 6, target=1280)
    assert r["certified"] is True
    assert r["feasible"] and r["residual_zero"] and r["psd_ok"] and r["nonneg_ok"]
    assert r["floor"] == 1280

"""Guard Phase 2b — the exact-rational dual-certificate pipeline (scripts/terwilliger_cert.py). Needs cvxpy +
numpy (operator-local), so SKIPS in CI. Asserts the PIPELINE-VERIFIED capability: from a solved SDP the
extracted dual, after rationalization, has an exactly-PSD Z, EXACTLY-zero stationarity residuals, and an exact
bound Σγ−ν that floors to the correct A(n,d) — i.e. the extraction + sign convention + exact stationarity
restoration are correct. (Full certification additionally needs boundary-multiplier nonnegativity via an exact
rational LP; that is tracked separately and NOT asserted here.)"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_HAS = importlib.util.find_spec("cvxpy") is not None and importlib.util.find_spec("numpy") is not None
_needs = pytest.mark.skipif(not _HAS, reason="cvxpy/numpy are operator-local; Phase 2b cert skipped in CI")


def _load():
    spec = importlib.util.spec_from_file_location("terwilliger_cert", _ROOT / "scripts" / "terwilliger_cert.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


tc = _load()


@_needs
def test_dual_extraction_reproduces_optimum():
    ex = tc.extract_dual(6, 4)
    assert ex["status"] in ("optimal", "optimal_inaccurate")
    assert abs(ex["value"] - 4.0) < 1e-3


@_needs
@pytest.mark.parametrize("n,d,target", [(4, 2, 8), (6, 4, 4), (7, 4, 8), (8, 4, 16)])
def test_exact_certificate_small_cells(n, d, target):
    # Full exact certificate: exactly-PSD Z, exactly-zero stationarity residuals, α,β1,γ ≥ 0 (all exact,
    # validated by dual_check), and ⌊Σγ−ν⌋ = A(n,d). Nonnegativity via high-precision clamping.
    r = tc.certify(n, d, target=target)
    assert r["feasible"] is True and r["certified"] is True
    assert r["residual_zero"] is True and r["psd_ok"] is True and r["nonneg_ok"] is True
    assert r["floor"] == target

"""Guard the Path C scale probe (scripts/terwilliger_scale_probe.py). Needs cvxpy/numpy (operator-local), so
SKIPS in CI. Records the measured A(19,6) finding: the exact certificate is compute-bound, NOT impossible —
the dual rounds to PSD (P=1e8 for CLARABEL-era duals; P=1e12–1e14 for the SDPA-GMP duals that are the solve
leg's default since D6/Q-pit-2), the bound floors to 1280, and the wall is exact nonnegativity (hundreds of
negative multipliers), which is why a bit-controlled rational LP was the remaining step."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_HAS = importlib.util.find_spec("cvxpy") is not None and importlib.util.find_spec("numpy") is not None
_needs = pytest.mark.skipif(not _HAS, reason="cvxpy/numpy are operator-local; scale probe skipped in CI")


def _load():
    spec = importlib.util.spec_from_file_location("terwilliger_scale_probe",
                                                  _ROOT / "scripts" / "terwilliger_scale_probe.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


sp = _load()


@_needs
def test_a19_6_certificate_is_compute_bound_not_impossible():
    r = sp.probe(19, 6, 1280)
    assert r["psd_round_P"] is not None          # conditioning surmountable (Z rounds to PSD)
    assert r["residual_zero"] is True            # exact stationarity restoration succeeds
    assert r["floor"] == 1280                    # the bound EXISTS and floors to Schrijver's 1280
    assert r["bound_floors_to_target"] is True
    assert r["negative_multipliers"] > 0         # the wall: exact nonnegativity (needs rational LP / SDPA-GMP)

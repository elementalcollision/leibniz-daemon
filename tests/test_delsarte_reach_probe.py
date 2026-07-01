"""Guard the Delsarte reach probe. Free-CPU; the LP band is ortools-gated (operator-local); the exact
sphere-packing/Singleton bounds always run. A tightening or verify-mismatch would fail the guard (both are
events that must be investigated, not silently accepted)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_HAS_ORTOOLS = importlib.util.find_spec("ortools") is not None
_needs_ortools = pytest.mark.skipif(not _HAS_ORTOOLS, reason="ortools is operator-local; skipped in CI")


def _load(mod, rel):
    import sys
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rp = _load("delsarte_reach_probe", "scripts/delsarte_reach_probe.py")


def test_elementary_bounds_exact():
    assert rp.hamming_ub(15, 3) == 2048          # perfect Hamming: 2^15 / 16
    assert rp.hamming_ub(7, 3) == 16             # perfect Hamming code
    assert rp.singleton_ub(10, 5) == 2 ** 6


@_needs_ortools
def test_reach_no_tightening_and_all_verified():
    res = rp.probe(cells=[(13, 3), (13, 5), (14, 5), (15, 5), (16, 5), (17, 5)])
    assert res["verify_mismatches"] == 0            # every cert re-verified exactly
    assert res["tightenings"] == 0                  # plain LP beats no best-known (any hit => investigate)
    assert res["verified"] >= 5
    # LP has real content: it beats sphere-packing on a clear case
    a175 = next(r for r in res["rows"] if r["cell"] == "A(17,5)")
    assert a175["lp_beats_hamming"] is True

"""Guard the independent verification of the EFX-nonexistence counterexample (scripts/verify_efx_counterexample.py).

Exact exhaustive census over the vendored valuation tables is CI-safe (~1 s). Tier audit; report-only; no trust
surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("efx", _ROOT / "scripts" / "verify_efx_counterexample.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_valuations_are_valid_monotone_ordinals():
    m = _load()
    V = m.load_valuations()
    assert len(V) == 3
    for v in V:
        assert sorted(v.values()) == list(range(256))          # bijection onto {0..255}
        assert v[0] == 0 and v[255] == 255                     # empty → 0, full set → 255


def test_no_efx_allocation_and_faithfulness():
    m = _load()
    r = m.checks()
    assert all(r["valuations_are_permutations"]) and all(r["valuations_monotone"])
    assert r["n_allocations"] == 6561 and r["n_efx_allocations"] == 0          # NO EFX allocation
    assert r["nonempty_allocations"] == 5796                                    # paper's allocation count
    assert r["nonempty_exactly_one_violation"] == 272                          # paper's statistic — faithfulness
    assert r["all_ok"] is True


def test_vendored_data_present():
    m = _load()
    for i in range(3):
        p = m.DATA / f"Val{i}ByCard.txt"
        assert p.exists() and len([ln for ln in p.read_text().splitlines() if ln.strip()]) == 255

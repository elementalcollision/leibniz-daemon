"""Fast guard for the cost-ceiling probe (validation plan Tier 0, R0.3). The full probe (with heavy cells)
is run by hand to emit the finding JSON; here we only assert the measurement machinery is sound on a tiny,
fast ladder."""
from __future__ import annotations

import importlib.util
from math import comb
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


probe = _load("covering_cost_ceiling_probe", "scripts/covering_cost_ceiling_probe.py")


def test_enumeration_floor_counts_all_tsubsets():
    secs, done = probe._enumerate_floor(12, 3)   # C(12,3)=220, trivially fast
    assert done is True and secs >= 0.0


def test_probe_structure_and_monotonic_cost_on_small_ladder():
    res = probe.probe(ladder=[(9, 3, 2), (13, 3, 2), (20, 4, 2)])
    assert len(res["rows"]) == 3
    for r in res["rows"]:
        assert r["t_subsets"] == comb(r["v"], r["t"])
        assert r["completed"] is True            # all tiny -> complete under the hard cap
    # the enumeration count grows with C(v,t)
    ts = [r["t_subsets"] for r in res["rows"]]
    assert ts == sorted(ts)
    assert "thresholds_smallest_cell_over_budget" in res

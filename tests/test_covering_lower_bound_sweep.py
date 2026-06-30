"""Guard the stronger-lower-bound sweep (validation plan Tier 0, R0.8 — the D-ladder rung).

The sweep must be SOUND as a lower-bound classifier: every reported lower bound must genuinely be <= the
best-known record (never above it — that would falsely declare a beatable cell optimal), and a record that
meets a provable lower bound must be tagged OPTIMAL (settled, not a re-open candidate). LP confirmation is
exercised separately (needs ortools) and is not in this fast guard.
"""
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


lbs = _load("covering_lower_bound_sweep", "scripts/covering_lower_bound_sweep.py")
ora = _load("covering_table_oracle", "scripts/covering_table_oracle.py")


def test_counting_bound_is_a_valid_lower_bound():
    # ceil(C(v,t)/C(k,t)): a k-block covers C(k,t) t-subsets, so you need at least this many.
    assert lbs.counting_bound(7, 3, 2) == -(-comb(7, 2) // comb(3, 2))   # ceil(21/3)=7
    assert lbs.counting_bound(9, 3, 2) == -(-comb(9, 2) // comb(3, 2))   # ceil(36/3)=12
    # the cheap lower bound is the max of schonheim and counting, and never below either
    for (v, k, t) in [(7, 3, 2), (9, 3, 2), (13, 3, 2), (8, 4, 3), (20, 5, 3)]:
        lb = lbs.cheap_lower_bound(v, k, t)
        assert lb["cheap_lb"] >= lb["schonheim"]
        assert lb["cheap_lb"] >= lb["counting"]


def test_sweep_is_sound_over_the_committed_snapshot():
    snap = ora.load_snapshot()[0]
    res = lbs.sweep(snap)
    # SOUNDNESS: never report a lower bound above the record (would falsely declare a cell optimal/dead).
    assert res["n_anomaly"] == 0, "a cheap lower bound exceeded a best-known record -> snapshot or bound bug"
    # partition is total
    assert res["n_optimal"] + res["n_open"] + res["n_anomaly"] == res["n_cells"] == len(snap)
    # every row: cheap_lb <= best_known, and the status follows the gap
    for r in res["rows"]:
        assert r["cheap_lb"] <= r["best_known"]
        if r["gap"] == 0:
            assert r["status"] == "OPTIMAL"
        elif r["gap"] > 0:
            assert r["status"] == "OPEN"


def test_known_optimal_and_open_cells_are_tagged():
    snap = ora.load_snapshot()[0]
    res = lbs.sweep(snap)
    by_cell = {(r["v"], r["k"], r["t"]): r for r in res["rows"]}
    # Fano: C(7,3,2)=7 meets schonheim=counting=7 -> OPTIMAL
    assert by_cell[(7, 3, 2)]["status"] == "OPTIMAL"
    # C(7,4,2)=5 vs cheap_lb 4 -> a surviving OPEN (re-open candidate)
    assert by_cell[(7, 4, 2)]["status"] == "OPEN" and by_cell[(7, 4, 2)]["gap"] >= 1

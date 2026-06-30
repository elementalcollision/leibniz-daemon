"""Guard the covering table-of-record oracle's snapshot validation (ADR 0045 review must-fix #4).

The covering oracle must, like the CWC oracle, REFUSE a wrong snapshot at load: ground-truth anchors must
match and every entry must be >= its Schonheim lower bound. Also pins the exact-integer Schonheim (a
float intermediate misrounded L(98,5,2) to 491, falsely flagging a correct cell).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ora = _load("covering_table_oracle", "scripts/covering_table_oracle.py")


def test_committed_snapshot_loads_and_validates():
    snap, meta = ora.load_snapshot()
    assert len(snap) > 9000 and "_provenance" in meta
    ok, problems = ora.validate(snap)
    assert ok, problems[:5]


def test_ground_truth_anchors_hold():
    snap = ora.load_snapshot()[0]
    for cell, expected in ora.GROUND_TRUTH.items():
        assert snap.get(cell) == expected


def test_schonheim_is_exact_integer():
    # the float-arithmetic bug computed L(98,5,2)=491; the true (and committed) value is 490
    assert ora.schonheim(98, 5, 2) == 490
    assert ora.schonheim(7, 3, 2) == 7 and ora.schonheim(9, 3, 2) == 12
    assert ora.schonheim(8, 4, 3) == 14


def test_below_schonheim_entry_is_rejected():
    snap = dict(ora.load_snapshot()[0])
    snap[(20, 4, 2)] = 1                      # 1 << Schonheim(20,4,2); a corrupt/mis-parsed cell
    ok, problems = ora.validate(snap)
    assert not ok and any("below-Schonheim" in p for p in problems)


def test_anchor_mismatch_is_rejected():
    snap = dict(ora.load_snapshot()[0])
    snap[(7, 3, 2)] = 6                       # Fano is optimal at 7; 6 is impossible
    ok, problems = ora.validate(snap)
    assert not ok and any("anchor" in p for p in problems)


def test_is_improvement_direction():
    snap = ora.load_snapshot()[0]
    assert ora.is_improvement(9, 3, 2, 11, snap) is True    # fewer blocks beats
    assert ora.is_improvement(9, 3, 2, 12, snap) is False   # equal is not a beat
    assert ora.is_improvement(999, 7, 4, 5, snap) is False  # untabulated


def test_load_raises_on_corrupt(tmp_path):
    import json
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"bounds": {"7,3,2": 6}}))   # anchor violation
    with pytest.raises(ValueError):
        ora.load_snapshot(bad)

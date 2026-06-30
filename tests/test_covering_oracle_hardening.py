"""Oracle backstop hardening (validation plan Tier 0, R0.6 — load-bearing pieces only).

The covering oracle's `is_improvement`/`best_known` is the SOLE novelty decision procedure (invariant 4)
and the gate any future BEAT verdict reads. test_covering_oracle.py already pins snapshot validation,
ground-truth anchors, exact-integer Schonheim, and the basic is_improvement direction. This adds only the
NEW backstops:
  - a parse-time guard that an ambiguous (zero-padded) key cannot silently overwrite a cell,
  - a check that the COMMITTED snapshot has no such ambiguity today,
  - a property soak that is_improvement is a strict-beat-only relation across many cells and never claims a
    record for an untabulated cell.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ora = _load("covering_table_oracle", "scripts/covering_table_oracle.py")


def test_zero_padded_key_collision_is_rejected(tmp_path):
    bad = tmp_path / "ambiguous.json"
    bad.write_text(json.dumps({"bounds": {"7,3,2": 7, "07,3,2": 99}}))
    with pytest.raises(ValueError, match="ambiguous|zero-padded|parse to"):
        ora.load_snapshot(bad)


def test_committed_snapshot_has_no_ambiguous_keys():
    raw = json.loads(ora.SNAPSHOT.read_text())
    parsed = {}
    for key in raw["bounds"]:
        cell = tuple(int(x) for x in key.split(","))
        assert cell not in parsed, f"ambiguous committed keys {parsed[cell]!r} and {key!r}"
        parsed[cell] = key


def test_is_improvement_is_strict_beat_only_property_soak():
    snap = ora.load_snapshot()[0]
    # sample a broad spread of tabulated cells (every ~200th) for the property soak
    cells = sorted(snap)[::200]
    assert len(cells) >= 20
    for (v, k, t) in cells:
        bk = snap[(v, k, t)]
        assert ora.best_known(v, k, t, snap) == bk
        assert ora.is_improvement(v, k, t, bk, snap) is False        # equalling the record is not a beat
        assert ora.is_improvement(v, k, t, bk + 1, snap) is False     # worse is not a beat
        assert ora.is_improvement(v, k, t, bk - 1, snap) is True      # strictly fewer blocks beats
        assert ora.is_improvement(v, k, t, 0, snap) is True           # any fewer beats


def test_untabulated_cell_is_never_an_improvement():
    snap = ora.load_snapshot()[0]
    # a cell guaranteed absent from the table -> no record to beat -> never an improvement
    assert (3, 2, 1) not in snap
    assert ora.best_known(3, 2, 1, snap) is None
    assert ora.is_improvement(3, 2, 1, 1, snap) is False

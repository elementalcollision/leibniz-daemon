"""Probe β piece 2 — guard the automated table-of-record oracle (the α-lesson safeguard).

The oracle decides Probe β novelty (a witness "beats the record" iff it exceeds best_known). A
wrong oracle poisons every novelty claim, so: the parser is pinned on a synthetic Brouwer-format
fragment (incl. the marker forms), the committed snapshot must LOAD + VALIDATE (ground-truth
anchors + monotonicity), improvement logic must be strict, and a corrupted snapshot must be
REFUSED by validate().
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "cwc_oracle", Path(__file__).resolve().parent.parent / "scripts" / "cwc_table_oracle.py")
ora = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ora)

_FRAGMENT = """\
# Bounds on A(n,4,w)
| n\\w | 3 | 4 | 5 |
| --- | --- | --- | --- |
| 6 | 4. | 7 | 7. |
| 7 | 7. | 8 | [14.] |
| 12 | 20.H | 51. | 80 |
"""


def test_parser_reads_cells_and_strips_markers():
    snap = ora.parse_brouwer_markdown(_FRAGMENT)
    assert snap[(6, 4, 3)] == 4 and snap[(6, 4, 4)] == 7 and snap[(6, 4, 5)] == 7
    assert snap[(7, 4, 3)] == 7 and snap[(7, 4, 5)] == 14      # [14.] -> 14 (bracketed ref)
    assert snap[(12, 4, 3)] == 20                              # 20.H -> 20 (citation superscript)


def test_committed_snapshot_loads_and_validates():
    snap, prov = ora.load_snapshot()
    assert len(snap) > 500
    assert prov["source_url"].endswith("Andw.html") and prov["validated"] is True
    assert set(prov["distances"]) == {4, 6, 8, 10, 12, 14, 16, 18}


def test_best_known_anchors_and_out_of_table():
    snap, _ = ora.load_snapshot()
    assert ora.best_known(7, 4, 3, snap) == 7        # Fano
    assert ora.best_known(13, 4, 3, snap) == 26      # STS(13)
    assert ora.best_known(6, 4, 2, snap) is None     # trivial w not tabulated => unknown


def test_is_improvement_is_strict_and_safe():
    snap, _ = ora.load_snapshot()
    assert ora.is_improvement(7, 4, 3, 8, snap) is True     # beats Fano=7
    assert ora.is_improvement(7, 4, 3, 7, snap) is False    # matches, not beat
    assert ora.is_improvement(7, 4, 3, 6, snap) is False    # worse
    assert ora.is_improvement(6, 4, 2, 99, snap) is False   # untabulated => never claim novelty


def test_validate_rejects_a_corrupted_snapshot():
    snap, _ = ora.load_snapshot()
    bad = dict(snap)
    bad[(7, 4, 3)] = 99                                       # break an anchor
    ok, problems = ora.validate(bad)
    assert not ok and any("A(7, 4, 3)" in p or "(7, 4, 3)" in p for p in problems)
    # monotonicity breach is also caught
    mono = dict(snap)
    mono[(8, 4, 3)] = 1                                       # < A(7,4,3)=7
    ok2, probs2 = ora.validate(mono)
    assert not ok2 and any("monotonicity" in p for p in probs2)


# --- Rosin-2026 cross-check guard (FunSearch precondition; arXiv 2603.00174) --------------------
_rc_spec = importlib.util.spec_from_file_location(
    "cwc_rosin_crosscheck", Path(__file__).resolve().parent.parent / "scripts" / "cwc_rosin_crosscheck.py")
rc = importlib.util.module_from_spec(_rc_spec)
import sys as _sys  # noqa: E402
_sys.modules["cwc_rosin_crosscheck"] = rc
_rc_spec.loader.exec_module(rc)


def test_snapshot_floor_dominates_all_rosin_2026_bounds():
    # the novelty floor must be post-Rosin: snapshot >= Rosin's published bound on every improved cell,
    # else a search re-discovering a Rosin code would be falsely flagged novel. A snapshot refresh that
    # regresses below Rosin fails HERE, loudly.
    ok, violations = rc.assert_post_rosin()
    assert ok, f"snapshot is STALE vs Rosin 2026 on cells: {violations}"
    assert len(rc.ROSIN_2026) == 24                      # all 24 improved cells present


def test_rosin_crosscheck_report_is_consistent():
    rep = rc.crosscheck()
    assert rep["snapshot_dominates_rosin"] is True
    assert rep["cells_stale"] == 0 and rep["cells_untabulated"] == 0
    assert rep["cells_equal"] + rep["cells_beyond"] == 24

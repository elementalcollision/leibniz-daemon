"""Guard the independent verification of the order-1252 skew-Hadamard difference family (Karoui 2026,
arXiv:2602.16089): the bordered SHDF {D0,D1} over GF(5^4) built from cyclotomic classes of order 16 is skew
and its ±1 autocorrelations sum to -2. Pure exact arithmetic, CI-safe (~1s). Tier audit; no trust surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location("sh1252", _ROOT / "scripts" / "verify_skew_hadamard_1252.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_M = _mod()
_R = _M.verify()


def test_field_and_classes():
    assert _M.Q == 625 and _M.GORD == 624 and _M.N == 16 and _M.CLASS_SIZE == 39


def test_shdf_is_valid():
    assert _R["shdf_valid"] is True
    assert _R["skew"] is True
    assert _R["autocorrelation_sum"] == -2


def test_blocks_have_the_right_size():
    # |D0| = |D1| = 8 classes * 39 = 312 = (625-1)/2
    assert _R["D0_size"] == 312 and _R["D1_size"] == 312


def test_matches_the_papers_window_structure():
    # The realized index sets are 8-windows offset by 4 (I0 = I1 + 4 mod 16) — the paper's I0={4..11}, I1={0..7}
    # up to the cyclic relabeling induced by the choice of primitive element.
    i0, i1 = set(_R["I0"]), set(_R["I1"])
    assert len(i0) == 8 and len(i1) == 8
    assert i0 == {(x + 4) % 16 for x in i1}


def test_paper_offset_zero_matches_exactly():
    # Our independently-chosen primitive element happens to realize the paper's exact sets at offset 0.
    assert _R["found_offset"] == 0
    assert sorted(_R["I0"]) == [4, 5, 6, 7, 8, 9, 10, 11]
    assert sorted(_R["I1"]) == [0, 1, 2, 3, 4, 5, 6, 7]

"""Probe β piece 3d — guard the automorphism-prescribed construction (the structural lever).

Pins: the group machinery (orbit sizes), that a prescribed-group code is ALWAYS valid (verify_cwc),
and the headline positive — cyclic-orbit search reaches A(14,6,6)=42 where unstructured search (exact
CP-SAT 30, heuristic 25) plateaued. The search output is untrusted but must always verify.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "probe_beta_automorphism",
    Path(__file__).resolve().parent.parent / "scripts" / "probe_beta_automorphism.py")
pa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pa)


def _snap():
    from cwc_table_oracle import load_snapshot
    return load_snapshot()[0]


def test_cyclic_group_has_n_shifts_and_orbits_partition():
    elems = pa.group_elements(7, "cyclic")
    assert len(elems) == 7 and elems[0] == (0, 1, 2, 3, 4, 5, 6)
    orbs = pa.orbits(7, 3, elems)
    total = sum(len(o) for o in orbs)
    from math import comb
    assert total == comb(7, 3)                                   # orbits partition all weight-w subsets


def test_structure_reaches_a_record_unstructured_search_missed():
    # the headline: cyclic-orbit search reaches A(14,6,6)=42; CP-SAT got 30, local search 25.
    snap = _snap()
    r = pa.attempt(14, 6, 6, snap, kind="cyclic", budget_s=20)
    assert r["verified"] is True
    assert r["found"] == 42 == r["best_known"]                   # reaches the record
    assert r["reaches_record"] is True and r["beats_record"] is False


def test_prescribed_group_code_always_verifies():
    from probe_beta_cwc_pilot import verify_cwc
    snap = _snap()
    for (n, d, w) in [(13, 6, 5), (17, 6, 4)]:
        r = pa.attempt(n, d, w, snap, kind="cyclic", budget_s=10)
        assert r["verified"] is True
        if r["witness"] is not None:
            assert verify_cwc([frozenset(c) for c in r["witness"]], n, d, w)[0] is True
        assert r["found"] <= r["best_known"] or r["beats_record"]

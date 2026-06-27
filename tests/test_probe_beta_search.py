"""Probe β piece 3 — guard the record-beating max-clique search + the non-triviality carve-out.

The search is untrusted (its output is checked by verify_cwc / the kernel), but its max-clique must
be CORRECT for the beats/confirms verdict to mean anything: a wrong max-clique could falsely claim a
beat. Pin it on cells whose optimum is certain (Fano A(7,4,3)=7, A(6,4,3)=4), and pin the carve-out.
"""
from __future__ import annotations

import importlib.util
import time
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "probe_beta_search", Path(__file__).resolve().parent.parent / "scripts" / "probe_beta_search.py")
ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ps)


def _mc(n, d, w):
    _, adj = ps.compat_graph(n, d, w)
    size, _mask, proved = ps.max_clique(adj, time.time() + 30)
    return size, proved


def test_max_clique_matches_known_optima():
    assert _mc(7, 4, 3) == (7, True)     # Fano / STS(7)
    assert _mc(6, 4, 3) == (4, True)     # A(6,4,3)=4
    assert _mc(6, 6, 3) == (2, True)     # two disjoint triples on 6 points


def test_empty_graph_max_clique_is_one():
    # a graph with no compatible pairs (impossible distance) => max code size 1
    _, adj = ps.compat_graph(4, 8, 2)    # weight 2, distance 8 impossible (max dist 4) => no edges
    size, _mask, proved = ps.max_clique(adj, time.time() + 5)
    assert size == 1 and proved


def test_attempt_cell_confirms_exact_for_fano():
    from cwc_table_oracle import load_snapshot
    snap, _ = load_snapshot()
    r = ps.attempt_cell(7, 4, 3, snap)
    assert r["found"] == 7 and r["verified"] and r["proved_optimal"]
    assert r["confirms_exact"] is True and r["beats_record"] is False


def test_attempt_cell_witness_is_a_valid_code():
    from cwc_table_oracle import load_snapshot
    from probe_beta_cwc_pilot import verify_cwc
    snap, _ = load_snapshot()
    r = ps.attempt_cell(9, 6, 4, snap)            # a real non-tight target from the run
    code = [frozenset(c) for c in r["witness"]]
    assert verify_cwc(code, 9, 6, 4)[0] is True
    assert len(code) == r["found"]


def test_nontriviality_carveout_is_improvement():
    from cwc_table_oracle import load_snapshot
    snap, _ = load_snapshot()
    assert ps.record_is_nontrivial(7, 4, 3, 8, snap) is True    # a beat is non-trivial
    assert ps.record_is_nontrivial(7, 4, 3, 7, snap) is False   # matching the record is not

"""Probe β piece 3c — guard the construction search (stochastic greedy + penalty/swap local search).

The search is untrusted; its output must always be a VALID code (verify_cwc), and it must reach known
optima on small tractable cells (so a RED on large open cells is a real plateau, not a broken search).
"""
from __future__ import annotations

import importlib.util
import time
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "probe_beta_construct", Path(__file__).resolve().parent.parent / "scripts" / "probe_beta_construct.py")
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)


def _snap():
    from cwc_table_oracle import load_snapshot
    return load_snapshot()[0]


def test_reaches_small_known_optima():
    snap = _snap()
    for (n, d, w, opt) in [(6, 4, 3, 4), (7, 4, 3, 7), (9, 6, 4, 3)]:
        r = pc.construct_max(n, d, w, snap, budget_s=8)
        assert r["verified"] is True
        assert r["found"] == opt, f"A({n},{d},{w}): construction reached {r['found']}, expected {opt}"
        assert r["reaches_record"] is True


def test_output_is_always_a_valid_code_and_never_a_spurious_beat():
    from probe_beta_cwc_pilot import verify_cwc
    snap = _snap()
    r = pc.construct_max(8, 6, 4, snap, budget_s=5)               # small non-tight cell
    # whatever it returns must verify, and must not exceed the record without a real witness
    if r["witness"] is not None:
        assert verify_cwc([frozenset(c) for c in r["witness"]], 8, 6, 4)[0] is True
    assert r["found"] <= r["best_known"] or r["beats_record"]
    assert r["verified"] is True


def test_find_clique_of_size_returns_valid_or_none():
    nodes, adj = pc.compat_graph(7, 4, 3)
    found = pc.find_clique_of_size(adj, 7, time.time() + 8, seed=1)   # Fano clique of size 7 exists
    if found is not None:
        # every pair in the returned set must be adjacent (a real clique)
        assert all((adj[a] >> b) & 1 for i, a in enumerate(found) for b in found[i + 1:])
        assert len(found) == 7

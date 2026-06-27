"""Probe β piece 3b — guard the CP-SAT strong-solver search (skipped when ortools is absent).

ortools is an optional, operator-local dependency (not a project/CI dep), so these tests skip in
CI. Where it IS available, pin that CP-SAT max-clique agrees with the exact pure-Python max-clique
on a certain cell (Fano A(7,4,3)=7) and that any returned code is a valid CWC (the search is
untrusted; its output must always verify)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "probe_beta_cpsat", Path(__file__).resolve().parent.parent / "scripts" / "probe_beta_cpsat.py")
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)

pytestmark = pytest.mark.skipif(not pc._HAVE, reason="ortools not installed (optional)")


def test_cpsat_matches_exact_max_clique_on_fano():
    nodes, adj = pc.compat_graph(7, 4, 3)
    size, code, proved = pc.cpsat_max_clique(nodes, adj, budget_s=20)
    assert size == 7 and proved                                  # A(7,4,3)=7, optimal
    from probe_beta_cwc_pilot import verify_cwc
    assert verify_cwc(code, 7, 4, 3)[0] is True                  # untrusted output must verify


def test_cpsat_attempt_reports_consistently():
    from cwc_table_oracle import load_snapshot
    snap, _ = load_snapshot()
    r = pc.attempt(6, 4, 3, snap, budget_s=15)                   # small certain cell, A(6,4,3)=4
    assert r["found"] == r["best_known"] == 4                    # reaches the record exactly
    assert r["beats_record"] is False and r["verified"] is True

"""Guard the LLM-free evolutionary loop (the FunSearch harness).

The loop only SEARCHES; it must be deterministic, must reach known structural optima (so a RED on hard
cells is a real plateau not a broken loop), must never report a false beat (witnesses are verify_cwc-
checked inside attempt and judged against the post-Rosin floor), and the post-Rosin floor must be used.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m            # register before exec so @dataclass introspection resolves
    spec.loader.exec_module(m)
    return m


fl = _load("funsearch_loop", "scripts/funsearch_loop.py")


def _snap():
    from cwc_table_oracle import load_snapshot
    return load_snapshot()[0]


def test_effective_floor_is_post_rosin():
    snap = _snap()
    # a Rosin-improved cell: floor must be >= Rosin's new bound (snapshot already dominates)
    assert fl.effective_best_known(31, 16, 14, snap) >= 24
    # a Rosin cell where the snapshot went beyond Rosin (51 > 50)
    assert fl.effective_best_known(25, 10, 8, snap) >= 50


def test_proposer_genes_are_valid_group_kinds():
    p = fl.DeterministicProposer(13)
    from probe_beta_automorphism import candidate_groups_rich
    valid = set(candidate_groups_rich(13))
    rng = fl._LCG(1)
    assert all(g.gene in valid for g in p.seed(rng, 5))
    assert p.mutate(fl.Genome("structural", "cyclic"), rng).gene in valid


def test_evolve_is_deterministic():
    snap = _snap()
    a = fl.evolve(13, 6, 5, snap=snap, pop=6, generations=3, islands=2, budget_s=2.0, seed=42)
    b = fl.evolve(13, 6, 5, snap=snap, pop=6, generations=3, islands=2, budget_s=2.0, seed=42)
    assert a["best_size"] == b["best_size"] and a["best_gene"] == b["best_gene"]


def test_evolve_reaches_a_structural_record_and_flags_no_false_beat():
    snap = _snap()
    # A(14,6,6)=42 is reachable by cyclic-orbit structure; the loop must match it and NOT claim a beat
    r = fl.evolve(14, 6, 6, snap=snap, pop=8, generations=5, islands=2, budget_s=8.0)
    assert r["best_size"] == 42 == r["floor"]
    assert r["beats"] is False and r["beats_detail"] == []


def test_evolve_never_reports_a_beat_on_a_known_cell():
    snap = _snap()
    for (n, d, w) in [(13, 6, 5), (17, 6, 4)]:
        r = fl.evolve(n, d, w, snap=snap, pop=6, generations=3, islands=2, budget_s=3.0)
        assert r["beats"] is False
        assert r["best_size"] <= r["floor"]              # never exceeds the post-Rosin floor here

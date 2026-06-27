"""Probe β piece 3b — STRONG-solver record-beating push (CP-SAT max-clique on larger cells).

Piece 3's pure-Python branch-and-bound was confined to tiny cells (all already tight). This is the
honest strong-solver attempt the finding pointed to: CP-SAT max independent... clique on the
compatibility graph for the *larger* non-tight Brouwer cells (C(n,w) beyond pure-Python's reach).
Max clique = true A(n,d,w); if CP-SAT finds (or proves) a clique larger than best_known, that is a
genuine record beat (Lean-checkable). Untrusted solver; every code is checked by verify_cwc.

ortools is an OPTIONAL, operator-local dependency (not a project/CI dep) — this script gates on it.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cwc_table_oracle as ora  # noqa: E402
from probe_beta_cwc_pilot import verify_cwc  # noqa: E402
from probe_beta_search import compat_graph  # noqa: E402

try:
    from ortools.sat.python import cp_model
    _HAVE = True
except Exception:
    _HAVE = False


def cpsat_max_clique(nodes, adj, budget_s: float, workers: int = 8):
    """Max clique via CP-SAT: x_i in {0,1}; incompatible pair (non-edge) => x_i + x_j <= 1;
    maximize sum. Returns (best_size, code, proved_optimal)."""
    N = len(nodes)
    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x{i}") for i in range(N)]
    for i in range(N):
        ai = adj[i]
        for j in range(i + 1, N):
            if not (ai >> j) & 1:           # not adjacent => incompatible => at most one
                model.Add(x[i] + x[j] <= 1)
    model.Maximize(sum(x))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = budget_s
    solver.parameters.num_search_workers = workers
    status = solver.Solve(model)
    code = [nodes[i] for i in range(N) if solver.Value(x[i]) == 1]
    proved = status == cp_model.OPTIMAL
    return len(code), code, proved


def attempt(n, d, w, snap, budget_s=30.0):
    nodes, adj = compat_graph(n, d, w)
    t0 = time.time()
    size, code, proved = cpsat_max_clique(nodes, adj, budget_s)
    ok, _ = verify_cwc(code, n, d, w)
    bk = ora.best_known(n, d, w, snap)
    return {"n": n, "d": d, "w": w, "nodes": len(nodes), "found": size, "best_known": bk,
            "proved_optimal": proved, "verified": ok,
            "beats_record": bool(ok and bk is not None and size > bk),
            "confirms_exact": bool(ok and proved and bk is not None and size == bk),
            "secs": round(time.time() - t0, 1),
            "witness": [sorted(c) for c in code] if (ok and bk is not None and size > bk) else None}


def main() -> int:
    if not _HAVE:
        print("[probe-β cpsat] ortools not installed — `pip install ortools` to run the strong-solver push")
        return 0
    snap, _ = ora.load_snapshot()
    targets = [[14, 6, 4], [13, 6, 5], [13, 8, 5], [15, 6, 4], [13, 8, 6], [13, 10, 6]]
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("probe_beta_out/cpsat_result.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for n, d, w in targets:
        r = attempt(n, d, w, snap, budget)
        rows.append(r)
        tag = "*** BEATS RECORD ***" if r["beats_record"] else (
            "confirms exact" if r["confirms_exact"] else "no beat")
        print(f"   A({n},{d},{w}) nodes={r['nodes']:4d} found={r['found']:3d} best_known={r['best_known']} "
              f"proved_opt={r['proved_optimal']} ({r['secs']}s) -> {tag}")
    beats = [r for r in rows if r["beats_record"]]
    out.write_text(json.dumps({"cells": len(rows), "beats": len(beats),
                               "confirmed_exact": sum(1 for r in rows if r["confirms_exact"]),
                               "rows": rows}, indent=2))
    print(f"  BEATS: {len(beats)} | confirmed-exact: {sum(1 for r in rows if r['confirms_exact'])} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

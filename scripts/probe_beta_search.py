"""Probe β piece 3 — the record-beating search (exact max-clique on small non-tight cells).

A constant-weight code A(n,d,w) is a clique in the compatibility graph (nodes = w-subsets of
{0..n-1}; edge iff Hamming distance >= d, i.e. |a∩b| <= w - ceil(d/2)). The maximum clique IS the
true A(n,d,w). For the *smallest non-tight* (non-exact) Brouwer cells the graph is small enough to
solve EXACTLY by branch-and-bound — which DECIDES the value: if max-clique > best_known, we have a
genuine record beat (a novel, Lean-checkable witness); if it equals best_known, we have confirmed
exactness (a smaller sound result). Untrusted search; the witness is checked by verify_cwc and (for
a beat) the Lean kernel.

Honest bound: this is exact only where the graph is tractable. The *open* (beatable) cells are large
(C(n,w) grows fast); exhaustive max-clique there needs strong solvers + serious compute beyond a
pure-stdlib run — which is itself the measured limit of naive autonomous record-beating.

Pure stdlib (bitmask branch-and-bound; no ortools/SAT dependency). Deterministic.
"""
from __future__ import annotations

import json
import sys
import time
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cwc_table_oracle as ora  # noqa: E402
from probe_beta_cwc_pilot import verify_cwc  # noqa: E402


def compat_graph(n: int, d: int, w: int):
    """Nodes = w-subsets of range(n); adjacency as bitmasks. Edge iff |a∩b| <= w - ceil(d/2)."""
    nodes = [frozenset(c) for c in combinations(range(n), w)]
    cap = w - (d + 1) // 2
    N = len(nodes)
    adj = [0] * N
    for i in range(N):
        bi = adj[i]
        ai = nodes[i]
        for j in range(i + 1, N):
            if len(ai & nodes[j]) <= cap:
                bi |= (1 << j)
                adj[j] |= (1 << i)
        adj[i] = bi
    return nodes, adj


def max_clique(adj, deadline: float):
    """Exact maximum clique via Tomita-style branch-and-bound with greedy-coloring bounds and
    bitmask sets. Returns (best_size, best_set_bitmask, proved_optimal). Stops early (proved=False)
    if the deadline passes."""
    N = len(adj)
    best = [0, 0]
    all_mask = (1 << N) - 1

    def color_order(P):
        # greedy coloring: assign colors, yield vertices with their color bound (ascending color)
        order = []
        uncolored = P
        color = 0
        while uncolored:
            color += 1
            avail = uncolored
            while avail:
                v = (avail & -avail).bit_length() - 1
                order.append((v, color))
                # remove v and its neighbors from this color class
                avail &= ~(adj[v] | (1 << v))
                uncolored &= ~(1 << v)
        return order  # sorted by color ascending

    def expand(R, P, rsize):
        if time.time() > deadline:
            return False
        order = color_order(P)
        for v, c in reversed(order):           # descending color = best bound first
            if rsize + c <= best[0]:
                return True                    # bound: cannot beat current best
            if time.time() > deadline:
                return False
            newP = P & adj[v]
            if newP == 0:
                if rsize + 1 > best[0]:
                    best[0] = rsize + 1
                    best[1] = R | (1 << v)
            else:
                if not expand(R | (1 << v), newP, rsize + 1):
                    return False
            P &= ~(1 << v)
        return True

    proved = expand(0, all_mask, 0)
    return best[0], best[1], proved


def attempt_cell(n: int, d: int, w: int, snap, budget_s: float = 20.0, max_nodes: int = 1200):
    nodes, adj = compat_graph(n, d, w)
    if len(nodes) > max_nodes:
        return {"n": n, "d": d, "w": w, "nodes": len(nodes), "status": "skipped_too_large",
                "best_known": ora.best_known(n, d, w, snap)}
    size, mask, proved = max_clique(adj, time.time() + budget_s)
    code = [nodes[i] for i in range(len(nodes)) if mask & (1 << i)]
    ok, _ = verify_cwc(code, n, d, w)
    bk = ora.best_known(n, d, w, snap)
    return {"n": n, "d": d, "w": w, "nodes": len(nodes), "found": size, "best_known": bk,
            "proved_optimal": proved, "verified": ok,
            "beats_record": bool(ok and bk is not None and size > bk),
            "confirms_exact": bool(ok and proved and bk is not None and size == bk),
            "witness": [sorted(c) for c in code] if ok else None,
            "status": "ok"}



def record_is_nontrivial(n: int, d: int, w: int, found: int, snap=None) -> bool:
    """Witness-non-triviality CARVE-OUT (piece-3 policy): a CWC witness theorem closed by `decide`
    is NON-trivial iff it BEATS the table-of-record (improves best_known). This is the criterion
    the pipeline's triviality gate (decide in DEFAULT_TRIVIAL_TACTICS) would need so a record-
    beating witness promulgates instead of being quarantined. Wiring into lean_cli is DEFERRED
    until a beat actually exists (this run produced 0 beats), to avoid a premature trust-edge change."""
    return ora.is_improvement(n, d, w, found, snap)


def main() -> int:
    snap, _ = ora.load_snapshot()
    # pre-registered smallest non-tight cells (by search space), tractable for exact max-clique
    targets = [(8, 6, 4), (9, 6, 4), (10, 8, 5), (10, 6, 4), (11, 8, 5),
               (10, 6, 5), (11, 6, 4), (12, 8, 5), (12, 10, 6), (12, 8, 6)]
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("probe_beta_out/search_result.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = [attempt_cell(n, d, w, snap) for (n, d, w) in targets]
    beats = [r for r in rows if r.get("beats_record")]
    confirmed = [r for r in rows if r.get("confirms_exact")]
    summary = {"cells": len(rows), "beats": len(beats), "confirmed_exact": len(confirmed),
               "rows": rows}
    out.write_text(json.dumps(summary, indent=2))
    print(f"[probe-β piece3] exact max-clique on {len(rows)} smallest non-tight cells -> {out}")
    for r in rows:
        if r["status"] != "ok":
            print(f"   A({r['n']},{r['d']},{r['w']}) {r['status']} (nodes={r.get('nodes')})")
            continue
        tag = "*** BEATS RECORD ***" if r["beats_record"] else (
            "confirms exact" if r["confirms_exact"] else "no beat")
        print(f"   A({r['n']},{r['d']},{r['w']}) nodes={r['nodes']:4d} found={r['found']:3d} "
              f"best_known={r['best_known']}  proved_opt={r['proved_optimal']}  -> {tag}")
    print(f"  BEATS: {len(beats)} | confirmed-exact: {len(confirmed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

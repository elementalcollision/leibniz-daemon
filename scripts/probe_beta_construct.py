"""Probe β piece 3c — CONSTRUCTION search (the witness round's unanimous pivot).

The 7-model round was unanimous: the record-beating constraint is ALGORITHM/DOMAIN, and we were using
an OPTIMALITY prover (max-clique/CP-SAT) to find LOWER-BOUND WITNESSES — a lower-bound record needs
ONE big code, not a proof of optimality. The right objective is a direct CONSTRUCTION search: find as
large a valid code as possible by stochastic greedy + penalty/swap local search (no optimality proof,
embarrassingly parallel, and the natural target for finite-witness records).

This is the CPU measure-before-build for the GPU construction-search pivot. Sharpest test: A(14,6,6) —
C(14,6)=3003 is tractable, best_known=42, yet exact CP-SAT reached only 30 in 90s. If construction
search reaches 42 (or beats it), the witnesses' reframe is validated even without a record. Output is
always re-checked by verify_cwc; a beat would then be Lean-checked (the witness IS the proof).

Pure stdlib, deterministic (seeded LCG). No GPU/solver dependency — this is the cheap paradigm test.
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


class _LCG:
    def __init__(self, seed):
        self.s = seed & 0x7FFFFFFF

    def nxt(self):
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s

    def pick(self, n):
        return self.nxt() % n


def find_clique_of_size(adj, k: int, deadline: float, seed: int):
    """Penalty/swap local search for a clique of size exactly k (a code of that size). Maintains a
    working set S of k nodes; `bad[v]` = #nodes in S incompatible with v; conflicts = nodes in S with
    bad>0. Swaps a conflicting in-node for the out-node that most reduces conflicts (greedy + random
    plateau kicks). Returns a conflict-free S (a valid k-code) or None on timeout."""
    N = len(adj)
    if k > N:
        return None
    rng = _LCG(seed)
    # incremental membership + conflict bookkeeping
    inS = bytearray(N)
    S = []
    # random initial k-subset
    order = list(range(N))
    for i in range(N - 1, 0, -1):
        j = rng.pick(i + 1)
        order[i], order[j] = order[j], order[i]
    for v in order[:k]:
        inS[v] = 1
        S.append(v)

    def bad_count(v):
        # #members of S incompatible with v (non-adjacent); v may or may not be in S
        c = 0
        av = adj[v]
        for u in S:
            if u != v and not (av >> u) & 1:
                c += 1
        return c

    bad = {v: bad_count(v) for v in S}

    def conflicts():
        return sum(1 for v in S if bad[v] > 0)

    best_conf = conflicts()
    stale = 0
    while time.time() < deadline:
        cur = conflicts()
        if cur == 0:
            return list(S)                                   # found a valid k-code
        # pick a random conflicting in-node u to remove
        confl_nodes = [v for v in S if bad[v] > 0]
        u = confl_nodes[rng.pick(len(confl_nodes))]
        # choose an out-node v minimizing resulting conflicts (sample to stay cheap)
        best_v, best_delta = None, None
        tries = 0
        vv = rng.pick(N)
        while tries < 64:
            v = (vv + tries) % N
            tries += 1
            if inS[v]:
                continue
            # conflicts v would have with S\{u}
            av = adj[v]
            cv = sum(1 for s in S if s != u and not (av >> s) & 1)
            if best_delta is None or cv < best_delta:
                best_delta, best_v = cv, v
                if cv == 0:
                    break
        if best_v is None:
            stale += 1
        else:
            # swap u out, best_v in; update bad[]
            S.remove(u)
            inS[u] = 0
            del bad[u]
            S.append(best_v)
            inS[best_v] = 1
            bad = {v: bad_count(v) for v in S}             # recompute (k small => cheap)
            nc = conflicts()
            if nc < best_conf:
                best_conf, stale = nc, 0
            else:
                stale += 1
        if stale > 200:                                     # plateau kick: random restart of a few nodes
            for _ in range(max(1, k // 5)):
                if not S:
                    break
                u = S[rng.pick(len(S))]
                S.remove(u)
                inS[u] = 0
                v = rng.pick(N)
                while inS[v]:
                    v = rng.pick(N)
                S.append(v)
                inS[v] = 1
            bad = {v: bad_count(v) for v in S}
            stale = 0
    return None


def construct_max(n, d, w, snap, budget_s=60.0):
    """Greedy seed, then climb the code size via local search until budget; return the largest valid
    code found and how it compares to best_known."""
    nodes, adj = compat_graph(n, d, w)
    rng = _LCG(0xC0FFEE ^ (n * 2654435761) ^ (d * 40503) ^ (w * 77777))
    # greedy seed (random order)
    order = list(range(len(nodes)))
    for i in range(len(order) - 1, 0, -1):
        j = rng.pick(i + 1)
        order[i], order[j] = order[j], order[i]
    code_idx = []
    for v in order:
        if all((adj[v] >> u) & 1 for u in code_idx):
            code_idx.append(v)
    best = code_idx[:]
    t0 = time.time()
    target = len(best) + 1
    while time.time() - t0 < budget_s:
        found = find_clique_of_size(adj, target, t0 + budget_s, seed=target * 2246822519)
        if found is None:
            break
        best = found
        target = len(best) + 1
    code = [nodes[i] for i in best]
    ok, _ = verify_cwc(code, n, d, w)
    bk = ora.best_known(n, d, w, snap)
    return {"n": n, "d": d, "w": w, "nodes": len(nodes), "found": len(code) if ok else 0,
            "best_known": bk, "verified": ok,
            "beats_record": bool(ok and bk is not None and len(code) > bk),
            "reaches_record": bool(ok and bk is not None and len(code) >= bk),
            "secs": round(time.time() - t0, 1),
            "witness": [sorted(c) for c in code] if (ok and bk is not None and len(code) > bk) else None}


def main() -> int:
    snap, _ = ora.load_snapshot()
    # A(14,6,6) first (CP-SAT reached only 30 vs best_known 42 — the cleanest construction-vs-exact test),
    # then other tractable open cells where CP-SAT matched-not-beaten.
    targets = [[14, 6, 6], [15, 6, 5], [14, 6, 5], [13, 6, 5], [17, 6, 4], [18, 6, 4]]
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("probe_beta_out/construct_result.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for n, d, w in targets:
        r = construct_max(n, d, w, snap, budget)
        rows.append(r)
        tag = "*** BEAT ***" if r["beats_record"] else ("reaches record" if r["reaches_record"] else "below record")
        print(f"   A({n},{d},{w}) nodes={r['nodes']:4d} found={r['found']:3d} best_known={r['best_known']} "
              f"({r['secs']}s) -> {tag}")
    out.write_text(json.dumps({"cells": len(rows), "beats": sum(r["beats_record"] for r in rows),
                               "reaches": sum(r["reaches_record"] for r in rows), "rows": rows}, indent=2))
    print(f"  BEATS: {sum(r['beats_record'] for r in rows)} | reaches-record: {sum(r['reaches_record'] for r in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

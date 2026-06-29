"""Stronger covering producer — exact CP-SAT set-cover (ADR 0042/0043 Track-D escalation, FREE/CPU).

The reproduction probe (generic greedy) reached the frontier but beat nothing. This is the strongest
CPU lever, run BEFORE any billable swing: an exact integer-program (CP-SAT) set-cover over the candidate
blocks — minimize the number of blocks subject to covering every t-subset. For the small La Jolla cells
the candidate set C(v,k) and the C(v,t) coverage constraints are tiny, so CP-SAT is DEFINITIVE:

    optimal < best_known  -> BEATS the record (a free, kernel-verifiable new record)
    optimal == best_known (proven OPTIMAL) -> the record is TIGHT; no beat is possible there
    time limit hit        -> inconclusive (raise the budget)

This is the cleanest possible "stronger producer" measurement: a non-beat that PROVES optimality is the
strongest form of the producer wall (it is the record, not our search, that is the ceiling) and tells us
a billable swing on those cells cannot help. Audit/measurement only — never promulgates. Any BEAT is
re-checked by verify_covering (and should then go through covering_check.py for the kernel + operator).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT))

import covering_table_oracle as ora  # noqa: E402
from covering_verify import verify_covering  # noqa: E402

# Headroom / plateau cells from the reproduction probe (gap≥1 to Schönheim or where greedy fell short).
HEADROOM = [(10, 4, 2), (13, 3, 2), (15, 3, 2), (16, 4, 2), (13, 5, 2), (16, 6, 2)]


def solve_cell(v, k, t, *, time_cap=60.0, workers=8):
    from ortools.sat.python import cp_model
    blocks = [tuple(b) for b in combinations(range(v), k)]
    cover = defaultdict(list)
    for i, b in enumerate(blocks):
        for s in combinations(b, t):
            cover[s].append(i)
    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"b{i}") for i in range(len(blocks))]
    for _, idxs in cover.items():
        model.Add(sum(x[i] for i in idxs) >= 1)
    model.Minimize(sum(x))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_cap
    solver.parameters.num_search_workers = workers
    st = solver.Solve(model)
    names = {cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE",
             cp_model.INFEASIBLE: "INFEASIBLE", cp_model.UNKNOWN: "UNKNOWN"}
    got_solution = st in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    found = int(round(solver.ObjectiveValue())) if got_solution else None
    chosen = [blocks[i] for i in range(len(blocks)) if got_solution and solver.Value(x[i]) == 1]
    return {"status": names.get(st, str(st)), "proven_optimal": st == cp_model.OPTIMAL,
            "found": found, "blocks": chosen, "candidate_blocks": len(blocks),
            "wall": round(solver.WallTime(), 1)}


def attack(v, k, t, *, time_cap=60.0):
    bk = ora.best_known(v, k, t)
    out = {"cell": f"C({v},{k},{t})", "v": v, "k": k, "t": t, "best_known": bk}
    if bk is None:
        out["verdict"] = "untabulated"
        return out
    r = solve_cell(v, k, t, time_cap=time_cap)
    out.update({"solver": r["status"], "proven_optimal": r["proven_optimal"],
                "found": r["found"], "candidate_blocks": r["candidate_blocks"], "wall": r["wall"]})
    if r["found"] is None:
        out["verdict"] = "inconclusive (no solution within budget)"
    elif r["found"] < bk:
        ok, reason = verify_covering([frozenset(b) for b in r["blocks"]], v, k, t)
        out["verdict"] = "BEATS" if ok else "BUG(false-beat)"
        out["beat_blocks"] = [sorted(b) for b in r["blocks"]] if ok else None
        out["beat_reason"] = reason
    elif r["found"] == bk and r["proven_optimal"]:
        out["verdict"] = "OPTIMAL-CONFIRMED (record is tight; no beat possible)"
    elif r["found"] == bk:
        out["verdict"] = "reproduced (not proven optimal within budget)"
    else:
        out["verdict"] = "above-record (solver suboptimal within budget)"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Exact CP-SAT covering producer — free record-beat attempt "
                                             "on headroom cells; gates the billable Track-D swing.")
    ap.add_argument("--time-cap", type=float, default=60.0)
    ap.add_argument("--out", help="write JSON report here")
    args = ap.parse_args()

    rows = [attack(v, k, t, time_cap=args.time_cap) for (v, k, t) in HEADROOM]
    beats = [r for r in rows if r.get("verdict") == "BEATS"]
    optimal = [r for r in rows if str(r.get("verdict", "")).startswith("OPTIMAL-CONFIRMED")]
    verdict = ("BEAT" if beats
               else "RECORDS-OPTIMAL" if len(optimal) >= len(rows) // 2
               else "INCONCLUSIVE")
    report = {"verdict": verdict, "beats": len(beats), "optimal_confirmed": len(optimal),
              "cells": len(rows), "rows": rows,
              "reading": ("BEAT = a free kernel-verifiable record (route via covering_check.py + operator). "
                          "RECORDS-OPTIMAL = the strongest producer (exact ILP) PROVES the La Jolla records "
                          "tight on these cells — the ceiling is the record itself, not our search, so a "
                          "billable swing cannot help here; bank Track A. INCONCLUSIVE = raise the budget "
                          "or pick larger-headroom cells.")}
    print(f"exact producer: verdict {verdict}  (beats {len(beats)}, optimal-confirmed {len(optimal)}/{len(rows)})")
    for r in rows:
        print(f"  [{str(r.get('verdict','')):48s}] {r['cell']:11s} best_known={r.get('best_known')} "
              f"found={r.get('found')} proven_opt={r.get('proven_optimal')} ({r.get('wall','?')}s, "
              f"{r.get('candidate_blocks','?')} blocks)")
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n")
        print(f"  -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

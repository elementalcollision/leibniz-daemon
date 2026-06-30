"""Stronger-lower-bound sweep (validation plan Tier 0, R0.8 — the D-ladder's first rung).

GATE-1 asks: does any beatable covering cell exist beyond the proven-optimal reachable band? A cell whose
best-known record EQUALS a provable lower bound is OPTIMAL — no producer can beat it, so it is settled and
not a re-open candidate. A cell with a GAP (best_known strictly above the strongest cheap lower bound) is
OPEN: the record might be beatable, or it might be optimal with a weak bound — only the exact ladder
(Tier 1) settles that. This sweep computes, for EVERY tabulated cell and for $0:

  - schonheim(v,k,t)            : the iterated Schonheim lower bound (exact integer; reused from the oracle)
  - counting bound  ceil(C(v,t)/C(k,t)) : the simple averaging lower bound (each k-block covers C(k,t)
                                  t-subsets; C(v,t) must be covered)
  - cheap_lb = max(schonheim, counting)  : the strongest CHEAP lower bound
  - status   = OPTIMAL  if best_known == cheap_lb   (record meets a provable bound -> settled)
               OPEN     if best_known >  cheap_lb   (a surviving re-open candidate)

It then OPTIONALLY confirms, on a small tractable sample, that the LP relaxation of the set-cover (solved
exactly with ortools GLOP over the full C(v,k) candidate columns) is no stronger than `cheap_lb` -- i.e.
the LP closes 0 gaps. (For these symmetric problems the LP optimum equals the fractional counting bound, so
this is expected; we MEASURE it rather than assert it.) ortools is optional; without it the LP confirmation
is skipped and the sweep still produces the full Schonheim/counting verdict.

Output: docs/results/covering_lower_bound_sweep.json + a printed summary. Pure stdlib for the core sweep.
This run NEVER touches the trust core; it only reads the committed oracle snapshot.
"""
from __future__ import annotations

import importlib.util
import json
from math import comb
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "covering_lower_bound_sweep.json"


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ora = _load("covering_table_oracle", "scripts/covering_table_oracle.py")


def counting_bound(v: int, k: int, t: int) -> int:
    """ceil(C(v,t) / C(k,t)) — a valid lower bound: each k-block covers C(k,t) of the C(v,t) t-subsets."""
    denom = comb(k, t)
    if denom == 0:
        return 0
    return -(-comb(v, t) // denom)  # exact integer ceil


def cheap_lower_bound(v: int, k: int, t: int) -> dict:
    """The strongest cheap (no-search) lower bound and its components."""
    s = ora.schonheim(v, k, t)
    c = counting_bound(v, k, t)
    return {"schonheim": s, "counting": c, "cheap_lb": max(s, c)}


def sweep(snap: dict) -> dict:
    """Tag every tabulated cell OPTIMAL vs OPEN under the strongest cheap lower bound."""
    rows = []
    n_optimal = n_open = n_anomaly = 0
    for (v, k, t), bk in snap.items():
        lb = cheap_lower_bound(v, k, t)
        cheap = lb["cheap_lb"]
        if bk < cheap:
            status = "ANOMALY"            # best-known below a provable LOWER bound -> snapshot corruption
            n_anomaly += 1
        elif bk == cheap:
            status = "OPTIMAL"            # record meets a cheap bound -> settled, not beatable
            n_optimal += 1
        else:
            status = "OPEN"               # gap survives the cheap bound -> re-open candidate
            n_open += 1
        rows.append({"v": v, "k": k, "t": t, "best_known": bk,
                     "schonheim": lb["schonheim"], "counting": lb["counting"],
                     "cheap_lb": cheap, "gap": bk - cheap, "status": status})
    rows.sort(key=lambda r: (r["status"] != "OPEN", r["gap"] if r["status"] == "OPEN" else 0,
                             r["best_known"], r["v"], r["k"], r["t"]))
    return {"n_cells": len(rows), "n_optimal": n_optimal, "n_open": n_open,
            "n_anomaly": n_anomaly, "rows": rows}


def lp_relaxation_bound(v: int, k: int, t: int, time_cap: float = 20.0) -> float | None:
    """Exact LP relaxation of the set-cover (continuous block weights >= 0) via ortools GLOP. Returns the
    fractional covering number (a valid lower bound), or None if ortools is absent or the cell is too large
    to enumerate cheaply. Used only to CONFIRM the LP adds nothing over cheap_lb on a small sample."""
    try:
        from ortools.linear_solver import pywraplp
    except Exception:
        return None
    if comb(v, k) > 4000 or comb(v, t) > 12000:   # keep the confirmation sample genuinely cheap
        return None
    from itertools import combinations
    blocks = list(combinations(range(v), k))
    tsubs = list(combinations(range(v), t))
    block_of = [set(b) for b in blocks]
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:
        return None
    solver.SetTimeLimit(int(time_cap * 1000))
    x = [solver.NumVar(0.0, solver.infinity(), f"x{i}") for i in range(len(blocks))]
    # each t-subset must be fractionally covered to >= 1
    for ts in tsubs:
        tss = set(ts)
        solver.Add(sum(x[i] for i, b in enumerate(block_of) if tss <= b) >= 1)
    solver.Minimize(sum(x))
    status = solver.Solve()
    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        return None
    return solver.Objective().Value()


def confirm_lp_no_stronger(rows: list[dict], sample_n: int = 24) -> dict:
    """On a sample of the smallest OPEN cells, confirm ceil(LP) <= cheap_lb (LP closes 0 gaps)."""
    open_rows = [r for r in rows if r["status"] == "OPEN"]
    # smallest C(v,k) first so the LP is cheap to build
    open_rows.sort(key=lambda r: comb(r["v"], r["k"]))
    checked, lp_stronger = [], 0
    for r in open_rows:
        if len(checked) >= sample_n:
            break
        lp = lp_relaxation_bound(r["v"], r["k"], r["t"])
        if lp is None:
            continue
        lp_ceil = -(-int(round(lp * 1e6)) // 1000000)  # ceil with a tiny epsilon guard
        stronger = lp_ceil > r["cheap_lb"]
        lp_stronger += int(stronger)
        checked.append({"v": r["v"], "k": r["k"], "t": r["t"], "cheap_lb": r["cheap_lb"],
                        "lp": round(lp, 3), "lp_ceil": lp_ceil, "lp_stronger_than_cheap": stronger})
    return {"sampled": len(checked), "lp_closed_gaps": lp_stronger, "detail": checked}


def main() -> int:
    snap, meta = ora.load_snapshot()
    result = sweep(snap)
    lp = confirm_lp_no_stronger(result["rows"])
    result["lp_confirmation"] = lp
    result["provenance"] = meta.get("_provenance")
    # keep the JSON readable: full rows for OPEN + a sample of OPTIMAL
    open_rows = [r for r in result["rows"] if r["status"] == "OPEN"]
    optimal_sample = [r for r in result["rows"] if r["status"] == "OPTIMAL"][:50]
    persisted = dict(result)
    persisted["rows"] = open_rows + optimal_sample
    persisted["rows_note"] = (f"all {result['n_open']} OPEN rows + first 50 OPTIMAL rows "
                              f"(of {result['n_optimal']}) for size")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(persisted, indent=2) + "\n")

    print(f"covering lower-bound sweep: {result['n_cells']} cells")
    print(f"  OPTIMAL (record == cheap lower bound, settled) : {result['n_optimal']}")
    print(f"  OPEN    (gap survives cheap bound, re-open cand): {result['n_open']}")
    print(f"  ANOMALY (best_known < provable lower bound!)    : {result['n_anomaly']}")
    print(f"  LP confirmation: sampled {lp['sampled']} OPEN cells, LP closed {lp['lp_closed_gaps']} gaps "
          f"(0 expected: LP == fractional counting bound <= cheap_lb)")
    if result["n_open"]:
        sm = [r for r in result["rows"] if r["status"] == "OPEN"][:8]
        print("  smallest OPEN cells (gap, best_known):")
        for r in sm:
            print(f"    C({r['v']},{r['k']},{r['t']})  best={r['best_known']:>4d}  cheap_lb={r['cheap_lb']:>4d}"
                  f"  gap={r['gap']:+d}")
    print(f"  -> {OUT}")
    return 1 if result["n_anomaly"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Tier 1 free-CPU exact ladder (validation plan, resolves GATE-1).

Threads ONE frozen OPEN-cell list (the critic's requirement) through two free producers, cheapest first:

  1. FREEZE: from the committed oracle snapshot, take every OPEN cell (best_known strictly above the
     strongest cheap lower bound, per R0.8) within a TRACTABLE band (small candidate set + small witness
     so exact CP-SAT is definitive), sorted deterministically. This list is embedded in the output.
  2. GREEDY first (covering_reproduction_probe.probe_cell): a $0 greedy beat short-circuits the exact run
     on that cell.
  3. EXACT (covering_exact_producer.solve_cell): on the cells greedy did NOT beat, prove OPTIMAL (record
     tight -> no beat possible) or find a BEAT, within a per-cell budget.

Per-cell verdict: BEAT (found < best_known, re-checked by verify_covering) / OPTIMAL (found == best_known,
proven optimal) / reproduced (== record, not proven optimal at budget) / still-open (no proof within budget)
/ above-record. GATE-1: any BEAT -> a reachable-and-renderable frontier exists (the deferred proof-edge
becomes worth reconsidering, via operator+ADR). Zero beats with the smallest cells proven optimal -> the
reachable OPEN band is dead for $0.

Audit/measurement only — never promulgates, never touches the trust core. Writes incremental JSON so a long
run is recoverable.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from math import comb
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT))

import covering_exact_producer as exact  # noqa: E402
import covering_reproduction_probe as greedy  # noqa: E402
import covering_table_oracle as ora  # noqa: E402
from covering_verify import verify_covering  # noqa: E402

OUT = _ROOT / "docs" / "results" / "tier1_exact_ladder.json"

# Frozen tractability band (the one canonical list, threaded through greedy + exact).
BAND = {"max_candidate_blocks": 2000, "max_t_subsets": 5000, "max_best_known": 50}


def _counting(v, k, t):
    d = comb(k, t)
    return 0 if d == 0 else -(-comb(v, t) // d)


def cheap_lb(v, k, t):
    return max(ora.schonheim(v, k, t), _counting(v, k, t))


def frozen_open_cells(snap) -> list[tuple]:
    """Deterministic OPEN-cell list within the tractable band, sorted by (candidate count, t-subsets, best)."""
    cells = []
    for (v, k, t), bk in snap.items():
        if bk <= cheap_lb(v, k, t):
            continue  # OPTIMAL by a cheap bound -> settled, not a re-open candidate
        cvk, cvt = comb(v, k), comb(v, t)
        if cvk <= BAND["max_candidate_blocks"] and cvt <= BAND["max_t_subsets"] and bk <= BAND["max_best_known"]:
            cells.append((v, k, t, bk, cvk, cvt))
    cells.sort(key=lambda c: (c[4], c[5], c[3], c[0], c[1], c[2]))
    return cells


def run_cell(v, k, t, bk, *, greedy_cap, exact_cap):
    row = {"cell": f"C({v},{k},{t})", "v": v, "k": k, "t": t, "best_known": bk,
           "cheap_lb": cheap_lb(v, k, t)}
    # 1) greedy first
    g = greedy.probe_cell(v, k, t, restarts=200, time_cap=greedy_cap)
    row["greedy"] = {"found": g["found"], "status": g["status"], "secs": g["secs"]}
    if g["status"] == "BEATS" and g["valid"]:
        row["verdict"] = "BEAT"
        row["beat_found"] = g["found"]
        row["beat_source"] = "greedy"
        return row
    # 2) exact on the rest
    e = exact.solve_cell(v, k, t, time_cap=exact_cap)
    row["exact"] = {"found": e["found"], "status": e["status"],
                    "proven_optimal": e["proven_optimal"], "wall": e["wall"],
                    "candidate_blocks": e["candidate_blocks"]}
    if e["found"] is not None and e["found"] < bk:
        ok, reason = verify_covering([frozenset(b) for b in e["blocks"]], v, k, t)
        row["verdict"] = "BEAT" if ok else "BUG(false-beat)"
        row["beat_found"] = e["found"] if ok else None
        row["beat_blocks"] = [sorted(b) for b in e["blocks"]] if ok else None
        row["beat_source"] = "exact"
        row["beat_reason"] = reason
    elif e["found"] == bk and e["proven_optimal"]:
        row["verdict"] = "OPTIMAL"
    elif e["found"] == bk:
        row["verdict"] = "reproduced-not-proven"
    elif e["found"] is None:
        row["verdict"] = "still-open"
    else:
        row["verdict"] = "above-record"
    return row


def summarize(rows: list[dict], frozen: list[dict], elapsed_s: float) -> dict:
    """Aggregate per-cell rows into the GATE-1 report. The BINDING result is `beats`: 0 beats means no
    reachable-and-beatable frontier was found by the free ladder. `optimal` (proven) vs the budget-limited
    remainder (reproduced-not-proven / above-record) is the optimality breakdown, NOT a beat signal."""
    beats = [r for r in rows if r["verdict"] == "BEAT"]
    optimal = [r for r in rows if r["verdict"] == "OPTIMAL"]
    reproduced = [r for r in rows if r["verdict"] == "reproduced-not-proven"]
    above = [r for r in rows if r["verdict"] == "above-record"]
    still_open = [r for r in rows if r["verdict"] == "still-open"]
    bugs = [r for r in rows if str(r["verdict"]).startswith("BUG")]
    gate1 = "BEAT-EXISTS" if beats else "NO-REACHABLE-BEAT"
    return {"status": "complete", "gate1": gate1, "band": BAND,
            "n_cells": len(rows), "beats": len(beats), "optimal": len(optimal),
            "reproduced_not_proven": len(reproduced), "above_record": len(above),
            "still_open": len(still_open), "bugs": len(bugs),
            "optimality_proven": f"{len(optimal)}/{len(rows)}", "elapsed_s": elapsed_s,
            "frozen_cell_list": frozen, "rows": rows,
            "reading": ("GATE-1. The binding result is `beats`. BEAT-EXISTS = a free, kernel-checkable "
                        "record beat on a reachable cell -> the deferred discharge proof-edge becomes worth "
                        "reconsidering (operator+ADR; route any beat via covering_check.py). "
                        "NO-REACHABLE-BEAT = neither greedy nor exact CP-SAT beat ANY record on the "
                        "tractable OPEN band -> no reachable-and-beatable frontier for free; freeze the "
                        "proof-edge. `optimal` cells are PROVEN tight (record == exact optimum); "
                        "reproduced-not-proven/above-record cells found no beat but did not prove optimality "
                        "within the per-cell budget (raising the budget could prove more, but cannot create "
                        "a beat that exact search already failed to find).")}


def main() -> int:
    ap = argparse.ArgumentParser(description="Tier 1 free-CPU exact ladder over the frozen OPEN-cell band.")
    ap.add_argument("--summarize-only", action="store_true",
                    help="recompute the GATE-1 header from rows already in the output file (no cell re-run)")
    ap.add_argument("--greedy-cap", type=float, default=5.0)
    ap.add_argument("--exact-cap", type=float, default=120.0)
    ap.add_argument("--limit", type=int, default=0, help="cap the number of cells (0 = all)")
    ap.add_argument("--resume", action="store_true",
                    help="reuse rows already present in the output file (skip recomputing finished cells)")
    args = ap.parse_args()

    snap = ora.load_snapshot()[0]
    cells = frozen_open_cells(snap)
    if args.limit:
        cells = cells[: args.limit]
    frozen = [{"cell": f"C({v},{k},{t})", "v": v, "k": k, "t": t, "best_known": bk,
               "candidate_blocks": cvk, "t_subsets": cvt} for (v, k, t, bk, cvk, cvt) in cells]

    if args.summarize_only:
        prev = json.loads(OUT.read_text())
        report = summarize(prev["rows"], prev.get("frozen_cell_list", frozen), prev.get("elapsed_s", 0.0))
        OUT.write_text(json.dumps(report, indent=2) + "\n")
        print(f"GATE-1: {report['gate1']}  beats={report['beats']} proven-optimal={report['optimality_proven']} "
              f"reproduced-not-proven={report['reproduced_not_proven']} above-record={report['above_record']} "
              f"still-open={report['still_open']} bugs={report['bugs']}")
        return 1 if report["bugs"] else 0

    done_by_cell: dict[str, dict] = {}
    if args.resume and OUT.exists():
        prev = json.loads(OUT.read_text())
        done_by_cell = {r["cell"]: r for r in prev.get("rows", [])}
        print(f"resume: {len(done_by_cell)} cells already computed, reusing them")

    print(f"Tier 1 exact ladder: {len(cells)} frozen OPEN cells "
          f"(band {BAND}); greedy_cap={args.greedy_cap}s exact_cap={args.exact_cap}s")
    rows = []
    t0 = time.time()
    for i, (v, k, t, bk, cvk, cvt) in enumerate(cells, 1):
        cell_name = f"C({v},{k},{t})"
        if cell_name in done_by_cell:
            rows.append(done_by_cell[cell_name])
            continue
        r = run_cell(v, k, t, bk, greedy_cap=args.greedy_cap, exact_cap=args.exact_cap)
        rows.append(r)
        ex = r.get("exact", {})
        print(f"  [{i:>3d}/{len(cells)}] {r['cell']:11s} best={bk:>3d} "
              f"greedy={r['greedy']['found']:>3d}/{r['greedy']['status']:<10s} "
              f"verdict={r['verdict']}"
              + (f" exact={ex.get('found')} opt={ex.get('proven_optimal')} ({ex.get('wall')}s)" if ex else ""))
        # incremental persist (recoverable)
        beats = [x for x in rows if x["verdict"] == "BEAT"]
        partial = {"status": "in-progress", "done": i, "total": len(cells),
                   "band": BAND, "frozen_cell_list": frozen, "rows": rows,
                   "beats": len(beats), "elapsed_s": round(time.time() - t0, 1)}
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(partial, indent=2) + "\n")

    report = summarize(rows, frozen, round(time.time() - t0, 1))
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nGATE-1: {report['gate1']}")
    print(f"  beats={report['beats']} proven-optimal={report['optimal']} "
          f"reproduced-not-proven={report['reproduced_not_proven']} above-record={report['above_record']} "
          f"still-open={report['still_open']} bugs={report['bugs']}  ({report['elapsed_s']}s)")
    if beats:
        for r in beats:
            print(f"  BEAT {r['cell']}: found {r.get('beat_found')} < record {r['best_known']} "
                  f"(via {r.get('beat_source')})")
    print(f"  -> {OUT}")
    return 1 if report["bugs"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

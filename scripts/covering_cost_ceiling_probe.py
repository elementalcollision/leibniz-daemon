"""verify_covering / render cost-ceiling probe (validation plan Tier 0, R0.3 — the free-CPU analog of the
kernel decide-wall, GATE-2).

`verify_covering` (called inside `render_covering_lean`) iterates EVERY t-subset of {0..v-1} —
`combinations(range(v), t)`, i.e. C(v,t) of them — with NO cost cap (covering has no RENDER_SUBSET_CAP,
unlike ramsey). For large (v,t) this Python pre-check alone becomes the bottleneck BEFORE the kernel ever
runs. This probe measures where that happens, so we can decide whether `render_covering_lean` needs a
refuse-above-threshold cap.

It times the unavoidable enumeration floor (build each t-subset as `verify` does) across a (v,t) ladder and
reports the smallest cell whose pre-check enumeration exceeds chosen budgets. Pure stdlib; no kernel, no
trust touch. Output: docs/results/covering_cost_ceiling.json + a printed reading.
"""
from __future__ import annotations

import importlib.util
import json
import time
from itertools import combinations
from math import comb
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "covering_cost_ceiling.json"

BUDGETS = (1.0, 5.0, 30.0)   # seconds; thresholds we care about for render-time refusal


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


cov = _load("covering_verify", "scripts/covering_verify.py")


def _enumerate_floor(v: int, t: int, hard_cap_s: float = 8.0) -> tuple[float, bool]:
    """Time the t-subset enumeration floor that verify_covering pays (build set(s) per t-subset). Aborts
    early if it blows past hard_cap_s. Returns (seconds, completed)."""
    t0 = time.perf_counter()
    count = 0
    for s in combinations(range(v), t):
        _ = set(s)
        count += 1
        if (count & 0x3FFFF) == 0 and time.perf_counter() - t0 > hard_cap_s:
            return time.perf_counter() - t0, False
    return time.perf_counter() - t0, True


def probe(ladder=None) -> dict:
    # a ladder spanning cheap (t=2) to enumeration-heavy (t=6 at larger v)
    ladder = ladder or [
        (9, 3, 2), (13, 3, 2), (20, 4, 2), (30, 5, 3), (40, 6, 3), (50, 6, 3),
        (40, 6, 4), (30, 6, 5), (35, 7, 5), (40, 8, 6), (45, 8, 6), (50, 9, 6),
    ]
    rows = []
    for (v, k, t) in ladder:
        n_tsubsets = comb(v, t)
        secs, done = _enumerate_floor(v, t)
        rows.append({"v": v, "k": k, "t": t, "t_subsets": n_tsubsets,
                     "enum_floor_secs": round(secs, 3), "completed": done})
    # smallest cell exceeding each budget (by t_subsets order)
    thresholds = {}
    ordered = sorted(rows, key=lambda r: r["t_subsets"])
    for b in BUDGETS:
        hit = next((r for r in ordered if (not r["completed"]) or r["enum_floor_secs"] > b), None)
        thresholds[str(b)] = (None if hit is None
                              else {"cell": f"C({hit['v']},{hit['k']},{hit['t']})",
                                    "t_subsets": hit["t_subsets"],
                                    "enum_floor_secs": hit["enum_floor_secs"]})
    return {"rows": rows, "thresholds_smallest_cell_over_budget": thresholds,
            "note": ("verify_covering cost is >= this enumeration floor (it also tests block coverage per "
                     "subset). A render-time RENDER_SUBSET_CAP should refuse cells whose C(v,t) floor "
                     "exceeds the chosen budget, mirroring ramsey's cap.")}


def main() -> int:
    res = probe()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print("covering verify/render cost-ceiling probe (t-subset enumeration floor):")
    for r in res["rows"]:
        flag = "" if r["completed"] else "  [ABORTED > hard cap]"
        print(f"  C({r['v']},{r['k']},{r['t']})  C(v,t)={r['t_subsets']:>12,d}  "
              f"floor={r['enum_floor_secs']:>7.3f}s{flag}")
    print("  smallest cell over budget:")
    for b, hit in res["thresholds_smallest_cell_over_budget"].items():
        print(f"    > {b}s: {hit['cell'] if hit else 'none in ladder'}"
              + (f" (C(v,t)={hit['t_subsets']:,}, {hit['enum_floor_secs']}s)" if hit else ""))
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

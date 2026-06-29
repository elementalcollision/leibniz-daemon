"""Covering-designs reproduction probe (ADR 0042/0043 — the gate before any billable Track-D swing).

The sharpened Gate-B0 criterion's deepest leg (the witness panel's "frontier reproducibility under
budget"): can a GENERIC search — the kind an LLM-in-sandbox would actually write, NOT a hyper-tuned
simulated annealer — REPRODUCE current La Jolla best-known coverings? If a generic baseline reaches the
frontier, the producer is in the game and a stronger producer (Track D) is a priced bet. If it only
reproduces easy/old cells and plateaus above best-known, the producer wall recurs (the CWC signature)
and we bank Track A (the two-domain amplification instrument) instead of funding a swing.

Baseline = greedy set-cover (add the block covering the most still-uncovered t-subsets; randomized
tie-break) + restarts + redundant-block pruning. Deterministic (LCG seed; no Math.random). Every covering
it reports is validated by covering_verify.verify_covering. Pure CPU, no spend, no kernel needed (the
verifier already proves validity; the kernel is for the final audited witness, not this measurement).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from itertools import combinations
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
sys.path.insert(0, str(_ROOT))

import covering_table_oracle as ora  # noqa: E402
from covering_verify import verify_covering  # noqa: E402

# Pre-registered cells (fixed BEFORE running — no post-hoc cherry-picking). t=2, small-witness band,
# spanning easy (Steiner-structured) -> medium -> harder. Chosen so C(v,k) is a tractable candidate set.
PRE_REGISTERED = [
    (7, 3, 2), (9, 3, 2), (13, 3, 2), (15, 3, 2),
    (10, 4, 2), (13, 4, 2), (16, 4, 2),
    (11, 5, 2), (13, 5, 2), (16, 6, 2),
]


class _LCG:
    def __init__(self, seed): self.s = seed & 0xFFFFFFFF
    def nxt(self):
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s
    def shuffled(self, xs):
        a = list(xs)
        for i in range(len(a) - 1, 0, -1):
            j = self.nxt() % (i + 1)
            a[i], a[j] = a[j], a[i]
        return a


def _greedy(v, k, t, rng, blocks, cover_map, all_t):
    uncovered = set(all_t)
    chosen = []
    while uncovered:
        best_b, best_gain = None, -1
        for b in rng.shuffled(blocks):                 # randomized tie-break across restarts
            g = len(cover_map[b] & uncovered)
            if g > best_gain:
                best_gain, best_b = g, b
        chosen.append(best_b)
        uncovered -= cover_map[best_b]
    return chosen


def _prune(chosen, cover_map):
    chosen = list(chosen)
    changed = True
    while changed:
        changed = False
        for i in range(len(chosen)):
            others = chosen[:i] + chosen[i + 1:]
            covered = set()
            for o in others:
                covered |= cover_map[o]
            if cover_map[chosen[i]] <= covered:
                chosen = others
                changed = True
                break
    return chosen


def probe_cell(v, k, t, *, restarts=300, time_cap=25.0, seed=0x9E3779B1):
    blocks = [tuple(b) for b in combinations(range(v), k)]
    all_t = [tuple(s) for s in combinations(range(v), t)]
    cover_map = {b: frozenset(combinations(b, t)) for b in blocks}
    rng = _LCG(seed ^ (v * 73856093) ^ (k * 19349663) ^ (t * 83492791))
    best = None
    t0 = time.time()
    r = 0
    while r < restarts and time.time() - t0 < time_cap:
        cov = _prune(_greedy(v, k, t, rng, blocks, cover_map, all_t), cover_map)
        if best is None or len(cov) < len(best):
            best = cov
        r += 1
    ok, reason = verify_covering([frozenset(b) for b in best], v, k, t)
    bk = ora.best_known(v, k, t)
    found = len(best)
    gap = (found - bk) if bk is not None else None
    if bk is None:
        status = "untabulated"
    elif found < bk:
        status = "BEATS"
    elif found == bk:
        status = "REPRODUCED"
    elif found <= bk + max(1, round(0.05 * bk)):
        status = "CLOSE"
    else:
        status = "PLATEAU"
    return {"cell": f"C({v},{k},{t})", "v": v, "k": k, "t": t, "best_known": bk,
            "found": found, "gap": gap, "status": status, "valid": ok, "reason": reason,
            "restarts": r, "secs": round(time.time() - t0, 1), "candidate_blocks": len(blocks)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Covering reproduction probe: can a GENERIC baseline reach "
                                             "the La Jolla frontier? Gates the Track-D producer swing.")
    ap.add_argument("--restarts", type=int, default=300)
    ap.add_argument("--time-cap", type=float, default=25.0)
    ap.add_argument("--out", help="write the JSON report here")
    args = ap.parse_args()

    rows = [probe_cell(v, k, t, restarts=args.restarts, time_cap=args.time_cap) for (v, k, t) in PRE_REGISTERED]
    reproduced = [r for r in rows if r["status"] in ("REPRODUCED", "BEATS")]
    close = [r for r in rows if r["status"] == "CLOSE"]
    plateau = [r for r in rows if r["status"] == "PLATEAU"]
    all_valid = all(r["valid"] for r in rows)
    # GREEN if the generic baseline reproduces (or beats) a majority AND reaches several non-trivial cells
    verdict = ("GREEN" if len(reproduced) >= (len(rows) + 1) // 2 and len(reproduced) >= 4
               else "AMBER" if reproduced or close
               else "RED")
    report = {"verdict": verdict, "reproduced": len(reproduced), "close": len(close),
              "plateau": len(plateau), "cells": len(rows), "all_valid": all_valid, "rows": rows,
              "reading": ("GREEN = generic search reaches the frontier; the producer is in the game and a "
                          "stronger producer (Track D) is a priced bet. RED = only easy cells reproduce; "
                          "the producer wall recurs (CWC signature) -> bank Track A (amplification), do "
                          "not fund the swing. AMBER = mixed; needs a sharper budget/baseline call.")}

    print(f"reproduction probe: verdict {verdict}  "
          f"(reproduced/beat {len(reproduced)}/{len(rows)}, close {len(close)}, plateau {len(plateau)}; "
          f"all valid={all_valid})")
    for r in rows:
        gp = f"{r['gap']:+d}" if r["gap"] is not None else " n/a"
        print(f"  [{r['status']:10s}] {r['cell']:11s} best_known={str(r['best_known']):>4s} "
              f"found={r['found']:>4d} gap={gp}  ({r['restarts']}r/{r['secs']}s, {r['candidate_blocks']} blocks)")
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n")
        print(f"  -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

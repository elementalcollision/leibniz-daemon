"""Build an amplification feed from the Tier-1 proven-OPTIMAL t>=3 coverings (validation plan follow-up).

The GATE-2 maxRecDepth fix made covering t>=3 kernel-checks possible for the first time. The Tier-1 exact
ladder proved 22 covering records optimal; the t>=3 ones (previously un-kernel-checkable) are now a clean,
high-quality addition to the audit-tier kernel-checked corpus: each is a CP-SAT-proven-optimal covering,
re-checked by the Lean kernel, novelty = equals-record (not a beat — the D-line is banked).

This emits the FEED only (re-solving each cell for a minimal witness); the actual kernel-verify + merge +
render is done by scripts/amplify.py on the emitted feed (audit-tier; never promulgates, no trust touch).

RUNS WHERE: free-CPU (CP-SAT witness construction). The subsequent `amplify.py` run needs docker for the
kernel step (operator/self-hosted).
"""
from __future__ import annotations

import json
import sys
from math import comb
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

import covering_exact_producer as exact  # noqa: E402
from covering_verify import verify_covering  # noqa: E402

LADDER = _ROOT / "docs" / "results" / "tier1_exact_ladder.json"
OUT = _ROOT / "docs" / "results" / "tier1_optimal_covering_feed.json"
CVT_CAP = 1000   # stay safely under the GATE-2 kernel wall (~C(v,t)=1140)


def build_feed() -> list[dict]:
    rows = json.loads(LADDER.read_text())["rows"]
    cells = [r for r in rows
             if r["verdict"] == "OPTIMAL" and r["t"] >= 3 and comb(r["v"], r["t"]) <= CVT_CAP]
    cells.sort(key=lambda r: (r["t"], comb(r["v"], r["t"])))
    feed = []
    for r in cells:
        v, k, t, bk = r["v"], r["k"], r["t"], r["best_known"]
        sol = exact.solve_cell(v, k, t, time_cap=30.0)
        if not sol.get("found") or sol["found"] != bk:
            print(f"  skip C({v},{k},{t}): re-solve found {sol.get('found')} != record {bk}")
            continue
        blocks = [sorted(b) for b in sol["blocks"]]
        ok, reason = verify_covering([frozenset(b) for b in blocks], v, k, t)
        if not ok:
            print(f"  skip C({v},{k},{t}): witness failed verify_covering ({reason})")
            continue
        feed.append({"domain": "covering", "v": v, "k": k, "t": t, "blocks": blocks,
                     "source": "tier1-exact-optimal",
                     "note": f"CP-SAT-proven-optimal C({v},{k},{t})={bk} (Tier 1); kernel-checked t>=3 "
                             f"(enabled by the GATE-2 maxRecDepth fix)"})
        print(f"  C({v},{k},{t}) optimal={bk}  witness B={len(blocks)}  ready")
    return feed


def main() -> int:
    print(f"building Tier-1 proven-optimal t>=3 covering feed (C(v,t)<={CVT_CAP}):")
    feed = build_feed()
    OUT.write_text(json.dumps(feed, indent=2) + "\n")
    print(f"\n{len(feed)} feed entries -> {OUT}")
    print("next: python3 scripts/amplify.py --feed " + str(OUT) +
          " --render docs/results/amplification_corpus.md"
          " --reading-room docs/results/amplification_reading_room.md   (needs docker for the kernel)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""GATE-2 — covering kernel-`decide` wall probe (validation plan Tier 2).

Locates where the SOUND kernel check (`render_covering_lean` -> Lean `decide`) goes intractable, so we can
(a) state the honest range over which the amplification spine can kernel-check a covering, and (b) decide
whether `render_covering_lean` needs a `RENDER_SUBSET_CAP` like Ramsey's. Covering's predicate is a
polynomial-size computation (enumerate C(v,t) t-subsets, each tested against the blocks), so — unlike the
exponential Ramsey predicate (Gate B2) — we expect a milder, higher wall; this MEASURES it.

For each (v,k,t) on a ladder of increasing C(v,t): build a near-minimal valid covering (exact CP-SAT, with
an all-k-subsets fallback), render the real Lean theorem, and time the kernel verdict under a per-cell
timeout. A `None` verdict with docker present = the kernel did not finish in the budget = past the wall.
Early-stops after two consecutive timeouts. Emits docs/results/covering_kernel_wall.json.

RUNS WHERE: **operator machine with docker + `leibniz-lean:v4.31.0`** (the kernel is the whole point). It
refuses to run without the image (exit 2), mirroring scripts/run_kernel_tests.sh. The witness construction
(CP-SAT) is free-CPU; only the per-cell verdict needs the kernel.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from math import comb
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

import covering_exact_producer as exact  # noqa: E402
from covering_verify import render_covering_lean, verify_covering  # noqa: E402

OUT = _ROOT / "docs" / "results" / "covering_kernel_wall.json"

# ladder of (v,k,t) by increasing C(v,t) — the kernel's per-check enumeration size
LADDER = [(7, 3, 2), (9, 3, 2), (13, 3, 2), (10, 4, 3), (20, 4, 2), (12, 4, 3),
          (14, 4, 3), (15, 5, 3), (16, 5, 3), (18, 5, 3), (20, 5, 3), (15, 4, 4)]


def witness_for(v, k, t, *, solve_cap=15.0):
    """A valid (near-minimal) covering for the cell: exact CP-SAT if it returns a solution, else the
    guaranteed-valid all-k-subsets covering. Verified before return."""
    try:
        r = exact.solve_cell(v, k, t, time_cap=solve_cap)
        blocks = [list(b) for b in r["blocks"]] if r.get("found") else None
    except Exception:
        blocks = None
    if not blocks:
        from itertools import combinations
        blocks = [list(c) for c in combinations(range(v), k)]
    ok, _ = verify_covering([frozenset(b) for b in blocks], v, k, t)
    if not ok:  # pragma: no cover - defensive; both sources are valid by construction
        from itertools import combinations
        blocks = [list(c) for c in combinations(range(v), k)]
    return blocks


def probe(ladder=None, *, timeout_s=60.0, stop_after_timeouts=2) -> dict:
    from leibniz.backends.lean_cli import LeanCliBackend
    ladder = ladder or LADDER
    rows = []
    consec_timeout = 0
    for (v, k, t) in ladder:
        blocks = witness_for(v, k, t)
        src = render_covering_lean(v, k, t, blocks)
        bk = LeanCliBackend(timeout_s=int(timeout_s))
        t0 = time.perf_counter()
        verdict = bk.check_source(src)            # True / False / None(=timeout, docker confirmed present)
        wall = round(time.perf_counter() - t0, 2)
        status = ("verified" if verdict is True else "REJECTED(bug)" if verdict is False
                  else "intractable(timeout)")
        rows.append({"v": v, "k": k, "t": t, "t_subsets": comb(v, t), "blocks": len(blocks),
                     "kernel": status, "wall_s": wall})
        print(f"  C({v},{k},{t})  C(v,t)={comb(v, t):>6,d}  B={len(blocks):>4d}  {status:<22s} {wall:>6.2f}s")
        consec_timeout = consec_timeout + 1 if verdict is None else 0
        if consec_timeout >= stop_after_timeouts:
            print(f"  [early stop: {consec_timeout} consecutive timeouts — past the wall]")
            break
    verified = [r for r in rows if r["kernel"] == "verified"]
    walled = [r for r in rows if r["kernel"] == "intractable(timeout)"]
    bugs = [r for r in rows if r["kernel"] == "REJECTED(bug)"]
    return {
        "timeout_s": timeout_s, "rows": rows,
        "largest_verified": (max(verified, key=lambda r: r["t_subsets"]) if verified else None),
        "smallest_intractable": (min(walled, key=lambda r: r["t_subsets"]) if walled else None),
        "kernel_rejected_a_valid_witness": [r for r in bugs],  # MUST be empty (would be a soundness bug)
        "reading": ("GATE-2. 'verified' = the kernel decided the bound within the budget; "
                    "'intractable(timeout)' = decide did not finish (past the wall). If the wall sits "
                    "inside the snapshot's tabulated range, render_covering_lean needs a RENDER_SUBSET_CAP "
                    "and record-sized covering proofs need a certificate architecture (cf. Ramsey, Gate "
                    "B2). If it sits well above the amplification 'small band', render is honest as-is."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="GATE-2 covering kernel-decide wall probe (docker-gated).")
    ap.add_argument("--timeout", type=float, default=60.0, help="per-cell kernel timeout (s)")
    args = ap.parse_args()
    try:
        from leibniz.backends.lean_cli import available
    except Exception as e:
        print(f"FAIL: cannot import the Lean backend ({e}).", file=sys.stderr)
        return 2
    if not available():
        print("FAIL: this probe requires docker + the leibniz-lean image (operator-local; the kernel is "
              "the whole point). Run on the operator machine or the self-hosted `lean` runner.",
              file=sys.stderr)
        return 2
    print(f"covering kernel-decide wall probe (per-cell timeout {args.timeout}s):")
    res = probe(timeout_s=args.timeout)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    lv = res["largest_verified"]
    si = res["smallest_intractable"]
    print(f"  largest verified : {('C(%d,%d,%d) C(v,t)=%d (%.2fs)' % (lv['v'],lv['k'],lv['t'],lv['t_subsets'],lv['wall_s'])) if lv else 'none'}")
    print(f"  smallest walled  : {('C(%d,%d,%d) C(v,t)=%d' % (si['v'],si['k'],si['t'],si['t_subsets'])) if si else 'none in ladder'}")
    if res["kernel_rejected_a_valid_witness"]:
        print("  SOUNDNESS ALARM: kernel rejected a VALID witness — investigate before trusting the spine!")
    print(f"  -> {OUT}")
    return 1 if res["kernel_rejected_a_valid_witness"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

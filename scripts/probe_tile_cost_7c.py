"""Probe 7c (offline, no trust surface) — the DECISIVE tile-cost measurement the adversarial review demanded.

The 7a/7b findings' Schur-tiling de-risk borrowed the shipped lowRankOK N=60 timing (~86 s), which was measured
at rank r=8 with ~8-bit entries. But the tiles the tiling actually needs are FULL-RANK (dense Schur pivots)
with ~1000-bit rational/cleared-integer entries (7b: dense Schur entries ~1035 bits). "One big-Nat op is
GMP-flat" (7a curve A) does NOT license "an order-60 matmul-identity of 1000-bit entries is fast" — that is an
unmeasured extrapolation on three axes (fact count k-deep, full rank, entry size). This probe MEASURES the
real object: a COMPACT `List`-def order-N matrix-identity `mm A B == C` (a full matmul, the block-identity
building block), decided by the real Lean 4.31 kernel, at small vs large ENTRY BIT-SIZE and growing N.

  - If order-60 with ~1000-bit entries stays near the ~8-bit time, entry size is ~free for a COMPACT decide
    (the reduction reuses; per-op GMP cost dominates) -> the tiling tiles are feasible -> CLAIM 2 upgrades.
  - If it walls (or blows up vs the 8-bit baseline), the effective tile ceiling drops below 60 for realistic
    (full-rank, large-entry) tiles -> the tiling de-risk is downgraded, k rises, budget grows.

Run:  python scripts/probe_tile_cost_7c.py   (needs docker + leibniz-lean-repl; skips cleanly if absent)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "probe_tile_cost_7c.json"
HDR = "set_option maxHeartbeats 0\nset_option maxRecDepth 1000000\n"

_PRELUDE = (
    "def dotp (u v : List Int) : Int := (List.zipWith (· * ·) u v).foldl (· + ·) 0\n"
    "def col (m : List (List Int)) (j : Nat) : List Int := m.map (fun r => r.getD j 0)\n"
    "def mm (a b : List (List Int)) : List (List Int) :=\n"
    "  a.map (fun r => (List.range (b.headD []).length).map (fun j => dotp r (col b j)))\n"
)


def _lcg(seed):
    s = seed & 0x7FFFFFFF
    while True:
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        yield s


def _mat(n, bits, g):
    hi = 1 << max(bits - 1, 1)
    return [[(next(g) % (2 * hi)) - hi for _ in range(n)] for _ in range(n)]


def _lit(m):
    return "[" + ", ".join("[" + ", ".join(str(x) for x in row) + "]" for row in m) + "]"


def matmul_id_src(n: int, bits: int) -> str:
    g = _lcg(20260705 + n * 131 + bits)
    a = _mat(n, bits, g)
    b = _mat(n, bits, g)
    c = [[sum(a[i][k] * b[k][j] for k in range(n)) for j in range(n)] for i in range(n)]
    return (HDR + _PRELUDE
            + f"def A : List (List Int) := {_lit(a)}\n"
            + f"def B : List (List Int) := {_lit(b)}\n"
            + f"def C : List (List Int) := {_lit(c)}\n"
            + "theorem t : (mm A B == C) = true := by decide")


def _run(bk, src):
    r = bk._run(src, ())
    return (r is not None) and not any(m.get("severity") == "error" for m in (r.get("messages") or []))


def main(cap_s: int = 160) -> int:
    print("=== Probe 7c — realistic tile cost: compact order-N matmul-identity decide vs entry bit-size ===")
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
    except Exception:
        available = lambda: False  # noqa: E731
    if not available():
        print("  SKIP (needs docker + leibniz-lean-repl)")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({"gate": "AMBER(lean-unavailable)"}, indent=2) + "\n")
        return 0
    bk = LeanReplBackend(timeout_s=cap_s)
    _run(bk, HDR + "theorem warm : (1 + 1 == 2) = true := by decide")

    rows = []
    for n in (20, 40, 60):
        for bits in (8, 1000):
            t0 = time.time()
            ok = _run(bk, matmul_id_src(n, bits))
            secs = round(time.time() - t0, 1)
            rows.append({"n": n, "entry_bits": bits, "ok": ok, "secs": secs})
            print(f"    order {n:>3}, {bits:>4}-bit entries: ok={ok} {secs}s", flush=True)

    def t(n, b):
        return next((r["secs"] for r in rows if r["n"] == n and r["entry_bits"] == b and r["ok"]), None)
    # entry-size penalty at fixed order (does 1000-bit slow a COMPACT decide vs 8-bit?)
    pen60 = (t(60, 1000) / t(60, 8)) if (t(60, 1000) and t(60, 8)) else None
    pen40 = (t(40, 1000) / t(40, 8)) if (t(40, 1000) and t(40, 8)) else None
    o60_ok = next((r["ok"] for r in rows if r["n"] == 60 and r["entry_bits"] == 1000), False)
    entry_size_cheap = bool(pen60 and pen60 < 3.0)
    out = {"gate": "GREEN(measured)", "tier": "probe", "ev": "AMPLIFICATION-research", "rows": rows,
           "order60_1000bit_ok": o60_ok, "order60_1000bit_secs": t(60, 1000),
           "entry_size_penalty_order60": (round(pen60, 2) if pen60 else None),
           "entry_size_penalty_order40": (round(pen40, 2) if pen40 else None),
           "entry_size_cheap_for_compact_decide": entry_size_cheap,
           "reading": (
               "The DECISIVE tile-cost measurement (adversarial review of the 7a/7b findings). A COMPACT "
               "order-N full matmul-identity decide is the block-identity building block the Schur-tiling path "
               f"needs. Order-60 with ~1000-bit entries: {'VERIFIED in ' + str(t(60, 1000)) + 's' if o60_ok else 'DID NOT verify within the ' + str(cap_s) + 's cap'}. "
               f"Entry-size penalty at order-60 (1000-bit / 8-bit): {('~' + str(round(pen60, 1)) + 'x') if pen60 else 'n/a'} "
               f"— so entry size is {'~free for a compact decide (reduction reuses; per-op GMP dominates)' if entry_size_cheap else 'NOT free; large entries materially slow the compact decide'}. "
               + ("NET: realistic (full-rank, 1000-bit-entry) order-60 tiles stay feasible -> the Schur-tiling "
                  "tiles are tractable, upgrading the tiling de-risk from 'plausible' toward 'measured'."
                  if (o60_ok and entry_size_cheap) else
                  "NET: realistic full-rank, large-entry order-60 tiles are HEAVIER than the borrowed r=8/8-bit "
                  "point -> the effective tiling ceiling drops below 60 for real tiles; the tiling de-risk is "
                  "downgraded (k rises, budget grows). Confirms the adversarial review's HIGH-severity gap."))}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\n  order-60 @1000-bit: ok={o60_ok} {t(60, 1000)}s | entry-size penalty ~{pen60}x")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

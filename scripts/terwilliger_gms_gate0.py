"""GATE 0 — the GMS 2012 (Hamming) quadruple reduced-block-size probe (the GMS build's front kill gate).

The decisive question the external witness panel split on: do the GMS quadruple SDP's *reduced* PSD blocks
stay O(n) (build viable — our native per-block integer-LDLT kernel checker verified 26x26) or grow O(n²)
(past the kernel ceiling → the plan's kernel-certification path is dead)?

Answer, read from the actual paper (arXiv:1005.4959, §4 "Fully block diagonalizing M_S(x)"): the reduced block
for orbit pair (k,l) is the submatrix of Γ_{α,k} ⊗ Γ_{β,l} whose rows/columns are indexed by **pairs** (i,i')
with i ∈ [k,n−k], i' ∈ [l,n−l], and i+i' ∈ [d,n] (plus an m-dependent constraint; a further S₂ action splits
each block sym/antisym, ~halving but not changing the order). The pair-indexing makes the block O(n²) — UNLIKE
the constant-weight (Johnson) case (D1), where fixed weight links i,i' into one index and blocks stay O(n).

This module computes the dominant-count block-dimension profile (pure Python, CI-safe, no deps). It is a
SCOPING estimate — the exact reduced orders need the m-constraint + S₂ split, applied here as an optional
halving — but the ORDER (O(n²), hundreds at n≥19) and the RED verdict are robust to those refinements.
"""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "terwilliger_gms_gate0.json"

KERNEL_CEILING = 30          # measured native integer-LDLT kernel ceiling (~26x26 verified for A(25,10))
SWEEP_D = (6, 8, 10, 12)


def block_dim(n: int, d: int, k: int, l: int) -> int:  # noqa: E741 -- l mirrors the paper's block index
    """#{(i,i') : k≤i≤n−k, l≤i'≤n−l, d ≤ i+i' ≤ n} — the reduced (k,l) block order (dominant count)."""
    return sum(1 for i in range(k, n - k + 1) for ip in range(l, n - l + 1) if d <= i + ip <= n)


def profile(n: int, d: int) -> dict:
    """Largest reduced block, #blocks, and total PSD dimension for cell (n,d)."""
    best = 0
    arg = None
    nblocks = 0
    total = 0
    for k in range(n // 2 + 1):
        for l in range(k, n // 2 + 1):  # noqa: E741 -- 0 ≤ k ≤ l ≤ ⌊n/2⌋
            bd = block_dim(n, d, k, l)
            if bd > 0:
                nblocks += 1
                total += bd
                if bd > best:
                    best, arg = bd, (k, l)
    return {"n": n, "d": d, "largest_block": best, "largest_at_kl": arg,
            "largest_block_s2_halved": (best + 1) // 2, "n_blocks": nblocks, "total_psd_dim": total,
            "three_point_largest": n + 1}


def main() -> int:
    rows = [profile(n, d) for d in SWEEP_D for n in range(19, 29)]
    small = [profile(n, d) for (n, d) in ((9, 6), (10, 6), (12, 6), (12, 8), (14, 8))]
    # RED if the S2-halved largest block exceeds the kernel ceiling on EVERY in-range target cell.
    over = [r for r in rows if r["largest_block_s2_halved"] > KERNEL_CEILING]
    verdict = "RED" if len(over) == len(rows) else ("AMBER" if over else "GREEN")
    res = {"verdict": verdict, "kernel_ceiling": KERNEL_CEILING,
           "rows": rows, "small_cells": small,
           "reading": ("GATE 0 (GMS Hamming quadruple reduced-block-size probe). Blocks are indexed by PAIRS "
                       "(i,i') with i+i' in [d,n] (arXiv:1005.4959 §4) => O(n²): the S₂-halved largest block is "
                       f"{rows[0]['largest_block_s2_halved']}..{max(r['largest_block_s2_halved'] for r in rows)} "
                       f"across n=19..28, vs the ~{KERNEL_CEILING} native-kernel integer-LDLT ceiling. RED = "
                       "every in-range target cell exceeds it (the plan's per-block kernel-certification path is "
                       "unreachable). Independently corroborated by GMS's own reported solve cost (13 days for "
                       "A(23,6), high-precision SDPA required). This REFUTES the O(n) reading (correct only for "
                       "the constant-weight/Johnson D1 case, where fixed weight collapses the second index) and "
                       "CONFIRMS the O(n²) reviewers for the unrestricted Hamming case.")}
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"GATE 0 (GMS Hamming quadruple block size): {verdict}")
    print(f"  {'n':>3} {'d':>3} {'largest':>8} {'halved':>7} {'#blocks':>8} vs 3pt / ceiling {KERNEL_CEILING}")
    for r in rows:
        if r["n"] in (19, 24, 28):
            print(f"  {r['n']:>3} {r['d']:>3} {r['largest_block']:>8} {r['largest_block_s2_halved']:>7} "
                  f"{r['n_blocks']:>8}   3pt~{r['three_point_largest']}")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

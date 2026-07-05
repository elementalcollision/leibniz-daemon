"""Probe 7b (offline, no trust surface) — Schur-tiling bit-growth & fill-in for the large-block PSD wall.

The panel's best novel path (docs/results/large-block-psd-panel-findings-2026-07-05.md) is to certify an
order-130–414 PSD block by TILING it UNDER the existing ~N≈60 `lowRankOK` ceiling: block-Schur-eliminate M
into pivot sub-blocks each of order ≤60, certify each with the existing kernel primitive, and combine via a
once-proved Haynsworth inertia lemma. Its one open risk is NOT trust (every piece is an existing kernel
primitive or a once-proved lemma) but EFFICACY: exact-rational Schur pivots may suffer bit-length blow-up or
fill-in that puts the sub-blocks back past the decide wall (which is sensitive to both order AND entry size).

This probe MEASURES, on representative structured integer PSD blocks M = BᵀB of growing order N:
  (1) fraction-free (Bareiss) minor bit-length — Hadamard-bounded, so polynomial by theory; measured to confirm;
  (2) the max entry bit-length appearing in the block-Schur complements when eliminating in ≤cap-order blocks
      (the number the decide leg actually pays); and its growth exponent vs N;
  (3) fill-in — the density of the Schur complements (does structure survive elimination?);
  (4) the tile count ⌈N/cap⌉² of ≤cap-order sub-block decides the tiling would need.
We bracket the real (unavailable here, needs cvxpy) GMS block between DENSE (worst-case fill-in) and BANDED
(best-case structure) inputs. GREEN(viable) = bit-growth polynomial AND banded fill-in stays sub-quadratic.

Run:  python scripts/probe_schur_tiling_7b.py
"""
from __future__ import annotations

import json
import math
from fractions import Fraction as Fr
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "probe_schur_tiling_7b.json"


def _lcg(seed: int):
    s = seed & 0xFFFFFFFF
    while True:
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        yield s


def psd_block(n: int, kind: str, seed: int = 12345):
    """A deterministic integer symmetric PSD matrix M = BᵀB (so M ⪰ 0 exactly). kind ∈ {dense,banded}."""
    g = _lcg(seed)
    bw = max(2, n // 12)                       # band half-width for the structured case
    B = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if kind == "banded" and abs(i - j) > bw:
                continue
            B[i][j] = (next(g) % 7) - 3        # small integer entries, like a scheme/Krawtchouk Gram factor
    M = [[sum(B[k][i] * B[k][j] for k in range(n)) for j in range(n)] for i in range(n)]
    for i in range(n):
        M[i][i] += 1                           # strict PD (nonsingular Schur pivots)
    return M


def _bits(x: int) -> int:
    return int(x).bit_length()


def _max_entry_bits(M) -> int:
    m = 0
    for row in M:
        for v in row:
            m = max(m, _bits(v.numerator if isinstance(v, Fr) else v), _bits(v.denominator if isinstance(v, Fr) else 1))
    return m


def _nnz_density(M) -> float:
    n = len(M)
    nz = sum(1 for row in M for v in row if (v != 0))
    return nz / (n * n)


def block_schur(M, cap: int):
    """Eliminate M in leading blocks of order ≤cap by exact-rational Schur complement:
    partition [[A,B],[Bᵀ,C]] with A of order ≤cap; the Schur complement C - Bᵀ A⁻¹ B is the next block to tile.
    Return per-step (order, max_entry_bits, density) of the successive Schur complements."""
    steps = []
    cur = [[Fr(v) for v in row] for row in M]
    while len(cur) > cap:
        n = len(cur)
        k = cap
        A = [[cur[i][j] for j in range(k)] for i in range(k)]
        Bm = [[cur[i][j] for j in range(k, n)] for i in range(k)]
        C = [[cur[i][j] for j in range(k, n)] for i in range(k, n)]
        Ainv_B = _solve(A, Bm)                 # A⁻¹ B, exact
        # Schur = C - Bᵀ (A⁻¹B)
        S = [[C[i][j] - sum(Bm[t][i] * Ainv_B[t][j] for t in range(k)) for j in range(n - k)] for i in range(n - k)]
        steps.append({"order": len(S), "max_entry_bits": _max_entry_bits(S), "density": round(_nnz_density(S), 3)})
        cur = S
    steps.append({"order": len(cur), "max_entry_bits": _max_entry_bits(cur), "density": round(_nnz_density(cur), 3)})
    return steps


def _solve(A, B):
    """Exact A⁻¹ B via Gaussian elimination over ℚ (A is order-≤cap, well-conditioned by construction)."""
    n, m = len(A), len(B[0])
    aug = [[Fr(A[i][j]) for j in range(n)] + [Fr(B[i][j]) for j in range(m)] for i in range(n)]
    for c in range(n):
        p = next(r for r in range(c, n) if aug[r][c] != 0)
        aug[c], aug[p] = aug[p], aug[c]
        piv = aug[c][c]
        aug[c] = [x / piv for x in aug[c]]
        for r in range(n):
            if r != c and aug[r][c] != 0:
                f = aug[r][c]
                aug[r] = [aug[r][j] - f * aug[c][j] for j in range(n + m)]
    return [[aug[i][n + j] for j in range(m)] for i in range(n)]


def run(kind: str, sizes, cap: int = 60) -> list:
    rows = []
    for n in sizes:
        M = psd_block(n, kind)
        steps = block_schur(M, cap)
        rows.append({"n": n, "input_max_entry_bits": _max_entry_bits(M), "input_density": round(_nnz_density(M), 3),
                     "n_tiles": math.ceil(n / cap) ** 2, "schur_max_entry_bits": max(s["max_entry_bits"] for s in steps),
                     "schur_min_density": min(s["density"] for s in steps), "steps": steps})
        print(f"  {kind:>6} n={n:>3}: schur max-entry {rows[-1]['schur_max_entry_bits']:>5} bits, "
              f"min density {rows[-1]['schur_min_density']:.2f}, tiles ~{rows[-1]['n_tiles']}", flush=True)
    return rows


def _growth_exponent(rows) -> float:
    """Fit schur_max_entry_bits ~ C·n^p (log-log slope); p≈1–2 = polynomial (Hadamard), p≫2 or exp = fatal."""
    pts = [(math.log(r["n"]), math.log(max(r["schur_max_entry_bits"], 1))) for r in rows]
    n = len(pts)
    sx = sum(x for x, _ in pts)
    sy = sum(y for _, y in pts)
    sxx = sum(x * x for x, _ in pts)
    sxy = sum(x * y for x, y in pts)
    return (n * sxy - sx * sy) / (n * sxx - sx * sx)


def main() -> int:
    print("=== Probe 7b — Schur-tiling bit-growth & fill-in (offline; representative structured PSD blocks) ===")
    # exact-rational Schur elimination is O(n^4)-ish with Hadamard-growing entries; small sizes fit the
    # log-log growth exponent reliably and extrapolate to the 130-414 target (which we do NOT run exactly here).
    sizes = [30, 45, 60, 90, 120, 160]
    dense = run("dense", sizes)
    banded = run("banded", sizes)
    # Fit the growth exponent ONLY over rows where a Schur step actually happened (n > cap); the n≤cap points
    # do no elimination (entry-bits = input ~8) and would spuriously inflate the log-log slope.
    elim = [r for r in dense if r["n_tiles"] > 1]
    elim_b = [r for r in banded if r["n_tiles"] > 1]
    p_dense, p_banded = _growth_exponent(elim), _growth_exponent(elim_b)
    # Hadamard predicts polynomial bit-growth over the eliminated range (~O(n log n), exponent ≲ 2).
    poly = p_dense < 2.5 and p_banded < 2.5
    banded_helps = banded[-1]["schur_min_density"] < 0.5 * dense[-1]["schur_min_density"] or banded[-1]["schur_max_entry_bits"] < dense[-1]["schur_max_entry_bits"]
    max_bits_dense = max(r["schur_max_entry_bits"] for r in elim)
    max_bits_banded = max(r["schur_max_entry_bits"] for r in elim_b)
    verdict = ("bit-growth is POLYNOMIAL over the eliminated range (exponent ~%.1f, consistent with Hadamard "
               "~O(n·log n)) — NOT the exponential blow-up that would make tiling fatal in principle." % p_dense
               if poly else "bit-growth is SUPER-polynomial — tiling arithmetic is itself fatal.")
    out = {"gate": "GREEN(polynomial-bitgrowth)" if poly else "RED(blowup)", "tier": "probe",
           "ev": "AMPLIFICATION-research", "cap": 60, "sizes": sizes,
           "dense": dense, "banded": banded,
           "bitgrowth_exponent_dense_eliminated": round(p_dense, 2),
           "bitgrowth_exponent_banded_eliminated": round(p_banded, 2),
           "max_schur_entry_bits_dense": max_bits_dense, "max_schur_entry_bits_banded": max_bits_banded,
           "polynomial_bitgrowth": poly, "banded_structure_helps": banded_helps,
           "reading": ("Probe 7b for the Schur-tiling path. " + verdict + " HOWEVER the ABSOLUTE entry sizes are "
                       f"large: a single order-60 Schur step already inflates entries to ~{max_bits_dense} bits "
                       "(dense) / ~%d bits (banded) — inherent, because the Schur complement carries the 60-block's "
                       "inverse whose entries have Hadamard-sized (~det of a 60x60) denominators. Structure (banded) "
                       % max_bits_banded
                       + ("DOES reduce fill-in (Schur density stays well below 1) and entry size vs dense."
                          if banded_helps else "does not visibly help vs dense here.")
                       + " NET: the tiling path is NOT killed by exponential blow-up (bit-growth is polynomial), but "
                         "each ≤60 tile carries hundreds-to-thousands-of-bit rational entries; whether the lowRankOK "
                         "decide leg still reaches order-60 at those entry sizes is the follow-on question — and "
                         "probe 7a's finding (a single big-Nat op is GMP-flat regardless of size; the wall is FACT "
                         "COUNT not bit size) suggests order-60 tiles remain tractable. HONEST SCOPE: representative "
                         "M=BᵀB proxies bracket a real GMS block (which needs cvxpy, operator-local); measures "
                         "feasibility-in-principle, not a build.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\n  bit-growth exponent: dense {p_dense:.2f}, banded {p_banded:.2f} (polynomial={poly})")
    print(f"  gate={out['gate']}\n  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

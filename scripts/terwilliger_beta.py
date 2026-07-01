"""Terwilliger block-diagonalization β generator + independent validation (Phase 0 of the SDP three-point
build; see docs/results/terwilliger-review-synthesis-2026-07-01.md).

AUTHORITATIVE source: Schrijver 2005, "New code upper bounds from the Terwilliger algebra and semidefinite
programming," eq. (7):

    β^t_{i,j,k} = Σ_u (−1)^{u−t} · C(u,t) · C(n−2k, u−k) · C(n−k−u, i−u) · C(n−k−u, j−u)      (all C(a,b)=0 outside 0≤b≤a)

The block-diagonalized Terwilliger algebra (eq. 19) gives, for each k = 0..⌊n/2⌋, TWO PSD block families of
size p_k = n−2k+1 (indices i,j ∈ {k..n−k}):
    R-family :  M_k(x)_{i,j}  = Σ_t β^t_{i,j,k} · x^t_{i,j}
    R'-family:  M'_k(x)_{i,j} = Σ_t β^t_{i,j,k} · (x^0_{i+j−2t,0} − x^t_{i,j})
(The paper deletes the factor C(n−2k,i−k)^{−1/2} C(n−2k,j−k)^{−1/2} to make β integer; PSD is preserved
because that is a positive diagonal congruence. So the *unnormalized* integer β-blocks are PSD iff the
normalized ones are — which is what makes the kernel check exact.)

The panel (terwilliger-review-synthesis) flagged that reviewers' hand-computed β anchors CONFLICT (Kimi used
C(t,u) → β¹₁₁₀=−2; GLM's Krawtchouk value → β¹₁₁₀=n; Gemini's β⁰₂₂₀=36 is a partial sum). So we DO NOT trust
any anchor. The independent oracle is combinatorial: for any real code C, x^t_{i,j} := λ^t_{i,j}/|C| (triple
counts) makes BOTH block families PSD by construction (they are multiplicity-reduced blocks of a sum of Gram
matrices). A single wrong sign/index in β makes some real code's block go non-PSD. We validate against several
codes at n=3..6, and a deliberately-corrupted β must FAIL (proving the test has teeth). Free-CPU, exact
rational arithmetic; no numpy/solver/docker.
"""
from __future__ import annotations

import json
from fractions import Fraction as Fr
from math import comb
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "terwilliger_beta.json"
TSV = _ROOT / "docs" / "results" / "terwilliger_beta_oracle.tsv"


def C(a: int, b: int) -> int:
    """Binomial with the standard zero convention outside 0 ≤ b ≤ a."""
    if b < 0 or a < 0 or b > a:
        return 0
    return comb(a, b)


def beta(n: int, i: int, j: int, k: int, t: int) -> int:
    """Schrijver eq. (7), exact integer. sign via parity so (u−t)<0 stays integer (Python (-1)**neg is float)."""
    total = 0
    for u in range(0, n + 1):
        term = C(u, t) * C(n - 2 * k, u - k) * C(n - k - u, i - u) * C(n - k - u, j - u)
        if term:
            total += term if (u - t) % 2 == 0 else -term
    return total


# ---- block families -------------------------------------------------------------------------------------

def _block_indices(n: int, k: int):
    return list(range(k, n - k + 1))


def r_block(n: int, k: int, x: dict, beta_fn=beta):
    """M_k(x)_{i,j} = Σ_t β^t_{i,j,k} x^t_{i,j}  (R-family). x maps (t,i,j)->Fraction, missing = 0."""
    idx = _block_indices(n, k)
    M = [[Fr(0) for _ in idx] for _ in idx]
    for a, i in enumerate(idx):
        for b, j in enumerate(idx):
            s = Fr(0)
            for t in range(0, n + 1):
                xv = x.get((t, i, j), Fr(0))
                if xv:
                    s += beta_fn(n, i, j, k, t) * xv
            M[a][b] = s
    return M


def rp_block(n: int, k: int, x: dict, x0: dict, beta_fn=beta):
    """M'_k(x)_{i,j} = Σ_t β^t_{i,j,k} (x^0_{i+j−2t,0} − x^t_{i,j})  (R'-family). x0 maps s->x^0_{s,0}."""
    idx = _block_indices(n, k)
    M = [[Fr(0) for _ in idx] for _ in idx]
    for a, i in enumerate(idx):
        for b, j in enumerate(idx):
            s = Fr(0)
            for t in range(0, n + 1):
                bijk = beta_fn(n, i, j, k, t)
                if not bijk:
                    continue
                d = i + j - 2 * t
                x0d = x0.get(d, Fr(0)) if 0 <= d <= n else Fr(0)
                s += bijk * (x0d - x.get((t, i, j), Fr(0)))
            M[a][b] = s
    return M


# ---- exact rational PSD test (no numpy) -----------------------------------------------------------------

def is_psd_exact(M) -> bool:
    """Symmetric rational M is PSD iff LDLᵀ (no pivoting) succeeds treating zero pivots correctly: a zero
    diagonal in the Schur-reduced matrix forces its whole row/col to be zero (else a 2-var vector is negative).
    Both the zero-pivot property and Schur-complement PSD-preservation are standard for PSD matrices."""
    n = len(M)
    A = [[Fr(M[i][j]) for j in range(n)] for i in range(n)]
    for k in range(n):
        if A[k][k] < 0:
            return False
        if A[k][k] == 0:
            # trailing Schur submatrix A[k:][k:] is PSD iff original is; a zero pivot there forces its
            # whole trailing row/col to vanish (else a 2-var vector is negative). Only the trailing part
            # (i > k) matters — columns < k are already eliminated.
            for i in range(k + 1, n):
                if A[i][k] != 0 or A[k][i] != 0:
                    return False
            continue
        piv = A[k][k]
        for i in range(k + 1, n):
            if A[i][k] == 0:
                continue
            f = A[i][k] / piv
            for j in range(k + 1, n):
                A[i][j] -= f * A[k][j]
    return True


# ---- combinatorial oracle: real-code triple counts ------------------------------------------------------

def _multinom(n: int, i: int, j: int, t: int) -> int:
    """C(n; i−t, j−t, t) = n!/((i−t)!(j−t)!t!(n−i−j+2t)!) — the count of triple *shapes*, via eq. (14).
    Returns 0 for an impossible triple (any part < 0)."""
    a, b, c, d = i - t, j - t, t, n - i - j + 2 * t
    if a < 0 or b < 0 or c < 0 or d < 0:
        return 0
    return C(n, a) * C(n - a, b) * C(n - a - b, c)


def code_x(n: int, code):
    """x^t_{i,j} = λ^t_{i,j} / (|C| · C(n; i−t,j−t,t))  and  x^0_{s,0} = λ^0_{s,0}/(|C|·C(n,s)), by brute triple
    counting over C³ (eq. 14: the M^t_{i,j} coefficient carries the multinomial normalization, NOT just 1/|C|;
    this is exactly what makes eq. 21 |C|=Σ C(n,i)x^0_{i,0} hold — full space ⇒ x^0_{i,0}=1). Codes are
    iterables of int bitmasks in [0, 2^n). Returns (x keyed (t,i,j), x0 keyed s)."""
    C_ = list(code)
    m = len(C_)
    assert m > 0
    lam: dict = {}
    lam0: dict = {}
    for X in C_:
        for Y in C_:
            dxy = (X ^ Y).bit_count()
            lam0[dxy] = lam0.get(dxy, 0) + 1          # (X,Y,Z=X): contributes to λ^0_{dxy,0}
            axy = X ^ Y
            for Z in C_:
                dxz = (X ^ Z).bit_count()
                t = (axy & (X ^ Z)).bit_count()
                key = (t, dxy, dxz)
                lam[key] = lam.get(key, 0) + 1
    x = {(t, i, j): Fr(v, m * _multinom(n, i, j, t)) for (t, i, j), v in lam.items() if _multinom(n, i, j, t)}
    x0 = {s: Fr(v, m * C(n, s)) for s, v in lam0.items() if C(n, s)}
    return x, x0


def _even_weight_code(n: int):
    return [v for v in range(1 << n) if v.bit_count() % 2 == 0]


def _test_codes(n: int):
    codes = {
        "singleton": [0],
        "repetition": [0, (1 << n) - 1],
        "even-weight": _even_weight_code(n),
        "full-space": list(range(1 << n)),
    }
    return codes


def validate_code(n: int, code, beta_fn=beta) -> bool:
    """All R and R' blocks PSD for a real code — the necessary condition (19) that any code satisfies."""
    x, x0 = code_x(n, code)
    for k in range(0, n // 2 + 1):
        if not is_psd_exact(r_block(n, k, x, beta_fn)):
            return False
        if not is_psd_exact(rp_block(n, k, x, x0, beta_fn)):
            return False
    return True


# ---- a deliberately-corrupted β (transposed binomial, Kimi's error) — the control -----------------------

def beta_corrupt(n: int, i: int, j: int, k: int, t: int) -> int:
    """C(t,u) instead of C(u,t): the exact transposition that produced Kimi's wrong −2 anchor. Must break PSD."""
    total = 0
    for u in range(0, n + 1):
        term = C(t, u) * C(n - 2 * k, u - k) * C(n - k - u, i - u) * C(n - k - u, j - u)
        if term:
            total += term if (u - t) % 2 == 0 else -term
    return total


# ---- derived spot anchors (computed from eq. 7, not trusted from any review) -----------------------------

def spot_anchors() -> dict:
    return {
        "beta^0_{0,0,0} n=2": beta(2, 0, 0, 0, 0),      # = 1
        "beta^1_{1,1,0} n=2": beta(2, 1, 1, 0, 1),      # = 2  (GLM's =n; Kimi's −2 was C(t,u))
        "beta^1_{1,1,0} n=6": beta(6, 1, 1, 0, 1),      # = 6  (=n)
        "beta^1_{1,1,1} n=4": beta(4, 1, 1, 1, 1),      # = 1  (Gemini anchor, verified)
        "beta^0_{2,2,0} n=4": beta(4, 2, 2, 0, 0),      # = 6  (Gemini said 36 — partial sum, wrong)
    }


def publish_table(nmax: int = 6):
    rows = ["n\tk\tt\ti\tj\tbeta"]
    for n in range(2, nmax + 1):
        for k in range(0, n // 2 + 1):
            idx = _block_indices(n, k)
            for t in range(0, n + 1):
                for i in idx:
                    for j in idx:
                        b = beta(n, i, j, k, t)
                        if b:
                            rows.append(f"{n}\t{k}\t{t}\t{i}\t{j}\t{b}")
    TSV.parent.mkdir(parents=True, exist_ok=True)
    TSV.write_text("\n".join(rows) + "\n")
    return len(rows) - 1


def main() -> int:
    results = {"anchors": spot_anchors(), "codes": {}, "control": {}}
    all_ok = True
    for n in range(3, 7):
        results["codes"][n] = {}
        for name, code in _test_codes(n).items():
            ok = validate_code(n, code)
            results["codes"][n][name] = ok
            all_ok = all_ok and ok

    # Control: the corrupted β MUST make at least one real-code block non-PSD.
    broke = False
    for n in range(3, 7):
        if not validate_code(n, _even_weight_code(n), beta_fn=beta_corrupt):
            broke = True
            break
    results["control"]["corrupt_beta_breaks_psd"] = broke

    n_entries = publish_table(6)
    verdict = "GREEN" if all_ok and broke else "RED"
    results["verdict"] = verdict
    results["oracle_entries"] = n_entries
    results["reading"] = (
        "GREEN = every real code's Terwilliger β-blocks (both families, all k) are exactly PSD AND the "
        "transposed-binomial corruption breaks PSD -> eq.(7) is transcribed correctly and the differential "
        "test has teeth. This validates the β generator that the SDP three-point producer will use; the "
        "block-by-block PSD check matches the kernel dimension-wall escape. RED = a sign/index bug in β."
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2) + "\n")

    print(f"terwilliger β generator: {verdict}")
    print(f"  anchors (from eq.7): {results['anchors']}")
    for n in range(3, 7):
        print(f"  n={n}: " + ", ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in results["codes"][n].items()))
    print(f"  control (corrupt β breaks PSD): {broke}")
    print(f"  published oracle: {n_entries} nonzero β entries -> {TSV}")
    print(f"  -> {OUT}")
    return 0 if verdict == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())

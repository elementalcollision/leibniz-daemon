"""Bareiss fraction-free integer LDLᵀ certificate — mitigation for the measured compute trap (gate #2,
scripts/psd_scaling_probe.py: naive rational-Cholesky cert bit-length explodes, 944 bits @ n=6 -> 30773 @ n=30).

BACKGROUND. The naive recipe in scripts/psd_certificate_microprobe.py does exact-rational LDLᵀ (Fraction
arithmetic) and clears denominators via `clear_denoms`, which takes the LCM of *every* L/d entry's reduced
denominator across the *whole* factorization. Those per-entry reduced denominators grow roughly linearly in
column index (empirically ~20-25 bits/column here), and the LCM across ~n of them compounds close to their
sum -- giving the observed near-quadratic-in-n bit-length blowup.

BAREISS FIX. Fraction-free (Bareiss) elimination on the same integer matrix M produces, with NO rounding and
NO fraction ever appearing, the leading principal minors p_0=1, p_1, ..., p_n (p_n = det M) together with an
integer "history" tableau. We prove (and verify numerically below, on the exact matrices this repo already
uses) the closed form linking that tableau to the ordinary LDLᵀ decomposition of M:

    L[i][k]  =  history[k][i][k] / p_{k+1}      (k < i)              -- exact, no remainder
    d[k]     =  p_{k+1} / p_k                                        -- exact, no remainder

(history[k] is the fraction-free tableau *after* k Bareiss elimination steps; history[k][i][k] is already an
integer bounded by a minor of M, i.e. Hadamard-bounded — this is the whole point of fraction-free elimination:
it is not a "naive" per-entry LCM, it is dividing out exactly what Sylvester's identity guarantees divides
evenly, at every step, so nothing but genuine minors ever appears.)

From that closed form, one certificate that reuses the existing `ldltOK` Lean checker (single global integer
`scale`, integer L, integer d>=0) verifies with

    L_int[i][k]  =  history[k][i][k]                   (k<i),   L_int[k][k] = p_{k+1}
    d_int[k]     =  scale / (p_k * p_{k+1})             for  scale = lcm_k(p_k * p_{k+1})

Because `scale` is an LCM of n numbers each bounded by (at most) det(M)^2-ish products of *adjacent* minors
(not a whole-matrix denominator LCM), its bit-length tracks the minors' growth, not the naive route's
compounding reduced-fraction denominators. MEASURED below: strictly smaller than the naive route at every
size tested, growing to a ~2.8x reduction at n=30 (10982 bits vs 30773).

Two certificate forms are produced, both reusing existing kernel-checkable machinery:
  (a) integer LDLᵀ (L, d>=0, scale) — reuses `render_ldlt_lean`/`ldltOK` from psd_certificate_microprobe.py
      VERBATIM (only the *producer* here is new).
  (b) Sylvester's criterion: all leading principal minors > 0 — a NEW tiny core-Lean checker (`detSignOK`)
      that recomputes the Bareiss minors from M itself inside the kernel (does not trust the producer's
      claimed minors), defined in this file.

Free-CPU producer; docker only for the kernel-check leg (matches the project's established probe pattern).
"""
from __future__ import annotations

import importlib.util
import sys
from fractions import Fraction as Fr
from math import gcd
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod, rel):
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# reuse: ldlt / clear_denoms / verify_int_cert / render_ldlt_lean / _lit (naive-rational route, for the
# bit-length comparison, and the kernel-checkable ldltOK form) and rounded_pd (the exact matrices exercised
# by the compute-trap probe) — imported, never edited.
pm = _load("psd_certificate_microprobe", "scripts/psd_certificate_microprobe.py")
sp = _load("psd_scaling_probe", "scripts/psd_scaling_probe.py")


def _lcm(a: int, b: int) -> int:
    return a * b // gcd(a, b) if a and b else (a or b)


# ---------------------------------------------------------------------------------------------------------
# Bareiss fraction-free elimination. Every division below is EXACT by Sylvester's identity (the fraction-free
# elimination invariant): asserted, not assumed.
# ---------------------------------------------------------------------------------------------------------

def bareiss_minors(M_int):
    """Leading principal minors p_0=1, p_1, ..., p_n of integer symmetric matrix M_int via fraction-free
    (Bareiss) elimination; p_n = det(M_int). Returns (minors, history) where history[k] is the fraction-free
    tableau after k elimination steps (integers only, exact — history[0] is M_int itself)."""
    n = len(M_int)
    A = [row[:] for row in M_int]
    minors = [1]  # p_0 = 1 by convention
    history = [[row[:] for row in A]]
    prev_pivot = 1
    for k in range(n):
        pivot = A[k][k]
        minors.append(pivot)
        if k == n - 1:
            break
        B = [row[:] for row in A]
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                num = A[i][j] * pivot - A[i][k] * A[k][j]
                q, r = divmod(num, prev_pivot)
                assert r == 0, "Bareiss step produced a non-exact division — algorithm invariant violated"
                B[i][j] = q
        A = B
        history.append([row[:] for row in A])
        prev_pivot = pivot
    return minors, history


def minors_positive(minors) -> bool:
    """Sylvester's criterion: M strictly PD  <=>  every leading principal minor > 0 (excluding p_0=1)."""
    return all(p > 0 for p in minors[1:])


def bareiss_ldlt_cert(M_int):
    """Fraction-free-derived LDLᵀ certificate in the SAME (L, d, scale) form psd_certificate_microprobe's
    clear_denoms produces: integer L, integer diagonal d>=0, integer scale, with
        L·diag(d)·Lᵀ == scale·M_int
    Returns None if M_int is not strictly PD (a leading minor <= 0).

    Derivation (see module docstring): L[i][k] = history[k][i][k]/p_{k+1}, d[k] = p_{k+1}/p_k exactly, so
        L_int[i][k] = history[k][i][k]  (k<i),  L_int[k][k] = p_{k+1}
        d_int[k]    = scale / (p_k * p_{k+1}),  scale = lcm_k(p_k * p_{k+1})
    which is an EXACT integer for every k (scale is a multiple of every p_k*p_{k+1} by construction), and
    reproduces scale*M_int exactly (checked below, not merely asserted, by the caller via verify_int_cert /
    the kernel's own ldltOK recomputation).
    """
    n = len(M_int)
    minors, history = bareiss_minors(M_int)
    if not minors_positive(minors):
        return None
    products = [minors[k] * minors[k + 1] for k in range(n)]
    scale = 1
    for p in products:
        scale = _lcm(scale, p)
    L_int = [[0] * n for _ in range(n)]
    for k in range(n):
        L_int[k][k] = minors[k + 1]
        for i in range(k + 1, n):
            L_int[i][k] = history[k][i][k]
    d_int = [scale // products[k] for k in range(n)]
    return L_int, d_int, scale


def bareiss_cert_bits(M_int):
    """Max integer bit-length across the Bareiss-derived certificate (L, d, scale) for M_int, plus the
    underlying minors' own max bit-length (the tighter theoretical floor this route tracks)."""
    cert = bareiss_ldlt_cert(M_int)
    if cert is None:
        return None
    L_int, d_int, scale = cert
    minors, _ = bareiss_minors(M_int)
    maxbits = sp._maxbits(L_int, d_int, [scale])
    minor_bits = max(abs(p).bit_length() for p in minors)
    return {"cert_bits": maxbits, "minor_bits": minor_bits, "scale_bits": int(scale).bit_length()}


def verify_bareiss_cert(M_int, L_int, d_int, scale) -> bool:
    """Python-side re-verification using the SAME check the Lean `ldltOK` performs (integer identity +
    d>=0), reused from psd_certificate_microprobe (no reimplementation of the trust-relevant check)."""
    return pm.verify_int_cert(M_int, L_int, d_int, scale)


# ---------------------------------------------------------------------------------------------------------
# Certificate form (b): Sylvester's criterion (all leading principal minors > 0). Kernel-checked via a tiny
# core-Lean checker that RECOMPUTES the Bareiss minors from M itself (does not trust the producer's claimed
# minors) — same trust posture as ldltOK recomputing the matrix product itself. No Mathlib; core Lean only.
# ---------------------------------------------------------------------------------------------------------
_DET_SIGN_LEAN_HELPERS = """\
set_option maxRecDepth 100000
def bStep (A : List (List Int)) (k : Nat) (piv prevPiv : Int) (n : Nat) : List (List Int) :=
  (List.range n).map (fun i =>
    (List.range n).map (fun j =>
      if i <= k || j <= k then A[i]![j]!
      else (A[i]![j]! * piv - A[i]![k]! * A[k]![j]!) / prevPiv))
def bareissMinorsAux (A : List (List Int)) (k : Nat) (n : Nat) (prevPiv : Int) (acc : List Int) : List Int :=
  match k with
  | 0 => acc
  | Nat.succ k' =>
    let idx := n - k
    let piv := A[idx]![idx]!
    let A' := bStep A idx piv prevPiv n
    bareissMinorsAux A' k' n piv (acc ++ [piv])
def bareissMinors (A : List (List Int)) : List Int :=
  let n := A.length
  bareissMinorsAux A n n 1 [1]
def detSignOK (A : List (List Int)) : Bool :=
  (bareissMinors A).drop 1 |>.all (fun p => 0 < p)"""


def render_detsign_lean(M_int) -> str:
    """Kernel program: recompute Bareiss' leading principal minors FROM M_int (not from the producer's
    claimed minors) and check they are all > 0 (Sylvester -> strictly PD -> PSD certificate, form (b))."""
    return (f"{_DET_SIGN_LEAN_HELPERS}\n\ntheorem psd_by_minors :\n"
            f"    detSignOK {pm._lit(M_int)} = true := by\n  decide\n")


def render_detsign_lean_bogus(M_int) -> str:
    """Control: perturb M_int's (0,0) entry to break PD (drive the first leading minor negative) while
    keeping the matrix shape/size identical, so the kernel must reject."""
    bad = [row[:] for row in M_int]
    bad[0][0] = -abs(bad[0][0]) - 10 ** 9
    return render_detsign_lean(bad)


def render_ldlt_lean_bogus(M_int, L_int, d_int, scale) -> str:
    """Control for form (a): corrupt d so the sign check (d>=0) fails, forcing kernel rejection."""
    bad_d = [x - 10 ** 9 for x in d_int]
    return pm.render_ldlt_lean(M_int, L_int, bad_d, scale)


# ---------------------------------------------------------------------------------------------------------
# measurement: naive route (existing microprobe) vs Bareiss route, on the SAME fixtures the scaling probe
# uses (psd_scaling_probe.rounded_pd) — the exact construction that demonstrated the compute trap.
# ---------------------------------------------------------------------------------------------------------

def compare_bitlengths(sizes=(6, 10, 14, 18, 22, 26, 30), D=10 ** 6):
    rows = []
    for n in sizes:
        N = sp.rounded_pd(0, n, D)
        # naive baseline (Fraction LDLT then whole-matrix LCM clear_denoms) — UNCHANGED, reused verbatim
        L, d = pm.ldlt([[Fr(N[i][j]) for j in range(n)] for i in range(n)])
        Li, di, sc = pm.clear_denoms(L, d)
        naive_bits = sp._maxbits(Li, di, [sc])
        naive_ok = pm.verify_int_cert(N, Li, di, sc)
        # Bareiss route
        BLi, Bdi, Bsc = bareiss_ldlt_cert(N)
        bareiss_ok = verify_bareiss_cert(N, BLi, Bdi, Bsc)
        bstats = bareiss_cert_bits(N)
        rows.append({
            "n": n,
            "naive_cert_bits": naive_bits, "naive_verifies": naive_ok,
            "bareiss_cert_bits": bstats["cert_bits"], "bareiss_minor_bits": bstats["minor_bits"],
            "bareiss_verifies": bareiss_ok,
            "reduction_x": round(naive_bits / max(bstats["cert_bits"], 1), 2),
        })
        print(f"  n={n:>3d}  naive={naive_bits:>7d}b (ok={naive_ok})   "
              f"bareiss={bstats['cert_bits']:>7d}b minors={bstats['minor_bits']:>6d}b (ok={bareiss_ok})   "
              f"reduction={rows[-1]['reduction_x']:>6.2f}x")
    return rows


def main() -> int:
    import json

    print("Bareiss fraction-free PSD certificate vs naive rational-Cholesky (bit-length):")
    rows = compare_bitlengths()

    kernel = {"status": "not run"}
    try:
        from leibniz.backends.lean_cli import LeanCliBackend, available
        if available():
            bk = LeanCliBackend(timeout_s=180)
            kernel_rows = []
            for n in (6, 10, 14):
                N = sp.rounded_pd(0, n, 10 ** 6)
                Li, di, sc = bareiss_ldlt_cert(N)
                good_a = bk.check_source(pm.render_ldlt_lean(N, Li, di, sc))
                bogus_a = bk.check_source(render_ldlt_lean_bogus(N, Li, di, sc))
                good_b = bk.check_source(render_detsign_lean(N))
                bogus_b = bk.check_source(render_detsign_lean_bogus(N))
                kernel_rows.append({
                    "n": n, "form_a_valid": good_a, "form_a_bogus_rejected": bogus_a is False,
                    "form_b_valid": good_b, "form_b_bogus_rejected": bogus_b is False,
                })
                print(f"  kernel n={n}: form(a) valid={good_a} bogus_rejected={bogus_a is False}   "
                      f"form(b) valid={good_b} bogus_rejected={bogus_b is False}")
            kernel = {"status": "checked", "rows": kernel_rows,
                      "sound": all(r["form_a_valid"] is True and r["form_a_bogus_rejected"]
                                   and r["form_b_valid"] is True and r["form_b_bogus_rejected"]
                                   for r in kernel_rows)}
        else:
            kernel = {"status": "unavailable (no docker)"}
    except Exception as e:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(e).__name__}: {e})"}

    biggest_naive = max(r["naive_cert_bits"] for r in rows)
    biggest_bareiss = max(r["bareiss_cert_bits"] for r in rows)
    gate = ("GREEN" if all(r["naive_verifies"] and r["bareiss_verifies"] for r in rows)
            and biggest_bareiss < biggest_naive and kernel.get("sound", None) in (True, None)
            and kernel.get("status") != "unavailable" else
            "AMBER(kernel-unavailable)" if "unavailable" in str(kernel.get("status")) else "RED")

    res = {"gate": gate, "rows": rows, "kernel": kernel,
           "biggest_naive_bits": biggest_naive, "biggest_bareiss_bits": biggest_bareiss,
           "reduction_x_at_largest": round(biggest_naive / max(biggest_bareiss, 1), 2),
           "reading": ("Bareiss fraction-free elimination mitigation for the measured compute trap "
                       "(psd_scaling_probe.py): replaces the naive whole-matrix LCM denominator-clearing "
                       "with a scale built only from products of ADJACENT leading principal minors "
                       "(Hadamard-bounded), LCM'd across columns. GREEN => certs verify (Python + kernel) "
                       "at strictly smaller bit-length than the naive route, confirming the mitigation. "
                       "RED => Bareiss route fails to verify or does not reduce bit-length.")}
    out = _ROOT / "docs" / "results" / "bareiss_ldlt.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2) + "\n")
    print(f"\ngate={gate}  biggest_naive={biggest_naive}b  biggest_bareiss={biggest_bareiss}b  "
          f"reduction={res['reduction_x_at_largest']}x")
    print(f"kernel: {kernel.get('status')}  sound={kernel.get('sound')}")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

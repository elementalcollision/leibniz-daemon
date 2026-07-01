"""$0 exact-PSD certificate micro-probe (gate for the SDP three-point bet).

The SDP scoping flagged the make-or-break as the leg UNIQUE to our trust boundary: can a float PSD solution
be rounded to an EXACT rational PSD certificate the Lean kernel checks cheaply? That is independent of the
specific SDP, so this probe isolates it (no SDP solver needed — none is installed).

Kernel-checkable PSD certificate (integer, core Lean, no Mathlib — mirrors the covering/Delsarte checkers):
the producer supplies an integer lower-triangular L, an integer diagonal d, and a positive integer `scale`
with

    L · diag(d) · Lᵀ  ==  scale · M      and    d_i >= 0  for all i

Then M = (1/scale)·L·diag(d)·Lᵀ ⪰ 0 (a congruence of a nonneg diagonal). The kernel verifies an integer
matrix identity + a sign check — polynomial, decidable, no eigenvalues, no decide-wall.

Probe:
1. rational LDLᵀ of an exact rational PD matrix -> clear denominators -> integer (L,d,scale); verify the
   integer identity + d>=0 exactly, and KERNEL-verify it (plus a bogus control the kernel rejects);
2. rounding recipe under simulated solver-float noise: floatify an exact PD matrix, round back to rationals
   + a diagonal shift, and check an exact PSD certificate still recovers (the flagged fragility).

GREEN: exact-PSD certs kernel-verify AND the rounding recipe recovers a valid cert from noisy float across
the sample. RED: the exact-PSD kernel-check or the rounding fails. (Residual, out of scope here: solving the
actual Terwilliger SDP needs an SDP solver dep — SCS/cvxpy, operator-local — a noted prereq for the build.)

Free-CPU (numpy for float simulation only; fractions for exact); docker for the kernel leg.
"""
from __future__ import annotations

import json
from fractions import Fraction as Fr
from math import gcd
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "psd_certificate_microprobe.json"


def _lcm(a, b):
    return a * b // gcd(a, b) if a and b else (a or b)


def ldlt(M):
    """Rational LDLᵀ of a symmetric PD matrix M (list of list of Fraction). Returns (L unit-lower-tri, d)."""
    n = len(M)
    L = [[Fr(0)] * n for _ in range(n)]
    d = [Fr(0)] * n
    for j in range(n):
        d[j] = M[j][j] - sum(L[j][k] * L[j][k] * d[k] for k in range(j))
        L[j][j] = Fr(1)
        if d[j] == 0:
            return None  # not PD (zero pivot); the probe uses strictly-PD matrices
        for i in range(j + 1, n):
            L[i][j] = (M[i][j] - sum(L[i][k] * L[j][k] * d[k] for k in range(j))) / d[j]
    return L, d


def clear_denoms(L, d):
    """Integer certificate (L_int, d_int, scale) with L_int·diag(d_int)·L_intᵀ == scale·M, d_int>=0."""
    a = 1
    for row in L:
        for x in row:
            a = _lcm(a, x.denominator)
    b = 1
    for x in d:
        b = _lcm(b, x.denominator)
    L_int = [[int(x * a) for x in row] for row in L]
    d_int = [int(x * b) for x in d]
    scale = a * a * b
    return L_int, d_int, scale


def _matI(A, B):
    n, m, p = len(A), len(B), len(B[0])
    return [[sum(A[i][k] * B[k][j] for k in range(m)) for j in range(p)] for i in range(n)]


def _T(A):
    return [[A[j][i] for j in range(len(A))] for i in range(len(A[0]))]


def verify_int_cert(M_int, L_int, d_int, scale) -> bool:
    """Exact: L·diag(d)·Lᵀ == scale·M and d>=0 (M_int is the exact rational M scaled to integers by mden)."""
    if any(x < 0 for x in d_int):
        return False
    n = len(d_int)
    Dm = [[d_int[i] if i == j else 0 for j in range(n)] for i in range(n)]
    lhs = _matI(_matI(L_int, Dm), _T(L_int))
    rhs = [[scale * M_int[i][j] for j in range(n)] for i in range(n)]
    return lhs == rhs


# ---- core-Lean kernel checker (integer matrices) ------------------------------------------------------
_LEAN_HELPERS = """\
set_option maxRecDepth 10000
def dot (u v : List Int) : Int := ((u.zip v).map (fun p => p.1 * p.2)).foldl (· + ·) 0
def col (A : List (List Int)) (j : Nat) : List Int := A.map (fun r => r[j]!)
def matmul (A B : List (List Int)) : List (List Int) :=
  A.map (fun r => (List.range (B[0]!.length)).map (fun j => dot r (col B j)))
def transpose (A : List (List Int)) : List (List Int) :=
  (List.range (A[0]!.length)).map (fun j => col A j)
def diag (d : List Int) : List (List Int) :=
  (List.range d.length).map (fun i => (List.range d.length).map (fun j => if i == j then d[i]! else 0))
def scaleM (s : Int) (M : List (List Int)) : List (List Int) := M.map (fun r => r.map (fun x => s * x))
def ldltOK (M L : List (List Int)) (d : List Int) (s : Int) : Bool :=
  d.all (fun x => 0 <= x) && (matmul (matmul L (diag d)) (transpose L) == scaleM s M)"""


def _lit(M):
    return "[" + ", ".join("[" + ", ".join(str(x) for x in row) + "]" for row in M) + "]"


def render_ldlt_lean(M_int, L_int, d_int, scale) -> str:
    dl = "[" + ", ".join(str(x) for x in d_int) + "]"
    return (f"{_LEAN_HELPERS}\n\ntheorem psd_cert :\n"
            f"    ldltOK {_lit(M_int)} {_lit(L_int)} {dl} ({scale}) = true := by\n  decide\n")


def _exact_pd(seed: int, n: int):
    """Exact rational PD matrix M = AᵀA + n·I (A small-integer, +nI => strictly PD). Pure Python (no numpy).
    Returns (M as Fractions, M_int integer)."""
    import random
    rng = random.Random(seed)
    A = [[rng.randint(-3, 3) for _ in range(n)] for _ in range(n)]
    M_int = [[sum(A[k][i] * A[k][j] for k in range(n)) + (n if i == j else 0) for j in range(n)]
             for i in range(n)]
    return [[Fr(M_int[i][j]) for j in range(n)] for i in range(n)], M_int


def _rounding_recovers(seed: int, n: int) -> bool:
    """Simulate a solver float PSD matrix: floatify an exact PD M + symmetric Gaussian noise, round back to
    integers + a diagonal shift to restore exact PD, and check an exact integer certificate recovers. Pure
    Python (no numpy)."""
    import random
    _M, M_int = _exact_pd(seed, n)
    rng = random.Random(seed + 1)
    noise = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            noise[i][j] = noise[j][i] = rng.gauss(0, 0.25)
    Mr = [[round(M_int[i][j] + noise[i][j]) for j in range(n)] for i in range(n)]
    for i in range(n):                       # enforce integer symmetry after rounding
        for j in range(i + 1, n):
            Mr[j][i] = Mr[i][j]
    for shift in (0, 1, 2, 4, 8, 16, 32):
        Ms = [[Mr[i][j] + (shift if i == j else 0) for j in range(n)] for i in range(n)]
        res = ldlt([[Fr(Ms[i][j]) for j in range(n)] for i in range(n)])
        if res is None:
            continue
        L, d = res
        Li, di, sc = clear_denoms(L, d)
        if verify_int_cert(Ms, Li, di, sc):
            return True
    return False


def main() -> int:
    sizes = [3, 4, 5]
    # 1) exact PSD certs verify (Python + kernel) on constructed PD matrices
    exact_ok, rows = 0, []
    kernel = {"status": "not run"}
    for s, n in enumerate(sizes):
        M, M_int = _exact_pd(s, n)
        L, d = ldlt(M)
        Li, di, sc = clear_denoms(L, d)
        ok = verify_int_cert(M_int, Li, di, sc)
        exact_ok += int(ok)
        rows.append({"n": n, "exact_cert_verifies": ok, "scale": sc})
    # kernel-check the first cell + a bogus control
    try:
        from leibniz.backends.lean_cli import LeanCliBackend, available
        if available():
            M, M_int = _exact_pd(0, 3)
            L, d = ldlt(M)
            Li, di, sc = clear_denoms(L, d)
            bk = LeanCliBackend(timeout_s=120)
            good = bk.check_source(render_ldlt_lean(M_int, Li, di, sc))
            bogus = bk.check_source(render_ldlt_lean(M_int, Li, [x - 10**6 for x in di], sc))  # d not >=0 / wrong
            kernel = {"status": "checked", "valid_cert": good, "bogus_cert": bogus,
                      "sound": good is True and bogus is False}
        else:
            kernel = {"status": "unavailable (no docker)"}
    except Exception as e:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(e).__name__})"}
    # 2) rounding recipe under simulated float noise
    trials = [(seed, n) for n in sizes for seed in range(6)]
    recovered = sum(_rounding_recovers(seed, n) for (seed, n) in trials)
    rounding = {"trials": len(trials), "recovered": recovered, "rate": round(recovered / len(trials), 3)}

    gate = ("GREEN" if exact_ok == len(sizes) and kernel.get("sound", None) in (True, None)
            and rounding["recovered"] == rounding["trials"]
            and kernel.get("status") != "unavailable" else
            "AMBER(kernel-unavailable)" if "unavailable" in str(kernel.get("status"))
            else "RED")
    res = {"gate": gate, "exact_certs_verified": f"{exact_ok}/{len(sizes)}", "kernel": kernel,
           "rounding": rounding, "rows": rows,
           "reading": ("Isolates the trust-boundary-unique make-or-break for the SDP bet: exact-PSD "
                       "kernel-checkable certificates (integer LDLᵀ) + rounding a noisy float PSD to an "
                       "exact PSD cert. GREEN => both legs feasible; the residual build is (a) an SDP solver "
                       "dep (SCS/cvxpy) and (b) the Terwilliger three-point formulation. RED => exact-PSD "
                       "rounding/kernel-check infeasible; bank LP as the final word.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"exact-PSD certificate micro-probe: {res['gate']}")
    print(f"  exact certs verified: {res['exact_certs_verified']}")
    print(f"  kernel: {kernel}")
    print(f"  rounding recovery: {rounding['recovered']}/{rounding['trials']} (rate {rounding['rate']})")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

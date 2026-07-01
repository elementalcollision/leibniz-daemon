"""Code-SDP -> dual-cert -> kernel pipeline pre-validation (Sonnet 5 build, post-#212/#214 gates).

#212 (exact-PSD micro-probe) and #214 (irrationality-margin test) validated the two make-or-break legs of
the Schrijver/Terwilliger SDP bet on SYNTHETIC matrices / a proxy graph family (Lovász theta of odd cycles).
This script runs the SAME chain — untrusted SDP solver -> rational rounding -> exact integer PSD certificate
-> Lean KERNEL check -> Delsarte-style bound -- on REAL binary-code confusability graphs, to pre-validate the
code-specific leg before any Terwilliger three-point build.

Formulation (Lovász theta upper-bounds the independence number of the confusability graph, which IS A(n,d)):
  Confusability graph G(n,d): vertices = {0,1}^n, edge {u,v} iff Hamming distance(u,v) < d.
  A(n,d) = max independent set of G(n,d) <= theta(G(n,d))  [Lovász sandwich theorem].
  Dual SDP (same shape as scripts/irrationality_margin_test.py's solve_theta_dual/min_rational_t, reused
  in spirit but re-derived here for the code graph):
      minimize t   s.t.   Z := t*I - J + sum_{(i,j) in E} y_ij * E_ij  >= 0 (PSD)
  Any FEASIBLE (t, y) gives theta(G) <= t (weak duality on the theta SDP), hence A(n,d) <= floor(t).
  The solver (SCS/CLARABEL) is UNTRUSTED; it only proposes (t, y). Soundness rests entirely on:
    1. rounding y to exact rationals,
    2. finding an exact rational t on a 1/P grid with Z(t) certified PSD via integer LDLT (Strict-PD, no
       pivoting -- reusing scripts/psd_certificate_microprobe.ldlt / clear_denoms / verify_int_cert),
    3. KERNEL-checking the integer LDLT identity (scripts/psd_certificate_microprobe.render_ldlt_lean) with
       the real Lean 4.31 kernel via Docker.

This is audit-tier: nothing here sets kernel_verified or promulgates. It is a standalone measurement script
that reuses the PROTECTED psd_certificate_microprobe module by import (never edits it).

EXPECTED (stated up front, not a discovery claim): for these tiny cells the SDP bound should equal the
existing Delsarte LP bound (no improvement) -- Lovász theta and the LP bound coincide on highly symmetric
small Hamming-scheme graphs. The point of this script is validating the CHAIN (code SDP -> dual -> rational
cert -> kernel), not beating a bound.

MEASURED cell selection (prototyped before committing to the final cell list): theta(G(n,d)) is tight
(floor(theta) == known A(n,d)) for A(4,2)=8, A(4,4)=2, A(5,2)=16 -- all three kernel-verified below. It is
also tight for A(6,3)=8, A(7,3)=16, A(8,4)=16, but a SEPARATE, more severe wall (see below) rules those out
as the cells to KERNEL-check. It is NOT tight for A(5,3), A(6,4), or A(8,5) (theta floors to 5, 5, 6
respectively vs known 4, 4, 4) -- Lovász theta is a valid but sometimes strictly WEAKER sandwich bound than
the Delsarte LP bound on these graphs; that is expected coding-theory behavior, not a bug.

MEASURED wall: the naive core-Lean PSD checker (psd_certificate_microprobe's `matmul`/`col`, O(N) List
indexing per lookup => effectively O(N^4) kernel-reduction work for an NxN matmul via `decide`) does NOT
scale to the FULL confusability graph at n>=6 (N=2^n>=64 vertices). Measured directly: an n=6 cert
(N=64, 4027 cert bits) TIMED OUT even at unlimited maxHeartbeats within a 590s process budget; a synthetic
N=32 matrix succeeds in ~20s at maxHeartbeats=0 but N=64 does not complete in 10 minutes. This is a
DIFFERENT, more fundamental bottleneck than the previously-measured bit-length compute trap
(psd_scaling_probe.py) -- it is matrix DIMENSION N (kernel reduction steps), not bit-length, that walls out
first for confusability-graph-sized matrices. Practical ceiling measured here: N<=32 kernel-checks reliably
in <30s with `set_option maxHeartbeats 0` prepended to the rendered source (done in main()/kern() below,
NOT by editing the protected render_ldlt_lean, which has no heartbeat-tuning of its own and is invoked with
Lean's low DEFAULT heartbeat budget by scripts that only ever fed it n<=5 matrices before). Because of this,
cells are capped at n<=5 (N<=32 vertices) here, NOT n<=8/N<=256 as the full task scope allows for the SDP
SOLVE -- the SDP solve itself is fast up to n=8 (see solve_theta_dual/confusability_graph), but the
KERNEL-CHECK leg is the one that does not reach n=8 with this checker. Reported honestly, not silently.

Needs cvxpy (operator-local, like ortools/z3) + docker (leibniz-lean:v4.31.0) for the kernel leg. Free-CPU
solve for n<=8 (<=256 vertices; dual SDP has one variable per graph edge + t -- NOT one per non-edge, which
is what makes even n=8's SDP SOLVE tractable; the primal Lovász-theta SDP with a 256x256 PSD variable and
one equality constraint per NON-edge is intractable at this size for a generic SDP solver and was rejected
during prototyping in favor of this dual formulation). The KERNEL-CHECK leg is capped at n<=5 (measured wall
above), independent of the solver leg's reach.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
from fractions import Fraction as Fr
from math import ceil, floor
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "sdp_code_bound.json"


def _load(mod, rel):
    import sys
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


pm = _load("psd_certificate_microprobe", "scripts/psd_certificate_microprobe.py")
dl = _load("delsarte_lp_probe", "scripts/delsarte_lp_probe.py")
# Reuse the rock-solid A(n,d) table the Delsarte LP probe cross-checks against, extended with a few more
# standard tiny cells (n<=5) needed here because the kernel-check leg's measured dimension wall (see module
# docstring) caps usable cells at N=2^n<=32. Each addition below is cross-checked against dl.solve_dual_lp's
# OWN exact-integer-certified Delsarte bound (never just asserted): A(4,2): p=[2,1,0,0],q=2 -> bound 8;
# A(4,4): p=[1,0,0,0],q=4 -> bound 2; A(5,2): p=[4,3,2,1,0],q=5 -> bound 16 (all reproduced live in
# tests/test_sdp_code_bound.py::test_known_extension_matches_delsarte_lp_cert).
KNOWN = dict(dl.KNOWN)
KNOWN.update({(4, 2): 8, (4, 4): 2, (5, 2): 16})


# ---- confusability graph -------------------------------------------------------------------------------

def confusability_graph(n: int, d: int):
    """Vertices = all n-bit strings; edge {i,j} iff Hamming distance < d (so an independent set is a code
    with min distance >= d). Returns (N vertex count, list of edges as (i,j) index pairs)."""
    verts = list(itertools.product((0, 1), repeat=n))
    N = len(verts)
    edges = []
    for i in range(N):
        vi = verts[i]
        for j in range(i + 1, N):
            hd = sum(a != b for a, b in zip(vi, verts[j]))
            if hd < d:
                edges.append((i, j))
    return N, edges


# ---- untrusted solver: dual Lovász-theta SDP on the confusability graph --------------------------------

def solve_theta_dual(N: int, edges: list[tuple[int, int]]):
    """Untrusted: minimize t s.t. Z = t*I - J + sum y_ij*E_ij >= 0. Returns (t float, y float list) or None
    if the solver fails. theta(G) <= t at any feasible point (weak duality), so A(n,d) <= floor(t)."""
    import cvxpy as cp
    import numpy as np
    from scipy import sparse
    J = np.ones((N, N))
    t = cp.Variable()
    y = cp.Variable(len(edges))
    # Vectorized off-diagonal accumulation (sum y_ij*E_ij) via a sparse "edge -> matrix-entry" operator, so
    # cvxpy builds ONE affine expression instead of accumulating len(edges) dense NxN Ek terms (the naive
    # per-edge Python loop over dense zero matrices was the measured bottleneck at n=8, ~250-450s wall time
    # with "too many subexpressions" warnings; this reshape-based construction is O(edges) sparse, not
    # O(edges * N^2) dense, and lets SCS's own vectorized canonicalization do the rest).
    rows_idx, data_rows = [], []
    for k, (i, j) in enumerate(edges):
        rows_idx += [i * N + j, j * N + i]
        data_rows += [k, k]
    scatter = sparse.coo_matrix((np.ones(len(rows_idx)), (rows_idx, data_rows)),
                                 shape=(N * N, len(edges)))
    Yflat = scatter @ y                      # cvxpy affine expression, shape (N*N,)
    Yoff = cp.reshape(Yflat, (N, N), order="C")
    Z = t * np.eye(N) - J + Yoff
    prob = cp.Problem(cp.Minimize(t), [Z >> 0])
    prob.solve(solver=cp.SCS, eps=1e-7)
    if t.value is None:
        return None
    return float(t.value), [float(v) for v in y.value]


def _W_rational(N, edges, y_rat):
    """W = -J + sum y'_ij E_ij as an exact rational matrix (mirrors irrationality_margin_test._W_rational)."""
    W = [[Fr(-1) for _ in range(N)] for _ in range(N)]
    for k, (i, j) in enumerate(edges):
        W[i][j] += y_rat[k]
        W[j][i] += y_rat[k]
    return W


def _gcd(a, b):
    while b:
        a, b = b, a % b
    return a


_MAX_CERT_BITS = 6000  # secondary safety net (bit-length), well below Python's ~14300-bit int-str conversion
# limit -- guards against the bit-length compute trap psd_scaling_probe.py measured. NOT the binding
# constraint for the cells used here (the binding constraint, measured directly above in this file's
# docstring, is kernel matrix DIMENSION N, which is capped independently via the n<=5 cell choice).
# min_rational_cert reports None rather than let bit growth run into the Python int-str limit uncontrolled
# (which previously raised a raw ValueError deep inside render_ldlt_lean before this guard was added).


def min_rational_cert(N, edges, y_rat, P, max_bits=_MAX_CERT_BITS):
    """Smallest rational t on a 1/P grid with Z(t) = t*I + W exactly PSD, via Strict-PD (+ margin) rational
    LDLT (NO pivoting -- the #212/#214 mechanism). Returns (t Fraction, Z integer numerator matrix,
    (L_int, d_int, scale)) or None (also None if the certificate's bit-length exceeds max_bits -- the
    measured compute trap -- so callers never hit an uncontrolled int-to-str blowup)."""
    import numpy as np
    W = _W_rational(N, edges, y_rat)
    Wf = np.array([[float(W[i][j]) for j in range(N)] for i in range(N)])
    lam_min = float(np.linalg.eigvalsh(Wf)[0])
    t0 = Fr(ceil((-lam_min) * P) + 1, P)  # smallest 1/P-grid rational strictly above -lambda_min(W)
    for bump in range(0, 8):
        t = t0 + Fr(bump, P)
        Z = [[(t if i == j else Fr(0)) + W[i][j] for j in range(N)] for i in range(N)]
        res = pm.ldlt(Z)
        if res is None:
            continue
        L, d = res
        Li, di, sc = pm.clear_denoms(L, d)
        if max(_bitlen(x) for row in Li for x in row) > max_bits:
            return None  # measured compute trap: bail before the integer blows past a checkable size
        dens = [t.denominator] + [yy.denominator for yy in y_rat] + [1]
        Dc = 1
        for x in dens:
            Dc = Dc * x // _gcd(Dc, x)
        Zn = [[int(Z[i][j] * Dc) for j in range(N)] for i in range(N)]
        if max(_bitlen(x) for row in Zn for x in row) > max_bits:
            return None
        # re-factor the integer numerator matrix directly for a clean integer certificate of Zn (PSD iff Z is)
        res2 = pm.ldlt([[Fr(Zn[i][j]) for j in range(N)] for i in range(N)])
        if res2 is None:
            continue
        L2, d2 = res2
        Li2, di2, sc2 = pm.clear_denoms(L2, d2)
        biggest = max(
            max((_bitlen(x) for row in Li2 for x in row), default=0),
            max((_bitlen(x) for x in di2), default=0),
            _bitlen(sc2),
        )
        if biggest > max_bits:
            return None  # cert (incl. diagonal/scale) too large -- the measured compute trap
        if pm.verify_int_cert(Zn, Li2, di2, sc2):
            return t, Zn, (Li2, di2, sc2)
    return None


def _bitlen(x: int) -> int:
    return int(x).bit_length()


def run_cell(n: int, d: int, kernel=None) -> dict:
    known = KNOWN.get((n, d))
    N, edges = confusability_graph(n, d)
    row = {"cell": f"A({n},{d})", "n": n, "d": d, "known": known, "n_vertices": N, "n_edges": len(edges)}
    sol = solve_theta_dual(N, edges)
    if sol is None:
        row["status"] = "sdp-infeasible"
        return row
    t_float, y_float = sol
    row["sdp_theta_float"] = round(t_float, 6)
    best = None
    for P in (10, 100, 1000, 10 ** 4, 10 ** 5):
        y_rat = [Fr(round(v * P), P) for v in y_float]
        got = min_rational_cert(N, edges, y_rat, P)
        if got is None:
            continue
        t, Zn, (Li, di, sc) = got
        allints = [x for r in Zn for x in r] + [x for r in Li for x in r] + list(di) + [sc]
        bits = max((int(abs(x)).bit_length() for x in allints), default=0)
        cand = {"P": P, "cert_bound_float": round(float(t), 6), "t": t, "Zn": Zn, "cert": (Li, di, sc),
                "max_bits": bits}
        if best is None or float(t) < float(best["t"]):
            best = cand
        if known is not None and floor(float(t)) <= known:
            break  # already reproduces (or beats) known at this P; a finer grid buys nothing for this probe
    if best is None:
        # SDP itself solved fine (sdp_theta_float is set); only the exact-rational-certificate rounding
        # step failed. floor(sdp_theta_float) is a HONEST, uncertified sanity number (NOT a proven bound --
        # it rests on the untrusted float solve only) reported for context, never treated as verified.
        row.update({"status": "compute-trap(cert-bits-exceeded)",
                    "sdp_only_floor_uncertified": floor(t_float) if t_float >= 0 else 0,
                    "note": ("naive rational-Cholesky certificate bit-length exceeded the measured safety "
                              f"ceiling ({_MAX_CERT_BITS} bits) before a kernel-checkable cert was found -- "
                              "the SAME compute trap scripts/psd_scaling_probe.py measured; mitigation is "
                              "Bareiss/fraction-free elimination (not built here). SDP solve itself succeeded.")})
        return row
    bound = floor(best["t"]) if best["t"] >= 0 else 0
    row.update({"best_P": best["P"], "cert_bound": bound, "cert_bound_exact": str(best["t"]),
                "cert_max_bits": best["max_bits"],
                "reproduces_known": (known is not None and bound == known),
                "matches_or_beats_known": (known is not None and bound <= known),
                "status": "verified"})
    if kernel is not None:
        Li, di, sc = best["cert"]
        row["kernel"] = kernel(best["Zn"], Li, di, sc)
        row["_cert"] = (best["Zn"], Li, di, sc)  # kept only in-memory for main(); stripped before JSON dump
    return row


def main() -> int:
    try:
        from leibniz.backends.lean_cli import LeanCliBackend, available
        bk = LeanCliBackend(timeout_s=180) if available() else None
    except Exception:
        bk = None

    def kern(Zn, Li, di, sc):
        if bk is None:
            return "unavailable(no-docker)"
        try:
            src = pm.render_ldlt_lean(Zn, Li, di, sc)
        except ValueError as e:  # defense in depth: min_rational_cert already caps bits before this is
            return f"unrenderable({e})"  # called, so this should not trigger, but never let a render blowup crash the run
        # Prepend (not edit render_ldlt_lean itself, which is PROTECTED): the DEFAULT Lean heartbeat budget
        # (200000) was measured to time out on some of these certs' `decide` elaboration even though the
        # underlying kernel reduction itself completes in seconds once unthrottled -- see the module
        # docstring's "MEASURED wall" note. This is a harness-side option, not a change to what is checked.
        return bk.check_source("set_option maxHeartbeats 0\n" + src)

    cells = [(4, 2), (4, 4), (5, 2)]
    rows = [run_cell(n, d, kernel=kern) for (n, d) in cells]

    # soundness control: kernel-reject a bogus certificate (corrupted diagonal) on the first verified cell
    bogus_kernel = None
    repro = next((r for r in rows if r.get("status") == "verified" and "_cert" in r), None)
    if repro is not None and bk is not None:
        Zn, Li, di, sc = repro["_cert"]
        bogus_di = [x - 10 ** 9 for x in di]  # forces a negative diagonal entry -> ldltOK must be false
        try:
            bogus_src = pm.render_ldlt_lean(Zn, Li, bogus_di, sc)
            bogus_kernel = bk.check_source("set_option maxHeartbeats 0\n" + bogus_src)
        except ValueError:
            bogus_kernel = None

    for r in rows:
        r.pop("_cert", None)  # drop the large in-memory-only payload before JSON serialization

    verified = [r for r in rows if r.get("status") == "verified"]
    reproduced = [r for r in verified if r.get("reproduces_known")]
    kernel_ok = [r for r in verified if r.get("kernel") is True]
    below_known = [r for r in verified if r.get("known") is not None and r["cert_bound"] < r["known"]]

    sound = (bogus_kernel is False) if bogus_kernel is not None else None
    gate = ("GREEN" if (len(reproduced) >= 2 and len(kernel_ok) >= 2 and not below_known
                        and sound in (True, None))
            else "AMBER(partial)" if reproduced else "RED")

    res = {"gate": gate, "cells": len(rows), "verified": len(verified), "reproduced_known": len(reproduced),
           "kernel_verified": len(kernel_ok), "below_known_count": len(below_known),
           "bogus_cert_kernel_result": bogus_kernel, "sound": sound, "rows": rows,
           "reading": ("Pre-validates the code-SDP -> dual -> rational-cert -> kernel chain (the #212/#214 "
                       "gates used synthetic matrices / theta of cycles as a proxy; this uses REAL binary-code "
                       "confusability-graph SDPs). EXPECTED: the SDP (Lovász theta) bound equals the existing "
                       "Delsarte LP bound on these tiny highly-symmetric cells -- no improvement is claimed or "
                       "expected here. GREEN => the full chain (untrusted SCS solve -> exact rational rounding "
                       "-> kernel-checked integer PSD certificate -> floor -> matches known A(n,d)) is "
                       "mechanically sound end-to-end on real code SDPs, clearing the way for the Terwilliger "
                       "three-point build where an actual improvement over LP would be sought.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")

    print(f"code-SDP -> kernel pipeline pre-validation: {res['gate']}")
    for r in res["rows"]:
        extra = ""
        if r.get("status") == "verified":
            extra = (f"sdp_theta~{r['sdp_theta_float']} cert_bound={r['cert_bound']} known={r['known']} "
                     f"bits={r['cert_max_bits']} kernel={r.get('kernel')}")
        elif r.get("status", "").startswith("compute-trap"):
            extra = (f"sdp_theta~{r.get('sdp_theta_float')} known={r['known']} "
                     f"uncertified_floor={r.get('sdp_only_floor_uncertified')} (no kernel cert -- see note)")
        print(f"  {r['cell']:9s} N={r['n_vertices']:4d} {r.get('status',''):26s} {extra}")
    print(f"  verified={res['verified']} reproduced_known={res['reproduced_known']} "
          f"kernel_verified={res['kernel_verified']} below_known={res['below_known_count']} "
          f"bogus_cert_kernel={res['bogus_cert_kernel_result']} sound={res['sound']}")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

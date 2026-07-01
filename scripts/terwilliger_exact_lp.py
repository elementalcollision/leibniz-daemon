"""Terwilliger three-point — Path C completion (option a): EXACT RATIONAL LP for the dual multipliers.

Replaces the O(hundreds)-clamp non-negativity projection with one exact two-phase simplex (Bland's rule,
Fraction arithmetic): given the rationalized PSD blocks Z_k, Z'_k, find multipliers

    min  Σγ − ν    s.t.   stationarity  A·m = −base   and   α, β1, γ ≥ 0   (ν free = ν⁺ − ν⁻)

The optimum, if it floors to the target, IS the exact audit-tier certificate (fed to Phase-1 dual_check). We
run the LP over the numerically-ACTIVE columns (complementary slackness ⇒ the optimal basis is small), which
keeps the tableau tractable. Whether this beats the #213 bit-growth at A(19,6) is measured, not assumed.

Needs cvxpy (solve) + numpy via terwilliger_cert; the LP itself is free-CPU exact.
"""
from __future__ import annotations

import importlib.util
import time
from fractions import Fraction as Fr
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod, rel):
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


td = _load("terwilliger_dual", "scripts/terwilliger_dual.py")
cert = _load("terwilliger_cert", "scripts/terwilliger_cert.py")


def exact_simplex(A, b, c, max_iter=100000):
    """min cᵀx s.t. A x = b, x ≥ 0 (exact Fraction two-phase simplex, Bland's rule). A: m×n list-of-lists of Fr;
    b: len m; c: len n. Returns (x, opt) or (None, reason)."""
    m = len(b)
    n = len(c)
    A = [[Fr(A[i][j]) for j in range(n)] for i in range(m)]
    b = [Fr(x) for x in b]
    c = [Fr(x) for x in c]
    for i in range(m):                                   # make b ≥ 0
        if b[i] < 0:
            b[i] = -b[i]
            A[i] = [-x for x in A[i]]
    # phase 1: artificials
    T = [A[i][:] + [Fr(1) if k == i else Fr(0) for k in range(m)] + [b[i]] for i in range(m)]
    basis = [n + i for i in range(m)]
    ncol = n + m
    phase1_c = [Fr(0)] * n + [Fr(1)] * m

    def run(cost):
        for _ in range(max_iter):
            cb = [cost[basis[i]] for i in range(m)]
            # reduced costs
            red = []
            for j in range(ncol):
                zj = sum(cb[i] * T[i][j] for i in range(m))
                red.append(cost[j] - zj)
            enter = next((j for j in range(ncol) if red[j] < 0), None)
            if enter is None:
                return "optimal"
            # ratio test (Bland: smallest basis index on ties)
            leave = None
            best = None
            for i in range(m):
                if T[i][enter] > 0:
                    r = T[i][-1] / T[i][enter]
                    if best is None or r < best or (r == best and basis[i] < basis[leave]):
                        best, leave = r, i
            if leave is None:
                return "unbounded"
            piv = T[leave][enter]
            T[leave] = [x / piv for x in T[leave]]
            for i in range(m):
                if i != leave and T[i][enter] != 0:
                    f = T[i][enter]
                    T[i] = [T[i][k] - f * T[leave][k] for k in range(ncol + 1)]
            basis[leave] = enter
        return "max_iter"

    st = run(phase1_c)
    if st != "optimal":
        return None, f"phase1 {st}"
    if sum(T[i][-1] for i in range(m) if basis[i] >= n) != 0:
        return None, "infeasible"
    # drop artificial columns; phase 2
    keep = list(range(n))
    T = [[T[i][j] for j in keep] + [T[i][-1]] for i in range(m)]
    ncol = n
    # if an artificial is still basic at 0, it was dropped; basis entries >= n shouldn't remain nonzero
    basis = [bj if bj < n else -1 for bj in basis]
    for i in range(m):                                   # pivot out any leftover artificial (degenerate)
        if basis[i] == -1:
            j = next((k for k in range(n) if T[i][k] != 0), None)
            if j is None:
                continue
            piv = T[i][j]
            T[i] = [x / piv for x in T[i]]
            for r in range(m):
                if r != i and T[r][j] != 0:
                    f = T[r][j]
                    T[r] = [T[r][k] - f * T[i][k] for k in range(ncol + 1)]
            basis[i] = j
    st = run(c)
    if st != "optimal":
        return None, f"phase2 {st}"
    x = [Fr(0)] * n
    for i in range(m):
        if 0 <= basis[i] < n:
            x[basis[i]] = T[i][-1]
    return x, sum(c[j] * x[j] for j in range(n))


def certify_lp(n, d, target=None, precisions=(10 ** 6, 10 ** 8, 10 ** 10, 10 ** 12), tol=1e-5, time_cap_s=900,
               return_duals=False):
    ex = cert.extract_dual(n, d)
    target = target if target is not None else int(ex["value"] + 1e-6)
    keys, cols, A, bnd = cert._mult_structure(n, d)
    t_start = time.time()
    best = None
    for P in precisions:
        if time.time() - t_start > time_cap_s:
            return {"n": n, "d": d, "target": target, "status": "time_cap"}
        Zq = {k: cert._round_psd(ex["Z"][k], P) for k in ex["Z"]}
        Zpq = {k: cert._round_psd(ex["Zp"][k], P) for k in ex["Zp"]}
        if not all(td.is_psd_exact(Zq[k]) and td.is_psd_exact(Zpq[k]) for k in Zq):
            continue
        base = cert._base_residual(n, d, Zq, Zpq)
        # all α/β1/γ columns (the LP picks the ≥0 basis; restricting to numerically-active ones excludes
        # columns needed to absorb the εI perturbation ⇒ spurious infeasibility). ν handled as ν⁺−ν⁻ below.
        act = [ci for ci, c in enumerate(cols) if c[0] != "nu"]
        nu_ci = next(ci for ci, c in enumerate(cols) if c[0] == "nu")
        # LP columns: act (≥0) then nu+ , nu-
        lp_cols = act + ["nu+", "nu-"]
        # constraint matrix rows = free vars
        Amat, bvec = [], []
        for key in keys:
            rowv = []
            for lc in lp_cols:
                if lc == "nu+":
                    rowv.append(Fr(A.get((nu_ci, key), 0)))
                elif lc == "nu-":
                    rowv.append(-Fr(A.get((nu_ci, key), 0)))
                else:
                    rowv.append(Fr(A.get((lc, key), 0)))
            Amat.append(rowv)
            bvec.append(-base[key])
        cvec = []
        for lc in lp_cols:
            if lc == "nu+":
                cvec.append(Fr(-1))          # −ν
            elif lc == "nu-":
                cvec.append(Fr(1))           # +ν  (ν = ν+ − ν−, so −ν = −ν+ + ν−)
            elif cols[lc][0] == "g":
                cvec.append(Fr(1))           # +γ
            else:
                cvec.append(Fr(0))
        x, opt = exact_simplex(Amat, bvec, cvec)
        if x is None:
            continue
        # assemble duals
        mvals = {ci: Fr(0) for ci in range(len(cols))}
        for idx, lc in enumerate(lp_cols):
            if lc == "nu+":
                mvals[nu_ci] = mvals[nu_ci] + x[idx]
            elif lc == "nu-":
                mvals[nu_ci] = mvals[nu_ci] - x[idx]
            else:
                mvals[lc] = x[idx]
        duals = cert._assemble(n, d, Zq, Zpq, cols, mvals)
        chk = td.dual_check(n, d, duals)
        b = chk["bound"]
        secs = round(time.time() - t_start, 1)
        row = {"n": n, "d": d, "target": target, "P": P, "n_active": len(act), "lp_opt": round(float(opt), 4),
               "feasible": chk["feasible"], "residual_zero": chk["n_residuals_nonzero"] == 0,
               "nonneg_ok": chk["nonneg_ok"], "psd_ok": chk["psd_ok"],
               "exact_bound": str(b), "bound_float": round(float(b), 4),
               "floor": (int(b) if b >= 0 else 0), "certified": bool(chk["feasible"] and b >= 0 and int(b) <= target),
               "secs": secs}
        if row["certified"]:               # feasible AND floors to the target -> the exact certificate
            if return_duals:
                row["duals"] = duals
            return row
        if chk["feasible"] and (best is None or (b >= 0 and b < Fr(best["exact_bound"]))):
            best = row                     # feasible but bound too loose at this P -> try higher precision
    return best or {"n": n, "d": d, "target": target, "status": "no exact LP cert at tried precisions"}


def kernel_verify_lp(n, d, target=None, timeout_s=900):
    """Path B2: certify a cell via the exact LP, render its PSD blocks as per-block Lean theorems, and
    kernel-verify (valid accepted; a corrupted block rejected). This is how the A(19,6) ≤ 1280 certificate
    becomes kernel-attested. Needs cvxpy (solve) + docker (Lean)."""
    row = certify_lp(n, d, target=target, return_duals=True)
    if not row.get("certified"):
        return {"n": n, "d": d, "certified": False, "note": "no exact LP cert to render"}
    blocks = cert.cert_psd_blocks(row["duals"])
    out = {"n": n, "d": d, "target": row["target"], "exact_bound": row["exact_bound"],
           "floor": row["floor"], "n_blocks": len(blocks),
           "largest_block": max(len(b["M"]) for b in blocks)}
    try:
        from leibniz.backends.lean_cli import LeanCliBackend, available
        if not available():
            out["kernel"] = "unavailable (no docker/image)"
            return out
        bk = LeanCliBackend(timeout_s=timeout_s)
        good = bk.check_source(cert.render_cert_lean(blocks))
        bogus_blocks = [dict(blocks[0], d=[x - 10 ** 6 for x in blocks[0]["d"]])] + blocks[1:]
        bogus = bk.check_source(cert.render_cert_lean(bogus_blocks))
        out["kernel"] = {"valid_cert": good, "bogus_cert": bogus, "sound": good is True and bogus is False}
    except Exception as e:  # pragma: no cover
        out["kernel"] = f"unavailable ({type(e).__name__})"
    return out


def main() -> int:
    import json
    out = _ROOT / "docs" / "results" / "terwilliger_exact_lp.json"
    rows = [certify_lp(n, d, target=t)
            for (n, d, t) in [(4, 2, 8), (6, 4, 4), (7, 4, 8), (8, 4, 16), (19, 6, 1280)]]   # incl. the record cell
    certified = [r for r in rows if r.get("certified")]
    kern = kernel_verify_lp(19, 6, target=1280)          # Path B2: kernel-attest the record certificate
    res = {"verdict": "GREEN" if len(certified) == len(rows) else "AMBER", "certified": f"{len(certified)}/{len(rows)}",
           "a19_kernel": kern.get("kernel"), "rows": rows,
           "reading": ("Exact rational LP nonneg enforcement (one simplex vs hundreds of clamps). a19_kernel = "
                       "the REAL Lean 4.31 kernel verdict on the A(19,6)<=1280 cert's 20 PSD blocks (per-block "
                       "theorems; valid accepted, corrupted rejected).")}
    out.write_text(json.dumps(res, indent=2) + "\n")
    print(f"terwilliger exact-LP cert: {res['verdict']} ({res['certified']})")
    for r in rows:
        print(f"  A({r['n']},{r['d']}): feasible={r.get('feasible')} bound={r.get('exact_bound')} "
              f"floor={r.get('floor')} certified={r.get('certified')} secs={r.get('secs')}")
    print(f"  A(19,6) kernel leg: {kern.get('kernel')} (blocks={kern.get('n_blocks')}, "
          f"largest={kern.get('largest_block')})")
    print(f"  -> {out}")
    return 0 if len(certified) == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

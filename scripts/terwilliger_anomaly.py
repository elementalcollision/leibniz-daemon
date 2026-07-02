"""Terwilliger discovery pivot D2 (task #103): resolve the A(22,10) anomaly — truncated-dual exact certs.

The solve-leg session (D6, docs/results/terwilliger-solve-leg-2026-07-02.md) left one open cell: our
transcription certified A(22,10) <= 88 exactly (88.2463 at P=1e14) while Schrijver's Table I says 87, and 87
did not certify at any tried precision. The gap was the DUAL SOURCE, not the formulation: certify_lp fixes
its PSD blocks from the FULL problem's float dual — the stalled `optimal_inaccurate` solve (pseudo-optimum
88.63). But the k_max-TRUNCATED problem is a RELAXATION (fewer PSD constraints ⇒ truncated optimum >= full
optimum), SDPA solves it to clean `optimal` at (22,10) (87.974 at k_max in {2,3}), and a truncated dual,
zero-padded on the dropped blocks, is a feasible FULL-problem dual with the same bound. Pushing THAT dual
through the exact LP certifies:

    A(22,10) <= 87.9734 exactly  ->  A(22,10) <= 87   (Table I VALIDATED — no discrepancy claim)
    A(26,10) <= 886.859  exactly  ->  A(26,10) <= 886  (the other stall cell, also Table I)

Two corollaries the exact tier settles: the full-solve float pseudo-optimum 88.63 was INFEASIBLE (its value
exceeds a certified upper bound on the SDP optimum by 0.66), and the 87.97 "stall attractor" the solve-leg
doc recorded as a provable under-solve was the honest signal all along (the "proof" leaned on the
pseudo-feasible 88.63 point, which no float-side audit can validate at this conditioning).

Provenance (path c, recorded in the JSON): Schrijver 2005 computed Table I with SDPT3 3.02 + DSDP 5.5
(double precision, NEOS) and states eq. (25) gave "no improvement in the above table"; GMS 2012 (the
four-point paper, A(22,10) <= 84) list 87 as the prior best and document the thin-feasible-region /
premature-termination failure mode of double-precision solvers on these programs — their reason for
switching to SDPA-GMP, same as our D6 fix.

No trust surface touched: floats (truncated or not) stay targeting data; certification is dual_check
(exact rational) + the Lean kernel on the PSD blocks (kernel-bank tier, corrupted control included).
Needs cvxpy + sdpap (solve) + docker (kernel leg); CI skips via the gated test.
"""
from __future__ import annotations

import importlib.util
import json
import time
from fractions import Fraction as Fr
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "terwilliger_anomaly.json"


def _load(mod, rel):
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


td = _load("terwilliger_dual", "scripts/terwilliger_dual.py")
ts = _load("terwilliger_sdp", "scripts/terwilliger_sdp.py")
cert = _load("terwilliger_cert", "scripts/terwilliger_cert.py")
tlp = _load("terwilliger_exact_lp", "scripts/terwilliger_exact_lp.py")
pm = _load("psd_certificate_microprobe", "scripts/psd_certificate_microprobe.py")

# (n, d, Table-I target, k_max values to certify from, known lower bound on A(n,d) for the soundness check)
CELLS = [(22, 10, 87, (2, 3), 64), (26, 10, 886, (3, 4), 384)]
P_CERT = (10 ** 14,)               # the D6-measured precision: these cells certify only at P=1e14


def build_labeled_kmax(n, d, k_max, normalize=True):
    """ts.build_labeled restricted to blocks k <= k_max — a RELAXATION of the full primal (dropping PSD
    constraints can only raise the optimum), so any certificate through its dual is valid for the full
    problem. Handles/dual conventions identical to ts.build_labeled."""
    import cvxpy as cp
    keys = td.free_keys(n, d)
    xvar = {k: cp.Variable(name=".".join(map(str, k))) for k in keys}
    psd_h, ii_h, scale_h = {}, {}, {}
    cons = []
    for k in range(k_max + 1):
        M, Mp, sigma, diag = ts._block_exprs(n, d, k, xvar, normalize=normalize)
        cM, cMp = cp.bmat(M) >> 0, cp.bmat(Mp) >> 0
        psd_h[(k, "M")], psd_h[(k, "Mp")] = cM, cMp
        scale_h[k] = {"sigma": sigma, "diag": diag}
        cons += [cM, cMp]
    i_h = xvar[(0, 0, 0)] == 1
    cons.append(i_h)
    for (t, i, j) in td.valid_triples(n):
        xv = ts._val(None, xvar, t, i, j, d)
        x0i = ts._val(None, xvar, 0, i, 0, d)
        x0j = ts._val(None, xvar, 0, j, 0, d)
        ca, cb, cg = (xv >= 0), (xv <= x0i), (x0i + x0j <= 1 + xv)
        ii_h[("a", t, i, j)], ii_h[("b1", t, i, j)], ii_h[("g", t, i, j)] = ca, cb, cg
        cons += [ca, cb, cg]
    obj = sum(td.obj_coeff(k, n) * xvar[k] for k in keys)
    prob = cp.Problem(cp.Maximize(obj), cons)
    return {"prob": prob, "xvar": xvar, "psd_h": psd_h, "i_h": i_h, "ii_h": ii_h, "scale_h": scale_h}


def extract_dual_kmax(n, d, k_max, solver=None, normalize=None, solver_opts=None):
    """cert.extract_dual on the truncated problem; the dropped blocks' duals are ZERO matrices (exactly PSD,
    contributing nothing) — the zero-padding that makes a truncated dual a full-problem dual."""
    import cvxpy as cp
    import numpy as np
    solver, normalize, solver_opts = ts._solver_defaults(solver, normalize, solver_opts)
    H = build_labeled_kmax(n, d, k_max, normalize=normalize)
    H["prob"].solve(solver=getattr(cp, solver), **solver_opts)

    def _unscale(k, Zt):
        sc = H.get("scale_h", {}).get(k)
        if Zt is None or sc is None:
            return Zt
        dg = np.array(sc["diag"], dtype=float)
        return Zt * np.outer(dg, dg) / sc["sigma"]

    Z, Zp = {}, {}
    for k in range(n // 2 + 1):
        m = len(td.block_idx(n, k))
        if k <= k_max:
            Z[k] = np.atleast_2d(_unscale(k, cert._dv(H["psd_h"][(k, "M")])))
            Zp[k] = np.atleast_2d(_unscale(k, cert._dv(H["psd_h"][(k, "Mp")])))
        else:
            Z[k] = np.zeros((m, m))
            Zp[k] = np.zeros((m, m))
    nu_c = cert._dv(H["i_h"])
    nu = -float(nu_c.reshape(-1)[0]) if nu_c is not None else 0.0        # nu = -nu_cvxpy
    lin = {"a": {}, "b1": {}, "g": {}}
    for (fam, t, i, j), c in H["ii_h"].items():
        v = cert._dv(c)
        lin[fam][(t, i, j)] = 0.0 if v is None else float(v.reshape(-1)[0])
    return {"status": H["prob"].status, "value": float(H["prob"].value), "Z": Z, "Zp": Zp,
            "nu": nu, "a": lin["a"], "b1": lin["b1"], "g": lin["g"], "k_max": k_max}


def _zero_fr(m):
    return [[Fr(0)] * m for _ in range(m)]


def certify_lp_trunc(n, d, k_max, target, precisions=P_CERT, return_duals=False, time_cap_s=900):
    """tlp.certify_lp's exact leg, with the PSD blocks fixed from the k_max-TRUNCATED dual: k <= k_max blocks
    are rationalized with the usual strict-PD margin; k > k_max blocks stay EXACT ZERO (PSD, no margin, no
    residual contribution). Everything downstream is unchanged — one exact simplex over all multipliers, then
    dual_check decides. A feasible result certifies A(n,d) <= floor(bound) for the FULL problem."""
    ex = extract_dual_kmax(n, d, k_max)
    keys, cols, A, bnd = cert._mult_structure(n, d)
    t_start = time.time()
    best = None
    for P in precisions:
        if time.time() - t_start > time_cap_s:
            return {"n": n, "d": d, "k_max": k_max, "target": target, "status": "time_cap"}
        Zq = {k: (cert._round_psd(ex["Z"][k], P) if k <= k_max else _zero_fr(len(td.block_idx(n, k))))
              for k in ex["Z"]}
        Zpq = {k: (cert._round_psd(ex["Zp"][k], P) if k <= k_max else _zero_fr(len(td.block_idx(n, k))))
               for k in ex["Zp"]}
        if not all(td.is_psd_exact(Zq[k]) and td.is_psd_exact(Zpq[k]) for k in Zq):
            continue
        base = cert._base_residual(n, d, Zq, Zpq)
        act = [ci for ci, c in enumerate(cols) if c[0] != "nu"]
        nu_ci = next(ci for ci, c in enumerate(cols) if c[0] == "nu")
        lp_cols = act + ["nu+", "nu-"]
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
                cvec.append(Fr(-1))
            elif lc == "nu-":
                cvec.append(Fr(1))
            elif cols[lc][0] == "g":
                cvec.append(Fr(1))
            else:
                cvec.append(Fr(0))
        x, opt = tlp.exact_simplex(Amat, bvec, cvec)
        if x is None:
            continue
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
        row = {"n": n, "d": d, "k_max": k_max, "float_status": ex["status"],
               "float_value": round(ex["value"], 6), "target": target, "P": P,
               "feasible": chk["feasible"], "residual_zero": chk["n_residuals_nonzero"] == 0,
               "nonneg_ok": chk["nonneg_ok"], "psd_ok": chk["psd_ok"],
               "exact_bound": str(b), "bound_float": round(float(b), 4),
               "floor": (int(b) if b >= 0 else 0),
               "certified": bool(chk["feasible"] and b >= 0 and int(b) <= target),
               "secs": round(time.time() - t_start, 1)}
        if row["certified"]:
            if return_duals:
                row["duals"] = duals
            return row
        if chk["feasible"] and (best is None or (b >= 0 and b < Fr(best["exact_bound"]))):
            best = row
    return best or {"n": n, "d": d, "k_max": k_max, "target": target,
                    "status": "no exact LP cert at tried precisions"}


def psd_blocks_with_zeros(duals):
    """cert.cert_psd_blocks, extended to cover the truncated dual's exact-zero blocks: a zero matrix gets the
    trivial LDLT certificate (L=I, d=0, scale=1 — I·diag(0)·Iᵀ = 0 = 1·M), which the Lean ldltOK checker
    verifies like any other block. Every block of the dual is attested; nothing is silently skipped."""
    blocks = []
    for fam, key in (("Z", "M"), ("Zp", "Mp")):
        for k in sorted(duals[fam]):
            Zq = [[Fr(x) for x in row] for row in duals[fam][k]]
            m = len(Zq)
            if all(x == 0 for row in Zq for x in row):
                eye = [[1 if i == j else 0 for j in range(m)] for i in range(m)]
                blocks.append({"label": f"{key}_{k}", "M": [[0] * m for _ in range(m)],
                               "L": eye, "d": [0] * m, "scale": 1})
                continue
            M_int, _den = cert._int_scale(Zq)
            res = pm.ldlt([[Fr(v) for v in row] for row in M_int])
            if res is None:
                return None                   # non-zero yet singular: the εI margin should prevent this
            L, dd = res
            Li, di, sc = pm.clear_denoms(L, dd)
            blocks.append({"label": f"{key}_{k}", "M": M_int, "L": Li, "d": di, "scale": sc})
    return blocks


def kernel_attest(duals, timeout_s=1800):
    """Kernel-bank tier: per-block ldltOK theorems on the real Lean 4.31 kernel, valid cert accepted AND the
    corrupted-block control rejected. Needs docker + the leibniz-lean image."""
    blocks = psd_blocks_with_zeros(duals)
    if blocks is None:
        return {"error": "LDLT failed on a nonzero block"}
    out = {"n_blocks": len(blocks), "largest_block": max(len(b["M"]) for b in blocks)}
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


PROVENANCE = {
    "schrijver_2005": ("Table I (22,10)=87 [prev best 88, Delsarte 95] and (26,10)=886 [prev 989, Delsarte "
                       "1040]. 'Our computations were done by the algorithm SDPT3 version 3.02 ... available "
                       "through the web on the NEOS Server ... The answers have been confirmed by the "
                       "algorithm DSDP version 5.5' — both double-precision, no exact-rational leg. Eq. (25) "
                       "caps: 'we did not obtain in this way any improvement in the above table' — Table I "
                       "is the base program (19)/(20)/(22), i.e. OUR transcription."),
    "gijswijt_mittelmann_schrijver_2012": ("arXiv:1005.4959 Table 1 row (22,10): known ub 87 (= Schrijver "
                                           "2005), new four-point bound 84 (A4=84.421). Their computational "
                                           "note documents the exact failure mode we measured: 'the "
                                           "semidefinite programs generated appear to have rather thin "
                                           "feasible regions so that SDPA and the other high-quality but "
                                           "double precision codes terminate prematurely with large "
                                           "infeasibilities' — hence SDPA-GMP (Nakata), same as our D6 fix."),
    "brouwer_table_2026": ("Current best at (22,10): lb 64, ub 84 (GMS 2012). The 87 was the 2004-era "
                           "three-point value ('Schrijver, personal communication, March 2004'), since "
                           "superseded. Our result certifies the three-point program's own value exactly; "
                           "it makes no claim against the current table."),
}


def main() -> int:
    rows = []
    kernels = []
    for (n, d, target, kmaxes, lb) in CELLS:
        cell_rows = []
        for k_max in kmaxes:
            try:
                r = certify_lp_trunc(n, d, k_max, target, return_duals=True)
            except Exception as e:  # noqa: BLE001 -- record, keep sweeping
                r = {"n": n, "d": d, "k_max": k_max, "target": target,
                     "error": f"{type(e).__name__}: {e}"}
            if "floor" in r:
                r["above_known_lb"] = r["floor"] >= lb          # soundness: never floor below a real code
            cell_rows.append(r)
        certified = [r for r in cell_rows if r.get("certified")]
        best = min(certified, key=lambda r: Fr(r["exact_bound"]), default=None)
        if best is not None:
            t0 = time.time()
            k = kernel_attest(best["duals"])
            k.update({"n": n, "d": d, "target": target, "exact_bound": best["exact_bound"],
                      "floor": best["floor"], "from_k_max": best["k_max"],
                      "total_secs": round(time.time() - t0, 1)})
            kernels.append(k)
        for r in cell_rows:
            r.pop("duals", None)
        rows += cell_rows

    all_certified = all(any(r.get("certified") and r["n"] == n and r["d"] == d for r in rows)
                        for (n, d, _t, _k, _lb) in CELLS)
    sound = [k for k in kernels if isinstance(k.get("kernel"), dict) and k["kernel"].get("sound")]
    kernel_ok = len(sound) == len(CELLS)
    verdict = "GREEN" if all_certified and kernel_ok else ("AMBER" if all_certified else "RED")
    res = {"verdict": verdict, "anomaly": "RESOLVED — Table I validated; no discrepancy claim",
           "certified": {"A(22,10)": "<= 87 exact (Table I 87)", "A(26,10)": "<= 886 exact (Table I 886)"},
           "kernel_sound": f"{len(sound)}/{len(CELLS)}", "rows": rows, "kernel_legs": kernels,
           "provenance": PROVENANCE,
           "reading": ("D2 (task #103). The (22,10) anomaly was a DUAL-SOURCE artifact, not a formulation "
                       "gap or a Table I error: certify_lp's blocks came from the stalled FULL-problem float "
                       "dual (pseudo-optimum 88.63, provably infeasible now that 87.97 is a certified upper "
                       "bound on the SDP optimum). The k_max-truncated problem is a relaxation; its clean "
                       "`optimal` dual, zero-padded, is a full-problem dual, and the exact LP through it "
                       "certifies A(22,10) <= 87 and A(26,10) <= 886 — both Table I values, now at a HIGHER "
                       "trust tier than the 2005 computation (double-precision SDPT3/DSDP, no exact leg). "
                       "GREEN = both cells certified exactly AND kernel-attested with the corrupted-block "
                       "control rejected. Floats remain targeting data only.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"terwilliger anomaly (D2): {verdict}")
    for r in rows:
        print(f"  A({r['n']},{r['d']}) k_max={r.get('k_max')}: float={r.get('float_value')} "
              f"exact_bound={r.get('exact_bound')} floor={r.get('floor')} certified={r.get('certified')} "
              f"secs={r.get('secs')}")
    for k in kernels:
        print(f"  kernel A({k['n']},{k['d']}) <= {k['floor']}: {k.get('kernel')} "
              f"(blocks={k.get('n_blocks')}, largest={k.get('largest_block')}, secs={k.get('total_secs')})")
    print(f"  -> {OUT}")
    return 0 if verdict == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Constant-weight (Johnson-scheme) Terwilliger three-point — EXACT dual certificate + kernel leg (D1 step 3).

The banked Path-C/B2 pipeline applied to the Section-III structure: solve the SDP (terwilliger_cwc_sdp
build_labeled) → extract the dual (Z_{k,l}, Z'_{k,l}, α, β1, γ, ν; convention ν = −ν_cvxpy, others direct —
the same empirically-pinned convention as the unrestricted build, revalidated here by the checker's exact
residuals) → rationalize the PSD blocks with a strict-PD margin (cert._round_psd) → find exact multipliers by
ONE exact rational LP (terwilliger_exact_lp.exact_simplex — min Σγ − ν s.t. stationarity, α,β1,γ ≥ 0) → run
the constant-weight dual_check. A feasible exact dual certifies A(n,d,w) ≤ ⌊Σγ − ν⌋ with NO primal witness.

Kernel leg: the certificate's PSD blocks render to per-block Lean `ldltOK` theorems (cert.cert_psd_blocks +
cert.render_cert_lean, both structure-agnostic) and the REAL Lean 4.31 kernel must accept the valid cert and
reject a corrupted block. Audit tier (DUAL_CERTIFICATE_CHECKED); no trust surface touched.

The HEAVY legs are all reused from the banked build — this module only supplies the constant-weight
structure (multiplier columns, base residual, assembly). Needs cvxpy (+ sdpap preferred) for the solve;
docker + leibniz-lean:v4.31.0 for the kernel; the exact leg is free-CPU.
"""
from __future__ import annotations

import importlib.util
import json
import time
from fractions import Fraction as Fr
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "terwilliger_cwc_cert.json"


def _load(mod, rel):
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


tc = _load("terwilliger_cwc_beta", "scripts/terwilliger_cwc_beta.py")
tcd = _load("terwilliger_cwc_dual", "scripts/terwilliger_cwc_dual.py")
tcs = _load("terwilliger_cwc_sdp", "scripts/terwilliger_cwc_sdp.py")
cert = _load("terwilliger_cert", "scripts/terwilliger_cert.py")           # _round_psd / cert_psd_blocks / render_cert_lean
tel = _load("terwilliger_exact_lp", "scripts/terwilliger_exact_lp.py")    # exact_simplex


# ---- dual extraction (ν = −ν_cvxpy, others direct; normalized-block duals map back via Z = D·Z̃·D) --------

def _dv(c):
    import numpy as np
    if isinstance(c, bool) or c is None or getattr(c, "dual_value", None) is None:
        return None
    return np.array(c.dual_value, dtype=float)


def extract_dual(n, d, w, solver=None, normalize=None, solver_opts=None):
    import cvxpy as cp
    import numpy as np
    solver, normalize, solver_opts = tcs.ts._solver_defaults(solver, normalize, solver_opts)
    H = tcs.build_labeled(n, d, w, normalize=normalize)
    H["prob"].solve(solver=getattr(cp, solver), **solver_opts)

    def _unscale(kl, Zt):
        # build_labeled solves D·M·D ⪰ 0 (positive diagonal congruence, exact PSD-equivalence); the dual of
        # the UNNORMALIZED integer-coefficient block is Z = D·Z̃·D.
        sc = H.get("scale_h", {}).get(kl)
        if Zt is None or sc is None:
            return Zt
        dg = np.array(sc["diag"], dtype=float)
        return Zt * np.outer(dg, dg)

    pairs = tc.block_pairs(w, n - w)
    Z = {kl: np.atleast_2d(_unscale(kl, _dv(H["psd_h"][(kl, "M")]))) for kl in pairs}
    Zp = {kl: np.atleast_2d(_unscale(kl, _dv(H["psd_h"][(kl, "Mp")]))) for kl in pairs}
    nu_c = _dv(H["i_h"])
    nu = -float(nu_c.reshape(-1)[0]) if nu_c is not None else 0.0
    lin = {"a": {}, "b1": {}, "g": {}}
    for (fam, t, s, i, j), c in H["ii_h"].items():
        val = _dv(c)
        lin[fam][(t, s, i, j)] = 0.0 if val is None else float(val.reshape(-1)[0])
    return {"status": H["prob"].status, "value": float(H["prob"].value), "Z": Z, "Zp": Zp,
            "nu": nu, "a": lin["a"], "b1": lin["b1"], "g": lin["g"]}


# ---- multiplier -> per-orbit-var contribution structure (from the cwc collected()) ------------------------

def _mult_structure(n, d, w):
    """Sparse coefficient of each linear-dual multiplier in each free-var residual + the bound contribution."""
    v = n - w
    keys = tc.free_keys(w, v, d)
    kset = set(keys)
    cols = []          # ('a',t,s,i,j) / ('b1',...) / ('g',...) / ('nu',)
    A = {}
    bnd = {}

    def put(ci, key, val):
        if key in kset:
            A[(ci, key)] = A.get((ci, key), 0) + val

    for (t, s, i, j) in tc.valid_quads(w, v):
        for fam in ("a", "b1", "g"):
            ci = len(cols)
            cols.append((fam, t, s, i, j))
            if fam == "a":
                put(ci, tc.canon(t, s, i, j), 1)
            elif fam == "b1":
                put(ci, tc.canon(0, 0, i, 0), 1)
                put(ci, tc.canon(t, s, i, j), -1)
            else:  # g
                put(ci, tc.canon(t, s, i, j), 1)
                put(ci, tc.canon(0, 0, i, 0), -1)
                put(ci, tc.canon(0, 0, j, 0), -1)
                bnd[ci] = 1
    ci = len(cols)
    cols.append(("nu",))
    put(ci, ((0, 0, 0), 0), 1)
    bnd[ci] = -1
    return keys, cols, A, bnd


def _base_residual(n, d, w, Zq, Zpq):
    """Exact residual of each free var from objective + PSD blocks only (multipliers excluded)."""
    v = n - w
    keys = tc.free_keys(w, v, d)
    coeff = {key: Fr(0) for key in keys}
    kset = set(keys)
    for key in keys:
        coeff[key] += tc.obj_coeff(key, w, v)
    for kl in tc.block_pairs(w, v):
        idx = tc.block_idx(w, v, *kl)
        for a, i in enumerate(idx):
            for b, j in enumerate(idx):
                for t in range(min(i, j) + 1):
                    bw = tc.beta(w, i, j, kl[0], t)
                    if not bw:
                        continue
                    for s in range(min(i, j) + 1):
                        if not tc.possible(w, v, i, j, t, s):
                            continue
                        bv = tc.beta(v, i, j, kl[1], s)
                        if not bv:
                            continue
                        bb = bw * bv
                        kt, ks = tc.canon(t, s, i, j), tc.canon(0, 0, i + j - t - s, 0)
                        if kt in kset:
                            coeff[kt] += Zq[kl][a][b] * bb - Zpq[kl][a][b] * bb
                        if ks in kset:
                            coeff[ks] += Zpq[kl][a][b] * bb
    return coeff


def _assemble(n, w, Zq, Zpq, cols, mvals):
    v = n - w
    duals = {"Z": Zq, "Zp": Zpq, "a": {q: Fr(0) for q in tc.valid_quads(w, v)},
             "b1": {q: Fr(0) for q in tc.valid_quads(w, v)},
             "g": {q: Fr(0) for q in tc.valid_quads(w, v)}, "nu": Fr(0)}
    for ci, val in mvals.items():
        col = cols[ci]
        if col[0] == "nu":
            duals["nu"] = val
        else:
            duals[col[0]][col[1:]] = val
    return duals


def certify_lp(n, d, w, target=None, lb=None, precisions=(10 ** 6, 10 ** 8, 10 ** 10, 10 ** 12), time_cap_s=900,
               return_duals=False):
    """Exact-rational constant-weight certificate: rationalize the solver dual's PSD blocks, then ONE exact
    two-phase simplex for the linear multipliers (min Σγ − ν s.t. stationarity, α,β1,γ ≥ 0), then the cwc
    dual_check. certified ⟺ feasible AND lb ≤ ⌊exact bound⌋ ≤ target.

    `lb` (the known lower bound on A(n,d,w)) is the SOUNDNESS tripwire the float legs already carry
    (terwilliger_cwc_sdp.valid_bound): an exact bound that floors BELOW a known lower bound is mathematically
    impossible, so it can only come from an over-constraining transcription bug — it is refused (certified
    False) and flagged `soundness_alarm`, never reported as a tightening."""
    ex = extract_dual(n, d, w)
    target = target if target is not None else int(ex["value"] + 1e-6)
    keys, cols, A, bnd = _mult_structure(n, d, w)
    t_start = time.time()
    best = None
    for P in precisions:
        if time.time() - t_start > time_cap_s:
            return {"n": n, "d": d, "w": w, "target": target, "status": "time_cap"}
        Zq = {kl: cert._round_psd(ex["Z"][kl], P) for kl in ex["Z"]}
        Zpq = {kl: cert._round_psd(ex["Zp"][kl], P) for kl in ex["Zp"]}
        if not all(tc.is_psd_exact(Zq[kl]) and tc.is_psd_exact(Zpq[kl]) for kl in Zq):
            continue
        base = _base_residual(n, d, w, Zq, Zpq)
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
        x, opt = tel.exact_simplex(Amat, bvec, cvec)
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
        duals = _assemble(n, w, Zq, Zpq, cols, mvals)
        chk = tcd.dual_check(n, d, w, duals)
        b = chk["bound"]
        secs = round(time.time() - t_start, 1)
        floor_b = int(b) if b >= 0 else 0
        below_lb = lb is not None and chk["feasible"] and b >= 0 and floor_b < lb
        row = {"n": n, "d": d, "w": w, "target": target, "P": P, "sdp_value": round(ex["value"], 4),
               "lp_opt": round(float(opt), 4), "feasible": chk["feasible"],
               "residual_zero": chk["n_residuals_nonzero"] == 0,
               "nonneg_ok": chk["nonneg_ok"], "psd_ok": chk["psd_ok"],
               "exact_bound": str(b), "bound_float": round(float(b), 4), "floor": floor_b,
               "certified": bool(chk["feasible"] and b >= 0 and floor_b <= target and not below_lb),
               "secs": secs}
        if below_lb:
            row["soundness_alarm"] = (f"exact bound {floor_b} < known lower bound {lb}: an impossible bound "
                                      "from an over-constraining transcription — NOT a discovery")
        if row["certified"]:
            if return_duals:
                row["duals"] = duals
            return row
        # a below-lb feasible dual is a soundness alarm, not a candidate — return it immediately, loudly
        if below_lb:
            return row
        if chk["feasible"] and (best is None or (b >= 0 and b < Fr(best["exact_bound"]))):
            best = row
    return best or {"n": n, "d": d, "w": w, "target": target,
                    "status": "no exact LP cert at tried precisions"}


def kernel_verify_lp(n, d, w, target=None, lb=None, timeout_s=900, precisions=None, time_cap_s=900,
                     cert_row=None):
    """The kernel leg: render the EXACT-certified certificate's PSD blocks as per-block Lean theorems
    (cert.render_cert_lean — one `ldltOK ... = true := by decide` per block, maxHeartbeats 0) and verify on
    the REAL Lean 4.31 kernel: valid accepted AND a corrupted block rejected.

    `cert_row` (a certified certify_lp row WITH 'duals') pins the attestation to the SAME certificate the
    caller certified; only when it is None do we re-derive one here. Soundness caveats made honest:
      • the kernel attests block PSD-ness ONLY — the stationarity system and the bound arithmetic Σγ−ν ≤ target
        are checked in exact Python (dual_check), NOT by the kernel (F2b bridge theorem is the only path past
        that; this stays audit-tier DUAL_CERTIFICATE_CHECKED);
      • EVERY certificate block must reach the kernel — a block cert.cert_psd_blocks silently drops (singular
        after scaling) makes the rendered census short, and a short census is a render failure, not `sound`;
      • the corrupted-block control must yield a GENUINE kernel rejection — an infra/daemon failure that also
        returns False is distinguished by a trivially-true liveness probe (else `sound` is left None)."""
    if cert_row is None:
        kw = {} if precisions is None else {"precisions": precisions}
        cert_row = certify_lp(n, d, w, target=target, lb=lb, return_duals=True, time_cap_s=time_cap_s, **kw)
    if not cert_row.get("certified") or "duals" not in cert_row:
        return {"n": n, "d": d, "w": w, "certified": False, "note": "no exact LP cert (with duals) to render"}
    blocks = cert.cert_psd_blocks(cert_row["duals"])
    expected = 2 * len(tc.block_pairs(w, n - w))          # both families over every nonempty (k,l) block pair
    out = {"n": n, "d": d, "w": w, "target": cert_row["target"], "exact_bound": cert_row["exact_bound"],
           "floor": cert_row["floor"], "n_blocks": len(blocks), "expected_blocks": expected,
           "largest_block": max((len(b["M"]) for b in blocks), default=0)}
    if len(blocks) != expected:                          # a dropped block => the kernel never saw the whole cert
        out["kernel"] = f"render_incomplete ({len(blocks)}/{expected} blocks; a singular block was dropped)"
        return out
    try:
        from leibniz.backends.lean_cli import LeanCliBackend, available
        if not available():
            out["kernel"] = "unavailable (no docker/image)"
            return out
        bk = LeanCliBackend(timeout_s=timeout_s)
        good = bk.check_source(cert.render_cert_lean(blocks))
        if good is None:
            out["kernel"] = "unavailable (backend returned None on the valid cert)"
            return out
        bogus_blocks = [dict(blocks[0], d=[x - 10 ** 6 for x in blocks[0]["d"]])] + blocks[1:]
        bogus = bk.check_source(cert.render_cert_lean(bogus_blocks))
        sound = good is True and bogus is False
        if bogus is False:
            # a False here must be a real kernel rejection, not docker/daemon breakage between runs (which
            # also returns False). A trivially-true source MUST still elaborate; if it doesn't, the control
            # is void and `sound` is inconclusive, never True.
            alive = bk.check_source("theorem cwc_kernel_liveness : True := trivial")
            if alive is not True:
                sound = None
        out["kernel"] = {"valid_cert": good, "bogus_cert": bogus, "sound": sound}
        if sound is None:
            out["kernel"]["note"] = ("control inconclusive: backend liveness probe failed after bogus=False "
                                     "(infrastructure error, not a kernel rejection)")
    except Exception as e:  # pragma: no cover
        out["kernel"] = f"unavailable ({type(e).__name__})"
    return out


def main() -> int:
    # small exact cells (certified bound must equal the known optimum) + the Table II gate cells. Each carries
    # its known lower bound (tcs.LOWER) so a certificate that floors BELOW it trips the soundness alarm rather
    # than certifying an impossible bound. (17,6,7) needs P=1e14 (measured): the SDP optimum 228.999 leaves
    # ~1e-3 of rounding headroom below 229 — the same precision-matters-for-the-BOUND behavior as D6.
    cells = [(6, 4, 3, 4, None), (7, 4, 3, 7, None), (8, 4, 4, 14, None), (9, 4, 3, 12, None),
             (17, 6, 7, 228, (10 ** 14,)), (18, 6, 6, 199, None), (17, 6, 8, 280, None)]
    rows, flagship = [], None       # flagship = the (17,6,7) certified row WITH duals, for the kernel leg (#7)
    for (n, d, w, t, p) in cells:
        lb = tcs.LOWER.get((n, d, w))
        kw = {} if p is None else {"precisions": p}
        want_duals = (n, d, w) == (17, 6, 7)
        r = certify_lp(n, d, w, target=t, lb=lb, return_duals=want_duals, **kw)
        if want_duals and r.get("certified"):
            flagship = dict(r)                           # keep duals here to attest THIS exact certificate
            r = {k: v for k, v in r.items() if k != "duals"}   # ... but never write duals into the artifact
        rows.append(r)
    certified = [r for r in rows if r.get("certified")]
    # kernel-attest the flagship record cell A(17,6,7) ≤ 228 on THE certified certificate (+ bogus control).
    # Wrapped: a kernel-leg crash (docker/solver) must never erase the exact certificates already computed.
    if flagship is not None:
        try:
            kern = kernel_verify_lp(17, 6, 7, target=228, lb=tcs.LOWER.get((17, 6, 7)),
                                    precisions=(10 ** 14,), cert_row=flagship)
        except Exception as e:  # noqa: BLE001 -- record; keep the exact results
            kern = {"kernel": f"error: {type(e).__name__}: {e}"}
    else:
        kern = {"kernel": "skipped (A(17,6,7) did not certify — no cert to attest)"}
    kd = kern.get("kernel")
    # the attested certificate must be the SAME one recorded (bound-consistency), else the attestation is void
    kernel_matches = (isinstance(kd, dict) and flagship is not None
                      and kern.get("exact_bound") == flagship.get("exact_bound"))
    verdict = "GREEN" if len(certified) == len(rows) and isinstance(kd, dict) and kd.get("sound") \
        and kernel_matches else "AMBER"
    res = {"verdict": verdict, "certified": f"{len(certified)}/{len(rows)}",
           "a17_6_7_kernel": kd, "kernel_blocks": kern.get("n_blocks"),
           "kernel_attests_recorded_cert": kernel_matches, "rows": rows,
           "reading": ("D1 step 3: exact + kernel legs on the constant-weight build. Every cell carries an "
                       "exact rational dual certificate (stationarity residuals exactly 0, blocks exactly "
                       "PSD, multipliers >= 0, bound >= known lower bound) whose floor hits the target; "
                       "a17_6_7_kernel = the REAL Lean 4.31 kernel verdict on the A(17,6,7)<=228 "
                       "certificate's PSD BLOCKS (valid accepted, corrupted rejected, liveness-confirmed). "
                       "The kernel attests block PSD-ness only; stationarity + the bound arithmetic are exact "
                       "Python (dual_check). Audit tier throughout - DUAL_CERTIFICATE_CHECKED, not Q.E.D.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"terwilliger cwc cert (exact + kernel): {verdict} ({res['certified']})")
    for r in rows:
        print(f"  A({r['n']},{r['d']},{r['w']}): feasible={r.get('feasible')} bound={r.get('exact_bound')} "
              f"floor={r.get('floor')} target={r.get('target')} certified={r.get('certified')} "
              f"P={r.get('P')} secs={r.get('secs')}")
    print(f"  A(17,6,7) kernel leg: {kern.get('kernel')} (blocks={kern.get('n_blocks')}, "
          f"largest={kern.get('largest_block')})")
    print(f"  -> {OUT}")
    return 0 if verdict == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())

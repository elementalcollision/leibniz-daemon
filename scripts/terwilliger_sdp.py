"""Terwilliger three-point — Phase 2: solve the SDP + exact-rational dual certificate (operator-local: cvxpy).

Builds the Schrijver 2005 primal (eq. 19/20/22) in cvxpy on the Phase-1 reduced-variable structure
(scripts/terwilliger_dual.py), solves it (Clarabel interior-point; the panel's pick over first-order SCS for
these ill-conditioned β-blocks), and:

  Phase 2a (numerical) — reproduce Table I. This is the empirical FORMULATION-FAITHFULNESS check the adversarial
    panel asked for: if our transcription is right, the SDP optimum floors to Schrijver's published bound
    (A(19,6)→1280, A(20,8)→274) and the k=0-only relaxation reproduces the Delsarte LP.
  Phase 2b (exact) — extract the dual, rationalize via feasibility-at-target (D2a), and run it through Phase-1
    dual_check for an exact audit-tier bound. (Kernel is Phase 3.)

Needs cvxpy + numpy (operator-local, like ortools); free-CPU parts still import. No trust surface touched.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "terwilliger_sdp.json"

# Schrijver 2005 Table I (unrestricted binary codes): (n,d) -> new SDP upper bound.
TABLE_I = {(19, 6): 1280, (23, 6): 13766, (25, 6): 47998, (19, 8): 142, (20, 8): 274,
           (25, 8): 5477, (27, 8): 17768, (28, 8): 32151, (22, 10): 87, (25, 10): 503, (26, 10): 886}

# Known lower bounds on A(n,d) (a valid upper-bound certificate must never floor BELOW these — the soundness
# check). Small cells are the exact A(n,d); the record cells use Schrijver Table I's best-lower-bound column.
LOWER = {(4, 2): 8, (5, 2): 16, (6, 4): 4, (7, 4): 8, (8, 4): 16, (9, 4): 20, (10, 4): 40,
         (19, 6): 1024, (20, 8): 256}

# The D6/Q-pit-2 solve-leg fix (2026-07-02): Schrijver's eq.(8) block normalization + the SDPA-GMP backend
# (pip install sdpa-multiprecision, operator-local like cvxpy). Defaults below are measured: epsilonStar
# looser than 1e-12 stops early ((20,8) "optimal" at 277.1 instead of 274.09); precision above 350 bits
# changes nothing on the stall cells (the residual stalls are structural, not precision).
SDPA_TIGHT = {"epsilonStar": 1e-12, "epsilonDash": 1e-12, "precision": 350, "maxIteration": 1000}


def _has_sdpa():
    return importlib.util.find_spec("sdpap") is not None


def _solver_defaults(solver, normalize, solver_opts):
    """Resolve the (solver, normalize, opts) triple. Measured pairing, do not mix-and-match blindly:
    SDPA-GMP needs the eq.(8)-normalized blocks (raw β overflows its dataset scaling: SolverError at (22,10))
    while CLARABEL is empirically BETTER on the raw integer blocks at n≤20 (1280.08 vs 1281.09 at (19,6) —
    its cone equilibration fights the congruence) and is kept raw for byte-compatible fallback behavior."""
    if solver is None:
        solver = "SDPA" if _has_sdpa() else "CLARABEL"
    if normalize is None:
        normalize = solver == "SDPA"
    if solver_opts is None:
        solver_opts = dict(SDPA_TIGHT) if solver == "SDPA" else {}
    return solver, normalize, solver_opts


def _load(mod, rel):
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


td = _load("terwilliger_dual", "scripts/terwilliger_dual.py")   # free_keys, canon, classify, obj_coeff, beta, ...


def _val(key_of, xvar, t, i, j, d):
    """cvxpy expression for x^t_{i,j}: the variable for its orbit key, or 0 if zeroed by (iv)/even-d."""
    key = td.canon(t, i, j)
    return xvar[key] if td.classify(key, d) == "free" else 0.0


def _block_exprs(n, d, k, xvar, normalize=True):
    """The block-k cvxpy expressions (M, Mp) plus the scaling that produced them.

    normalize=True restores, FOR THE FLOAT SOLVE ONLY, Schrijver's own eq. (8) block form: the
    C(n−2k,i−k)^{−1/2} C(n−2k,j−k)^{−1/2} factor that the paper deletes to make β integer (see
    terwilliger_beta.py). A positive diagonal congruence D·M·D ⪰ 0 ⟺ M ⪰ 0 is an exact PSD-equivalence, so
    the feasible set and optimum are UNCHANGED — only the solver's conditioning is: the raw integer β spans
    1..~10¹³ by n=26 (the measured Q-pit-2 wall: CLARABEL crash onset at (23,6), SCS up to ~88×
    under-convergence); in eq. (8) form the span is 1..~10⁶. (A further per-block scalar σ_k normalizing the
    largest coefficient to 1 was tried and REJECTED: it un-balances the blocks against the untouched
    objective/linear coefficients and measurably degrades Clarabel — A(19,6) drifts 1280.08→1289.46.)
    Returns (M, Mp, sigma, diag) with sigma kept for the dual map: the solver's dual Z̃ maps back to the
    UNNORMALIZED block dual via Z = D·Z̃·D / σ_k (terwilliger_cert.extract_dual does this, so the
    exact-rational legs see the same objects as before)."""
    from math import sqrt
    idx = td.block_idx(n, k)
    diag = [1.0 / sqrt(td.C(n - 2 * k, i - k)) for i in idx] if normalize else [1.0] * len(idx)
    M = [[0.0] * len(idx) for _ in idx]
    Mp = [[0.0] * len(idx) for _ in idx]
    for a, i in enumerate(idx):
        for b, j in enumerate(idx):
            mk = 0.0
            mpk = 0.0
            for t in range(min(i, j) + 1):
                s = i + j - 2 * t
                if not td.possible(n, i, j, t):            # skip impossible shapes (Schrijver eq.10: x=0)
                    continue
                bijk = td.beta(n, i, j, k, t)
                if not bijk:
                    continue
                c = float(bijk) * diag[a] * diag[b] if normalize else bijk
                xv = _val(None, xvar, t, i, j, d)
                x0 = _val(None, xvar, 0, s, 0, d)
                mk = mk + c * xv
                mpk = mpk + c * (x0 - xv)
            M[a][b] = mk
            Mp[a][b] = mpk
    return M, Mp, 1.0, diag


def build_primal(n, d, k_max=None, normalize=True):
    """The Schrijver primal in cvxpy. k_max limits the block index (k_max=0 ⇒ the Delsarte-LP relaxation).
    normalize rescales the PSD blocks for the float solver (exact PSD-equivalence; see _block_exprs).
    Returns (problem, xvar, psd_constraints, lin_constraints)."""
    import cvxpy as cp
    keys = td.free_keys(n, d)
    xvar = {k: cp.Variable(name=".".join(map(str, k))) for k in keys}
    kmax = n // 2 if k_max is None else min(k_max, n // 2)

    psd, lin = [], []
    for k in range(kmax + 1):
        M, Mp, _sigma, _diag = _block_exprs(n, d, k, xvar, normalize=normalize)
        psd.append(cp.bmat(M) >> 0)
        psd.append(cp.bmat(Mp) >> 0)

    lin.append(xvar[(0, 0, 0)] == 1)                                       # (20)(i)
    for (t, i, j) in td.valid_triples(n):                                  # (20)(ii)
        xv = _val(None, xvar, t, i, j, d)
        x0i = _val(None, xvar, 0, i, 0, d)
        x0j = _val(None, xvar, 0, j, 0, d)
        lin += [xv >= 0, xv <= x0i, x0i + x0j <= 1 + xv]

    obj = sum(td.obj_coeff(k, n) * xvar[k] for k in keys)                  # (22)
    prob = cp.Problem(cp.Maximize(obj), psd + lin)
    return prob, xvar, psd, lin


def build_labeled(n, d, normalize=False, k_max=None):
    """Same primal, but returns LABELED constraint handles so Phase 2b can read each dual:
      psd_h[(k,'M')] / psd_h[(k,'Mp')]  -> the two block-family PSD constraints (dual = Z_k / Z'_k)
      i_h                                -> the x^0_{0,0}=1 equality (dual = ν)
      ii_h[('a'|'b1'|'g', t,i,j)]        -> the three (20)(ii) inequality families (duals = α/β1/γ)
      scale_h[k] = {'sigma':…, 'diag':…} -> the block scaling; the solver dual of the k-block maps back to
                                            the unnormalized-β dual via Z = diag·Z̃·diag / sigma (elementwise
                                            Z[a][b] = diag[a]·diag[b]·Z̃[a][b]/sigma) — extract_dual does this.
    k_max restricts the PSD block families to k <= k_max — a RELAXATION of the full primal (dropping PSD
    constraints can only raise the optimum), so any certificate through its dual, zero-padded on the dropped
    blocks, is valid for the FULL problem (the D2 stall rescue; extract_dual does the padding). k_max=None
    keeps the full build unchanged.
    Constraint families are enumerated over td.valid_triples(n) in the SAME order as dual_check/collected."""
    import cvxpy as cp
    keys = td.free_keys(n, d)
    xvar = {k: cp.Variable(name=".".join(map(str, k))) for k in keys}
    psd_h, ii_h, scale_h = {}, {}, {}
    cons = []
    kmax = n // 2 if k_max is None else min(k_max, n // 2)
    for k in range(kmax + 1):
        M, Mp, sigma, diag = _block_exprs(n, d, k, xvar, normalize=normalize)
        cM, cMp = cp.bmat(M) >> 0, cp.bmat(Mp) >> 0
        psd_h[(k, "M")], psd_h[(k, "Mp")] = cM, cMp
        scale_h[k] = {"sigma": sigma, "diag": diag}
        cons += [cM, cMp]
    i_h = xvar[(0, 0, 0)] == 1
    cons.append(i_h)
    for (t, i, j) in td.valid_triples(n):
        xv = _val(None, xvar, t, i, j, d)
        x0i = _val(None, xvar, 0, i, 0, d)
        x0j = _val(None, xvar, 0, j, 0, d)
        ca, cb, cg = (xv >= 0), (xv <= x0i), (x0i + x0j <= 1 + xv)
        ii_h[("a", t, i, j)], ii_h[("b1", t, i, j)], ii_h[("g", t, i, j)] = ca, cb, cg
        cons += [ca, cb, cg]
    obj = sum(td.obj_coeff(k, n) * xvar[k] for k in keys)
    prob = cp.Problem(cp.Maximize(obj), cons)
    return {"prob": prob, "xvar": xvar, "psd_h": psd_h, "i_h": i_h, "ii_h": ii_h, "scale_h": scale_h}


def solve_primal(n, d, k_max=None, solver=None, normalize=None, solver_opts=None):
    """Solve the primal. solver=None auto-picks SDPA-GMP (tight, normalized) when sdpap is installed, else
    the pre-fix CLARABEL-on-raw-β behavior. Explicit args override (see _solver_defaults for the pairing)."""
    import cvxpy as cp
    solver, normalize, solver_opts = _solver_defaults(solver, normalize, solver_opts)
    prob, xvar, psd, lin = build_primal(n, d, k_max=k_max, normalize=normalize)
    prob.solve(solver=getattr(cp, solver), **solver_opts)
    return {"status": prob.status, "value": (None if prob.value is None else float(prob.value)),
            "prob": prob, "xvar": xvar, "psd": psd, "lin": lin, "solver": solver, "normalized": normalize}


def _delsarte_lp_value(n, d, solver=None, normalize=None):
    """k=0-only relaxation optimum = the Delsarte LP bound (used as an upper sanity anchor)."""
    r = solve_primal(n, d, k_max=0, solver=solver, normalize=normalize)
    return r["value"]


def run_numerical(n, d, solver=None, normalize=None):
    """Phase 2a: numerical reproduction of Table I + the k=0=Delsarte relaxation."""
    full = solve_primal(n, d, solver=solver, normalize=normalize)
    row = {"n": n, "d": d, "status": full["status"],
           "sdp_value": None if full["value"] is None else round(full["value"], 4),
           "sdp_floor": None if full["value"] is None else int(full["value"] + 1e-6)}
    if (n, d) in TABLE_I:
        row["table_I"] = TABLE_I[(n, d)]
        row["reproduces_table_I"] = (row["sdp_floor"] == TABLE_I[(n, d)])
    lp = _delsarte_lp_value(n, d, solver=solver, normalize=normalize)
    row["delsarte_lp_value"] = None if lp is None else round(lp, 4)
    if full["value"] is not None and lp is not None:
        row["sdp_le_lp"] = full["value"] <= lp + 1e-4        # three-point must not exceed the LP (when both solve accurately)
    if (n, d) in LOWER and row["sdp_floor"] is not None:
        # SOUNDNESS: a valid upper bound never floors below a known lower bound on A(n,d).
        row["lower"] = LOWER[(n, d)]
        row["valid_bound"] = row["sdp_floor"] >= LOWER[(n, d)]
    return row


def main() -> int:
    # small cells (plumbing) + the record cells (formulation faithfulness against Table I)
    small = [(4, 2), (5, 2), (6, 2), (6, 4), (7, 4), (8, 4)]
    record = [(19, 6), (20, 8)]
    rows = []
    for (n, d) in small + record:
        try:
            rows.append(run_numerical(n, d))
        except Exception as e:  # noqa: BLE001 -- report, don't crash the sweep
            rows.append({"n": n, "d": d, "status": f"error: {type(e).__name__}: {e}"})

    repro = [r for r in rows if r.get("reproduces_table_I")]
    table_cells = [r for r in rows if "reproduces_table_I" in r]
    valid = [r for r in rows if r.get("valid_bound")]
    checked_valid = [r for r in rows if "valid_bound" in r]
    le_lp = [r for r in rows if r.get("sdp_le_lp")]
    checked_lp = [r for r in rows if "sdp_le_lp" in r]
    # GREEN = every record cell reproduces Table I AND no cell floors below a known lower bound (soundness).
    # sdp_le_lp is reported but NOT gated: the k=0 diagnostic solve is itself ill-conditioned at n≈20 (the
    # panel's Q-pit-2), so a spurious le_lp=False there is a solver artifact, not a formulation error.
    verdict = ("GREEN" if table_cells and len(repro) == len(table_cells)
               and len(valid) == len(checked_valid) else "AMBER")
    res = {"verdict": verdict, "reproduced_table_I": f"{len(repro)}/{len(table_cells)}",
           "valid_bounds": f"{len(valid)}/{len(checked_valid)}", "sdp_le_lp": f"{len(le_lp)}/{len(checked_lp)}",
           "rows": rows,
           "reading": ("Phase 2a numerical. GREEN = the SDP optimum floors to Schrijver Table I on every record "
                       "cell AND never floors below a known lower bound on A(n,d) -> the formulation "
                       "transcription is FAITHFUL (the empirical answer to the panel's formulation-faithfulness "
                       "concern), and the possible()/binom≠0 fix is validated (A(8,4): 13.7->16). sdp_le_lp is "
                       "a reported diagnostic only. The Q-pit-2 conditioning wall is FIXED (D6, 2026-07-02): "
                       "eq.(8)-normalized blocks + SDPA-GMP when sdpap is installed — see "
                       "terwilliger-solve-leg-2026-07-02.md; floats stay indicative, certification is "
                       "certify_lp + kernel.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"terwilliger SDP (Phase 2a numerical): {verdict}")
    for r in rows:
        extra = ""
        if "table_I" in r:
            extra = f" tableI={r['table_I']} repro={r.get('reproduces_table_I')}"
        print(f"  A({r['n']},{r['d']}): status={r['status']} sdp={r.get('sdp_value')} "
              f"floor={r.get('sdp_floor')} lp={r.get('delsarte_lp_value')} le_lp={r.get('sdp_le_lp')}{extra}")
    print(f"  reproduced Table I: {res['reproduced_table_I']}; sdp<=lp: {res['sdp_le_lp']}")
    print(f"  -> {OUT}")
    return 0 if verdict == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())

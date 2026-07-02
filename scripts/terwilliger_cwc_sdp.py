"""Constant-weight (Johnson-scheme) Terwilliger three-point — the SDP producer (operator-local: cvxpy).

Builds the Schrijver 2005 Section-III primal (eq. 64/65/67) on the terwilliger_cwc_beta structure and solves
it. D1 step 2 is the FORMULATION-FAITHFULNESS gate: if the transcription is right, the SDP optimum floors to
Schrijver's published Table II bound on the gate cells (A(17,6,7)→228, A(18,6,6)→199, A(17,6,8)→280 — the
constant-weight analogue of the unrestricted (19,6)/(20,8) gate), and never floors below a known lower bound.

    maximize   Σ_i C(w,i)·C(v,i)·y^{0,0}_{i,0}                                            (67)
    s.t. (64)  M_{k,l}(y) ⪰ 0 and M'_{k,l}(y) ⪰ 0    for all (k,l), W_k∩V_l ≠ ∅
         (65)  (i) y^{0,0}_{0,0}=1 ; (ii) 0 ≤ y^{t,s}_{i,j} ≤ y^{0,0}_{i,0},
               y^{0,0}_{i,0} + y^{0,0}_{j,0} ≤ 1 + y^{t,s}_{i,j}   over POSSIBLE quads only
         (iii)/(iv) folded into the orbit variables / zero classification (terwilliger_cwc_beta).

Solver pairing mirrors the banked solve-leg fix (terwilliger_sdp._solver_defaults): SDPA-GMP tight on the
eq.(58)-normalized blocks when sdpap is installed, else CLARABEL on raw integer coefficients. The
normalization deletes/restores the (w−2k,i−k)^{−1/2}(v−2l,i−l)^{−1/2} row/column factors — a positive diagonal
congruence, exact PSD-equivalence; duals map back via Z = D·Z̃·D (terwilliger_cwc_cert handles that).

Needs cvxpy + numpy (operator-local); free-CPU parts still import. No trust surface touched (audit tier).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "terwilliger_cwc_sdp.json"


def _load(mod, rel):
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


tc = _load("terwilliger_cwc_beta", "scripts/terwilliger_cwc_beta.py")
ts = _load("terwilliger_sdp", "scripts/terwilliger_sdp.py")     # _solver_defaults / SDPA_TIGHT reuse

# Schrijver 2005 Table II (constant-weight codes): (n,d,w) -> new SDP upper bound. Transcribed from the paper
# (page 8); (23,8,11) lower==upper==1288 is the paper's own "exact value" cross-check of the transcription.
TABLE_II = {
    (17, 6, 7): 228, (17, 6, 8): 280, (18, 6, 6): 199, (19, 6, 8): 718, (21, 6, 9): 2359,
    (21, 6, 10): 2685, (22, 6, 9): 3736, (22, 6, 10): 4415, (26, 6, 11): 42075, (26, 6, 12): 50169,
    (21, 8, 9): 314, (21, 8, 10): 383, (22, 8, 9): 473, (22, 8, 10): 634, (22, 8, 11): 680,
    (23, 8, 9): 707, (23, 8, 10): 1025, (23, 8, 11): 1288, (24, 8, 9): 1041, (24, 8, 10): 1551,
    (24, 8, 11): 2142, (25, 8, 9): 1486, (25, 8, 10): 2333, (25, 8, 11): 3422, (25, 8, 12): 4087,
    (26, 8, 9): 2108, (26, 8, 10): 3496, (26, 8, 11): 5225, (26, 8, 12): 6741, (26, 8, 13): 7080,
    (27, 8, 10): 4986, (27, 8, 11): 7833, (27, 8, 13): 11981, (28, 8, 10): 7016, (28, 8, 12): 17011,
    (28, 8, 13): 21152, (28, 8, 14): 22710,
    (22, 10, 10): 72, (22, 10, 11): 80, (24, 10, 9): 118, (25, 10, 11): 380, (25, 10, 12): 434,
    (26, 10, 10): 406, (26, 10, 11): 566, (26, 10, 12): 702, (26, 10, 13): 754, (27, 10, 10): 571,
    (27, 10, 11): 882, (27, 10, 12): 1201, (27, 10, 13): 1419, (28, 10, 11): 1356, (28, 10, 12): 1977,
    (25, 12, 10): 37, (26, 12, 11): 66, (26, 12, 13): 91, (27, 12, 10): 64, (28, 12, 10): 87,
}

# The paper's Delsarte column on the gate cells (reported diagnostic: our SDP must not exceed it).
DELSARTE_COL = {(17, 6, 7): 249, (17, 6, 8): 283, (18, 6, 6): 204}

# Known lower bounds on A(n,d,w): a valid upper-bound certificate must never floor BELOW these. Small cells
# are exact optima (d=2 ⇒ the whole Johnson space; d=4 Steiner cells match the validated cwc oracle
# ground truth in scripts/cwc_table_oracle.py); gate cells use Table II's best-lower-bound column.
LOWER = {
    (4, 2, 2): 6, (5, 2, 2): 10, (6, 2, 3): 20,
    (6, 4, 3): 4, (7, 4, 3): 7, (8, 4, 4): 14, (9, 4, 3): 12,
    (17, 6, 7): 166, (17, 6, 8): 184, (18, 6, 6): 132,
}


def _val(yvar, d, t, s, i, j):
    """cvxpy expression for y^{t,s}_{i,j}: its orbit variable, or 0 if zeroed by (65)(iv)."""
    key = tc.canon(t, s, i, j)
    return yvar[key] if tc.classify(key, d) == "free" else 0.0


def _block_exprs(w, v, d, k, l, yvar, normalize=True):  # noqa: E741
    """The (k,l)-block cvxpy expressions (M, Mp) plus the diagonal that produced them. normalize=True restores
    Schrijver's eq. (58) form (the paper deletes the row/column binomial factors to make coefficients integer;
    restoring them is a positive diagonal congruence — exact PSD-equivalence, better float conditioning; the
    same measured fix as the unrestricted build's Q-pit-2). Duals of the normalized block map back to the
    integer-coefficient dual via Z = D·Z̃·D."""
    from math import sqrt
    idx = tc.block_idx(w, v, k, l)
    diag = ([1.0 / sqrt(tc.C(w - 2 * k, i - k) * tc.C(v - 2 * l, i - l)) for i in idx]
            if normalize else [1.0] * len(idx))
    M = [[0.0] * len(idx) for _ in idx]
    Mp = [[0.0] * len(idx) for _ in idx]
    for a, i in enumerate(idx):
        for b, j in enumerate(idx):
            mk = 0.0
            mpk = 0.0
            for t in range(min(i, j) + 1):
                bw = tc.beta(w, i, j, k, t)
                if not bw:
                    continue
                for s in range(min(i, j) + 1):
                    if not tc.possible(w, v, i, j, t, s):
                        continue
                    bv = tc.beta(v, i, j, l, s)
                    if not bv:
                        continue
                    c = float(bw * bv) * diag[a] * diag[b] if normalize else bw * bv
                    yv = _val(yvar, d, t, s, i, j)
                    y0 = _val(yvar, d, 0, 0, i + j - t - s, 0)
                    mk = mk + c * yv
                    mpk = mpk + c * (y0 - yv)
            M[a][b] = mk
            Mp[a][b] = mpk
    return M, Mp, diag


def build_labeled(n, d, w, normalize=False):
    """The Section-III primal with LABELED constraint handles (the cert leg reads each dual):
      psd_h[((k,l),'M')] / psd_h[((k,l),'Mp')] -> the two block-family PSD constraints
      i_h                                       -> the y^{0,0}_{0,0}=1 equality (dual = ν)
      ii_h[('a'|'b1'|'g', t,s,i,j)]             -> the three (65)(ii) inequality families
      scale_h[(k,l)] = {'diag': …}              -> block scaling; unnormalized dual = diag·Z̃·diag elementwise.
    Constraint families are enumerated over tc.valid_quads(w,v) in the SAME order as the dual/cert legs."""
    import cvxpy as cp
    assert d % 2 == 0, "constant-weight machinery is built for even d (A(n,2e-1,w) = A(n,2e,w))"
    v = n - w
    keys = tc.free_keys(w, v, d)
    yvar = {key: cp.Variable(name=f"y{ki}") for ki, key in enumerate(keys)}
    psd_h, ii_h, scale_h = {}, {}, {}
    cons = []
    for (k, l) in tc.block_pairs(w, v):  # noqa: E741
        M, Mp, diag = _block_exprs(w, v, d, k, l, yvar, normalize=normalize)
        cM, cMp = cp.bmat(M) >> 0, cp.bmat(Mp) >> 0
        psd_h[((k, l), "M")], psd_h[((k, l), "Mp")] = cM, cMp
        scale_h[(k, l)] = {"diag": diag}
        cons += [cM, cMp]
    i_h = yvar[((0, 0, 0), 0)] == 1                                        # (65)(i)
    cons.append(i_h)
    for (t, s, i, j) in tc.valid_quads(w, v):                              # (65)(ii), possible quads only
        yv = _val(yvar, d, t, s, i, j)
        y0i = _val(yvar, d, 0, 0, i, 0)
        y0j = _val(yvar, d, 0, 0, j, 0)
        ca, cb, cg = (yv >= 0), (yv <= y0i), (y0i + y0j <= 1 + yv)
        ii_h[("a", t, s, i, j)], ii_h[("b1", t, s, i, j)], ii_h[("g", t, s, i, j)] = ca, cb, cg
        cons += [ca, cb, cg]
    obj = sum(tc.obj_coeff(key, w, v) * yvar[key] for key in keys)         # (67)
    prob = cp.Problem(cp.Maximize(obj), cons)
    return {"prob": prob, "yvar": yvar, "psd_h": psd_h, "i_h": i_h, "ii_h": ii_h, "scale_h": scale_h,
            "keys": keys, "w": w, "v": v}


def solve_primal(n, d, w, solver=None, normalize=None, solver_opts=None):
    """Solve the primal. solver=None auto-picks SDPA-GMP (tight, normalized) when sdpap is installed, else
    CLARABEL raw — the banked pairing (terwilliger_sdp._solver_defaults)."""
    import cvxpy as cp
    solver, normalize, solver_opts = ts._solver_defaults(solver, normalize, solver_opts)
    H = build_labeled(n, d, w, normalize=normalize)
    H["prob"].solve(solver=getattr(cp, solver), **solver_opts)
    return {"status": H["prob"].status,
            "value": (None if H["prob"].value is None else float(H["prob"].value)),
            "H": H, "solver": solver, "normalized": normalize}


def run_numerical(n, d, w, solver=None, normalize=None):
    """One cell: solve, floor, compare against Table II (faithfulness) and LOWER (soundness)."""
    full = solve_primal(n, d, w, solver=solver, normalize=normalize)
    row = {"n": n, "d": d, "w": w, "status": full["status"], "solver": full["solver"],
           "n_vars": len(full["H"]["keys"]),
           "sdp_value": None if full["value"] is None else round(full["value"], 4),
           "sdp_floor": None if full["value"] is None else int(full["value"] + 1e-6)}
    if (n, d, w) in TABLE_II:
        row["table_II"] = TABLE_II[(n, d, w)]
        row["reproduces_table_II"] = (row["sdp_floor"] == TABLE_II[(n, d, w)])
    if (n, d, w) in DELSARTE_COL and row["sdp_value"] is not None:
        row["delsarte_col"] = DELSARTE_COL[(n, d, w)]
        row["sdp_le_delsarte"] = row["sdp_value"] <= DELSARTE_COL[(n, d, w)] + 1e-3
    if (n, d, w) in LOWER and row["sdp_floor"] is not None:
        # SOUNDNESS: a valid upper bound never floors below a known lower bound on A(n,d,w).
        row["lower"] = LOWER[(n, d, w)]
        row["valid_bound"] = row["sdp_floor"] >= LOWER[(n, d, w)]
    return row


def main() -> int:
    # small cells (plumbing: d=2 ⇒ whole Johnson space; d=4 Steiner cells) + the Table II gate cells
    small = [(4, 2, 2), (5, 2, 2), (6, 2, 3), (6, 4, 3), (7, 4, 3), (8, 4, 4), (9, 4, 3)]
    gate = [(17, 6, 7), (18, 6, 6), (17, 6, 8)]
    rows = []
    for (n, d, w) in small + gate:
        try:
            rows.append(run_numerical(n, d, w))
        except Exception as e:  # noqa: BLE001 -- report, don't crash the sweep
            rows.append({"n": n, "d": d, "w": w, "status": f"error: {type(e).__name__}: {e}"})

    repro = [r for r in rows if r.get("reproduces_table_II")]
    table_cells = [r for r in rows if "reproduces_table_II" in r]
    valid = [r for r in rows if r.get("valid_bound")]
    checked = [r for r in rows if "valid_bound" in r]
    verdict = ("GREEN" if table_cells and len(repro) == len(table_cells)
               and len(valid) == len(checked) else "AMBER")
    res = {"verdict": verdict, "reproduced_table_II": f"{len(repro)}/{len(table_cells)}",
           "valid_bounds": f"{len(valid)}/{len(checked)}", "rows": rows,
           "reading": ("D1 step 2, the formulation-faithfulness gate. GREEN = the constant-weight SDP optimum "
                       "floors to Schrijver Table II on every gate cell AND never floors below a known lower "
                       "bound on A(n,d,w) -> the Section-III transcription is FAITHFUL (the exact analogue of "
                       "the unrestricted build's (19,6)/(20,8) gate). Floats are indicative only; "
                       "certification is the exact + kernel legs (terwilliger_cwc_cert.py).")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"terwilliger cwc SDP (faithfulness gate): {verdict}")
    for r in rows:
        extra = ""
        if "table_II" in r:
            extra = f" tableII={r['table_II']} repro={r.get('reproduces_table_II')}"
        if "lower" in r:
            extra += f" lower={r['lower']} valid={r.get('valid_bound')}"
        print(f"  A({r['n']},{r['d']},{r['w']}): status={r.get('status')} sdp={r.get('sdp_value')} "
              f"floor={r.get('sdp_floor')} vars={r.get('n_vars')}{extra}")
    print(f"  reproduced Table II: {res['reproduced_table_II']}; sound: {res['valid_bounds']}")
    print(f"  -> {OUT}")
    return 0 if verdict == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())

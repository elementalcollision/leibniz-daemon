"""Terwilliger solve-leg fix (roadmap D6 / Q-pit-2) — the measured verdict harness (operator-local).

The task #99 reach probe measured the binding constraint of the three-point pipeline: the float solve leg
(CLARABEL crash onset ~4600 free vars at (23,6); SCS under-convergence up to ~88x; every d>=10 cell with
n>=20 failing both solvers; chaotic k_max-bisect scatter at (22,10)). This harness measures the fix:

  1. Schrijver's own eq.(8) block normalization restored FOR THE FLOAT SOLVE ONLY (terwilliger_sdp._block_exprs;
     an exact PSD-equivalence — positive diagonal congruence — so the feasible set is untouched), and
  2. the SDPA-GMP high-precision backend (pip install sdpa-multiprecision) at measured-tight settings
     (terwilliger_sdp.SDPA_TIGHT).

Every solve is AUDITED: the returned primal x is checked against the EXACT integer-beta blocks (numpy
eigenvalues of the exactly-rebuilt, congruence-scaled blocks) and the exact linear constraints. The audit is a
VIOLATION PROFILE, not a bound: this session measured, at (22,10), a float point auditing at −7e-19 block
eigenvalue / 2.7e-10 linear violation whose objective (88.63) sits 0.38 ABOVE the exact-rational dual
certificate (88.2469, certify_lp, dual_check-validated) — the certificate's 1.5e9-scale multipliers monetize
1e-10 violations, so NO float-side quantity here is trusted as a bound in either direction. The independent
exact-arithmetic Delsarte LP (Krawtchouk + HiGHS) anchors the k=0 top; certification stays with
terwilliger_exact_lp.certify_lp + the kernel.

Needs cvxpy + numpy + sdpap (all operator-local, find_spec-gated; CI skips clean). No trust surface touched.
"""
from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "terwilliger_solve_leg.json"

HAVE = all(importlib.util.find_spec(m) is not None for m in ("cvxpy", "numpy", "sdpap"))


def _load(mod, rel):
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


td = _load("terwilliger_dual", "scripts/terwilliger_dual.py")
ts = _load("terwilliger_sdp", "scripts/terwilliger_sdp.py")

# Suite: regression cells (must keep flooring to Table I), the reach-probe crash cell (23,6), the d>=10
# validation trio, the d=12 exact-value anchor, and the two pre-SDP-ub frontier cells from the probe.
CELLS = [
    (19, 6, {"table_I": 1280}),
    (20, 8, {"table_I": 274}),
    (23, 6, {"table_I": 13766}),          # reach-probe CLARABEL crash onset (~4600 free vars)
    (22, 10, {"table_I": 87}),            # d>=10 faithfulness: the k_max-bisect chaos cell
    (25, 10, {"table_I": 503}),
    (26, 10, {"table_I": 886}),
    (21, 12, {"exact_A": 8}),             # probe diagnostic anchor (both solvers collapsed here)
    (27, 12, {"published_ub": 169}),      # frontier: published ub is pre-SDP (AVZ 2001)
    (28, 12, {"published_ub": 288}),
]


def delsarte_exact_float(n, d):
    """Independent Delsarte LP anchor (Krawtchouk, scipy HiGHS): NOT part of the SDP build under test."""
    from math import comb

    from scipy.optimize import linprog

    def K(k, i):
        return sum((-1) ** j * comb(i, j) * comb(n - i, k - j) for j in range(min(i, k) + 1))

    dists = [i for i in range(d, n + 1)]
    res = linprog([-1.0] * len(dists),
                  A_ub=[[-float(K(k, i)) for i in dists] for k in range(n + 1)],
                  b_ub=[float(K(k, 0)) for k in range(n + 1)],
                  bounds=[(0, None)] * len(dists), method="highs")
    return None if not res.success else 1 - res.fun


def audit_point(n, d, xv):
    """Check a solver's x against the EXACT integer-beta constraint set (floats only enter via the final
    numpy eigenvalue call on the congruence-scaled block). Returns the violation profile of the returned
    point. NOT a bound: at this problem's conditioning, exact dual certificates carry ~1e9-scale multipliers,
    so even 1e-10 violations can hide tenths of objective (measured at (22,10) — see module docstring)."""
    from math import sqrt

    import numpy as np

    def val(t, i, j):
        key = td.canon(t, i, j)
        return xv.get(key, 0.0) if td.classify(key, d) == "free" else 0.0

    obj = sum(td.obj_coeff(k, n) * v for k, v in xv.items())
    worst_lin = 0.0
    for (t, i, j) in td.valid_triples(n):
        x, x0i, x0j = val(t, i, j), val(0, i, 0), val(0, j, 0)
        worst_lin = max(worst_lin, -x, x - x0i, x0i + x0j - 1 - x)
    worst_eig, worst_blk = 0.0, None
    for k in range(n // 2 + 1):
        idx = td.block_idx(n, k)
        dg = [1.0 / sqrt(td.C(n - 2 * k, i - k)) for i in idx]
        M = np.zeros((len(idx), len(idx)))
        Mp = np.zeros_like(M)
        for a, i in enumerate(idx):
            for b, j in enumerate(idx):
                for t in range(min(i, j) + 1):
                    s = i + j - 2 * t
                    if not td.possible(n, i, j, t):
                        continue
                    bijk = td.beta(n, i, j, k, t)
                    if not bijk:
                        continue
                    c = float(bijk) * dg[a] * dg[b]
                    M[a, b] += c * val(t, i, j)
                    Mp[a, b] += c * (val(0, s, 0) - val(t, i, j))
        for name, B in (("M", M), ("Mp", Mp)):
            mn = float(np.linalg.eigvalsh((B + B.T) / 2).min())
            if mn < worst_eig:
                worst_eig, worst_blk = mn, f"k={k} {name}"
    return {"audited_objective": round(obj, 6), "worst_lin_violation": worst_lin,
            "worst_block_eig": worst_eig, "worst_block": worst_blk,
            "x000_dev": abs(xv.get((0, 0, 0), 0.0) - 1.0)}


def run_cell(n, d, anchors, time_note=True):
    row = {"n": n, "d": d, **anchors}
    t0 = time.time()
    try:
        r = ts.solve_primal(n, d)                      # auto: SDPA-GMP tight + eq.(8) normalization
        row["status"] = r["status"]
        row["solver"] = r["solver"]
        row["sdp_value"] = None if r["value"] is None else round(r["value"], 6)
        row["sdp_floor"] = None if r["value"] is None else int(r["value"] + 1e-6)
        xv = {k: float(v.value) for k, v in r["xvar"].items() if v.value is not None}
        if xv:
            row["audit"] = audit_point(n, d, xv)
    except Exception as e:  # noqa: BLE001 -- record, don't crash the sweep
        row["status"] = f"error: {type(e).__name__}: {e}"
    if time_note:
        row["secs"] = round(time.time() - t0, 1)
    dl = delsarte_exact_float(n, d)
    row["delsarte_lp"] = None if dl is None else round(dl, 4)
    if "table_I" in anchors and row.get("sdp_floor") is not None:
        row["reproduces_table_I"] = row["sdp_floor"] == anchors["table_I"]
    if "exact_A" in anchors and row.get("sdp_floor") is not None:
        row["valid_bound"] = row["sdp_floor"] >= anchors["exact_A"]
    return row


def kmax_ladder(n, d, ks=(0, 1, 2, 3, None)):
    """The reach-probe k_max-bisect, re-run through the fixed leg: must be ~monotone non-increasing in k
    (more blocks = more constraints), replacing the probe's chaotic scatter."""
    out = []
    for k in ks:
        try:
            r = ts.solve_primal(n, d, k_max=k)
            out.append({"k_max": "full" if k is None else k, "status": r["status"],
                        "value": None if r["value"] is None else round(r["value"], 4)})
        except Exception as e:  # noqa: BLE001
            out.append({"k_max": "full" if k is None else k, "status": f"error: {type(e).__name__}"})
    return out


# Exact-rational escalation (certify_lp: rationalized SDPA dual -> exact simplex -> dual_check). Measured on
# the operator machine: (23,6) and (25,10) certify at P=1e14 (~50 s / ~20 s LP legs); (22,10) does NOT certify
# 87 at any tried precision — its best exact bound is ~88.246 (floor 88), which is the recorded anomaly.
ESCALATIONS = [
    (23, 6, 13766, (10 ** 14,)),
    (25, 10, 503, (10 ** 14,)),
    (22, 10, 87, (10 ** 10, 10 ** 14)),
]


def main() -> int:
    if not HAVE:
        print("terwilliger solve-leg: SKIP (needs operator-local cvxpy+numpy+sdpap; "
              "pip install cvxpy sdpa-multiprecision)")
        return 0
    rows = [run_cell(n, d, anchors) for (n, d, anchors) in CELLS]
    ladder = kmax_ladder(22, 10)

    tel = _load("terwilliger_exact_lp", "scripts/terwilliger_exact_lp.py")
    certs = []
    for (n, d, target, precs) in ESCALATIONS:
        try:
            c = tel.certify_lp(n, d, target=target, precisions=precs, time_cap_s=2400)
            certs.append({k: v for k, v in c.items() if k != "duals"})
        except Exception as e:  # noqa: BLE001
            certs.append({"n": n, "d": d, "target": target, "error": f"{type(e).__name__}: {e}"})

    repro = [r for r in rows if r.get("reproduces_table_I")]
    table_cells = [r for r in rows if "reproduces_table_I" in r]
    regression_ok = all(r.get("reproduces_table_I") for r in rows if (r["n"], r["d"]) in ((19, 6), (20, 8)))
    wall_ok = next(r.get("reproduces_table_I") for r in rows if (r["n"], r["d"]) == (23, 6))
    lv = [x["value"] for x in ladder if x["value"] is not None]
    ladder_monotone = all(a >= b - 1e-3 for a, b in zip(lv, lv[1:]))
    certified = [c for c in certs if c.get("certified")]
    verdict = "GREEN" if regression_ok and wall_ok else "RED"
    res = {
        "verdict": verdict,
        "fix": "eq.(8) block normalization (exact PSD-equivalence, float leg only) + SDPA-GMP backend "
               "(sdpa-multiprecision) at SDPA_TIGHT settings",
        "regression_ok": regression_ok, "crash_cell_23_6_ok": wall_ok,
        "reproduced_table_I": f"{len(repro)}/{len(table_cells)}",
        "kmax_ladder_22_10": ladder, "kmax_ladder_monotone": ladder_monotone,
        "exact_certificates": certs, "exact_certified": f"{len(certified)}/{len(certs)}",
        "rows": rows,
        "reading": (
            "D6/Q-pit-2 solve-leg fix, measured. GREEN = the regression cells still floor to Table I "
            "(A(19,6)->1280, A(20,8)->274, now at true 'optimal' status) AND the reach-probe crash cell "
            "(23,6) returns a stable optimal near Schrijver's 13766. The audit fields are the returned "
            "point's violation profile, NOT bounds (measured at (22,10): a -7e-19/2.7e-10 audit still sat "
            "0.38 above the exact dual certificate; 1.5e9-scale multipliers monetize 1e-10 violations). "
            "exact_certificates is the certify_lp escalation through the SDPA dual: A(23,6) <= 13766 and "
            "the first d>=10 exact cert A(25,10) <= 503 both CERTIFIED (dual_check-validated, "
            "kernel-renderable); (22,10) does NOT certify Table I's 87 - best exact bound ~88.246, floor "
            "88, while floats stall on BOTH sides of it (87.97 under-solves, 88.63 pseudo-feasible) - "
            "eq.(25) caps are provably inactive at the relevant points, so whether the transcribed SDP's "
            "optimum floors to 87 is OPEN (decidable only exactly; see the results doc). (26,10) still "
            "stalls (structural, precision-independent). Floats stay indicative only - certification is "
            "certify_lp + kernel."),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"terwilliger solve-leg (D6/Q-pit-2): {verdict}")
    for r in rows:
        a = r.get("audit", {})
        print(f"  A({r['n']},{r['d']}): status={r['status']} value={r.get('sdp_value')} "
              f"floor={r.get('sdp_floor')} delsarte={r.get('delsarte_lp')} "
              f"anchors={ {k: v for k, v in r.items() if k in ('table_I', 'exact_A', 'published_ub')} } "
              f"repro={r.get('reproduces_table_I', '-')} eig={a.get('worst_block_eig', '-')} secs={r.get('secs')}")
    print(f"  k_max ladder (22,10): {[(x['k_max'], x['value']) for x in ladder]} monotone={ladder_monotone}")
    for c in certs:
        print(f"  exact cert A({c['n']},{c['d']}): target={c.get('target')} bound={c.get('exact_bound')} "
              f"floor={c.get('floor')} certified={c.get('certified')} P={c.get('P')} secs={c.get('secs')}")
    print(f"  -> {OUT}")
    return 0 if verdict == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())

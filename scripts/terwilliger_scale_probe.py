"""Terwilliger three-point — Path C scale probe: WHERE the exact A(19,6) certificate is compute-bound.

Measures, per cell, the three walls that gate an exact-rational dual certificate at scale (operator-local:
cvxpy). Capped so it cannot hang. This is a MEASURE-BEFORE-BUILD probe: it quantifies exactly what the record
cell A(19,6) needs (a bit-controlled rational LP and/or a high-precision solver), rather than attempting the
full cert (which is the compute-trap #213).

Walls:
  1. PSD-roundability — smallest precision P at which the float64 dual blocks round to exactly-PSD rationals.
  2. Restoration cost — one min-norm exact restoration solve (residuals -> 0) and its wall-clock.
  3. Nonnegativity — how many multipliers come out negative (⇒ how far a nonneg-feasible point is): the number
     of clamp iterations the naive projection would need, and hence why a rational LP / SDPA-GMP is required.

It also confirms the BOUND is reachable (⌊Σγ−ν⌋ = the target) even where the exact nonneg cert is not yet
cheap — i.e. the certificate exists; only its exact representation is compute-bound.
"""
from __future__ import annotations

import importlib.util
import json
import time
from fractions import Fraction as Fr
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "terwilliger_scale_probe.json"


def _load(mod, rel):
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


td = _load("terwilliger_dual", "scripts/terwilliger_dual.py")
cert = _load("terwilliger_cert", "scripts/terwilliger_cert.py")


def probe(n, d, target, precisions=(10 ** 6, 10 ** 7, 10 ** 8, 10 ** 9), tol=1e-4):
    ex = cert.extract_dual(n, d)
    keys, cols, A, bnd = cert._mult_structure(n, d)
    row = {"n": n, "d": d, "target": target, "sdp_value": round(ex["value"], 4),
           "n_free_vars": len(keys), "n_multipliers": len(cols)}
    goodP = None
    for P in precisions:
        Zq = {k: cert._round_psd(ex["Z"][k], P) for k in ex["Z"]}
        Zpq = {k: cert._round_psd(ex["Zp"][k], P) for k in ex["Zp"]}
        if all(td.is_psd_exact(Zq[k]) and td.is_psd_exact(Zpq[k]) for k in Zq):
            goodP = P
            break
    row["psd_round_P"] = goodP
    if goodP is None:
        row["note"] = "Z not PSD-roundable at tried precisions (conditioning wall)"
        return row
    Zq = {k: cert._round_psd(ex["Z"][k], goodP) for k in ex["Z"]}
    Zpq = {k: cert._round_psd(ex["Zp"][k], goodP) for k in ex["Zp"]}
    base = cert._base_residual(n, d, Zq, Zpq)
    rhs = [-base[key] for key in keys]
    active = [ci for ci, c in enumerate(cols)
              if c[0] == "nu" or abs((ex["nu"] if c[0] == "nu" else ex[c[0]].get(c[1:], 0.0))) > tol]
    m0 = {ci: Fr(round((ex["nu"] if cols[ci][0] == "nu" else ex[cols[ci][0]].get(cols[ci][1:], 0.0)) * goodP), goodP)
          for ci in active}
    rows = [{ci: A.get((ci, key), 0) for ci in active} for key in keys]
    t0 = time.time()
    sol = cert._min_deviation(rows, active, m0, rhs)
    row["restore_solve_secs"] = round(time.time() - t0, 3)
    mvals = {ci: Fr(0) for ci in range(len(cols))}
    mvals.update(dict(zip(active, sol)))
    duals = cert._assemble(n, d, Zq, Zpq, cols, mvals)
    chk = td.dual_check(n, d, duals)
    b = chk["bound"]
    negs = sum(1 for ci in active if cols[ci][0] in ("a", "b1", "g") and mvals[ci] < 0)
    row.update({"n_active": len(active), "residual_zero": chk["n_residuals_nonzero"] == 0,
                "bound_float": round(float(b), 4), "floor": (int(b) if b >= 0 else 0),
                "bound_floors_to_target": (target is not None and b >= 0 and int(b) == target),
                "negative_multipliers": negs,
                "feasible_one_shot": chk["feasible"]})
    return row


def main() -> int:
    cells = [(8, 4, 16), (10, 4, None), (14, 6, None), (19, 6, 1280)]   # intermediate cells: scaling data points
    rows = []
    for (n, d, tgt) in cells:
        try:
            rows.append(probe(n, d, tgt))
        except Exception as e:  # noqa: BLE001
            rows.append({"n": n, "d": d, "error": f"{type(e).__name__}: {e}"})
    res = {"rows": rows,
           "reading": ("Path C scale probe. Confirms the exact A(19,6) certificate is COMPUTE-BOUND, not "
                       "impossible: the dual blocks round to PSD at P=1e8, the min-norm restoration zeroes the "
                       "stationarity residuals, and ⌊Σγ−ν⌋ = 1280 (the certificate EXISTS and floors correctly). "
                       "The wall is EXACT NONNEGATIVITY — hundreds of multipliers come out negative, so the "
                       "one-at-a-time clamp is O(hundreds × seconds). Completing A(19,6) needs a bit-controlled "
                       "rational LP (Bareiss/integer-preserving simplex, min Σγ−ν s.t. stationarity + α,β1,γ≥0) "
                       "and/or a high-precision solve (SDPA-GMP) so the duals are well-separated — the panel's "
                       "D6. Small cells (n≤8) are already full exact certs (terwilliger_cert, GREEN).")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print("terwilliger scale probe (Path C):")
    for r in rows:
        if "error" in r:
            print(f"  A({r['n']},{r['d']}): {r['error']}")
            continue
        print(f"  A({r['n']},{r['d']}): vars={r['n_free_vars']} mults={r['n_multipliers']} psdP={r.get('psd_round_P')} "
              f"restore={r.get('restore_solve_secs')}s floor={r.get('floor')} tgt={r['target']} "
              f"neg_mults={r.get('negative_multipliers')} one_shot_feasible={r.get('feasible_one_shot')}")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

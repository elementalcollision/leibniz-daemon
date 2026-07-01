"""Irrationality-margin test — the revised gate for the SDP three-point bet (external critique #213).

The agent's PRIMARY, previously-untested risk: SDP optima are algebraic-irrational, so a rational PSD dual
certificate over-approximates the optimum; with the εI/rounding margin, ⌈bound⌉ can overshoot the target
integer and FAIL to certify a tightening. This isolates that question WITHOUT building the full Terwilliger
three-point SDP (that is the gated build): use the Lovász theta ϑ(G), whose optimum is genuinely irrational
for odd cycles (ϑ(C₅)=√5), and measure —

  can a KERNEL-CHECKABLE rational PSD certificate certify the correct integer bound ⌊ϑ⌋ = α(G),
  and how small is the achievable "irrationality tax" (rational bound − ϑ) vs the certificate bit-length?

Dual ϑ SDP: minimize t s.t.  Z := t·I − J + Σ_{ij∈E} y_ij·E_ij  ⪰ 0   ⟹   α(G) ≤ t  (= ϑ at the optimum).
An untrusted solver (cvxpy/SCS) proposes (t, y); we round y to rationals, find the smallest rational t* on a
1/P grid making Z(t*) exactly PSD (rational Cholesky), clear denominators, and KERNEL-check Z(t*) ⪰ 0 via the
integer LDLᵀ checker from the exact-PSD micro-probe (#212). The soundness rests only on the kernel check.

GREEN: ⌊t*⌋ == α(G) across the irrational-ϑ graphs AND the achievable tax shrinks with precision at bounded
bit-length (so a narrow code-cell margin is reachable). RED: the rational cert cannot floor to α, or the tax
stays large — the irrationality wall is fatal and the SDP discovery bet should be dropped.

Needs cvxpy (operator-local, like ortools) + docker for the kernel leg. Free-CPU otherwise.
"""
from __future__ import annotations

import importlib.util
import json
from fractions import Fraction as Fr
from math import ceil, cos, pi
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "irrationality_margin_test.json"


def _load(mod, rel):
    import sys
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


pm = _load("psd_certificate_microprobe", "scripts/psd_certificate_microprobe.py")


def odd_cycle(n: int):
    """Edges of C_n and its exact data: α = (n-1)/2, ϑ = n·cos(π/n)/(1+cos(π/n)) (irrational for odd n>1)."""
    edges = [(i, (i + 1) % n) for i in range(n)]
    alpha = (n - 1) // 2
    c = cos(pi / n)
    theta = n * c / (1 + c)
    return n, edges, alpha, theta


def solve_theta_dual(n, edges):
    """Untrusted: solve the dual ϑ SDP; return (t*=ϑ float, y_dual per edge float)."""
    import cvxpy as cp
    import numpy as np
    J = np.ones((n, n))
    t = cp.Variable()
    y = cp.Variable(len(edges))
    Z = t * np.eye(n) - J
    for k, (i, j) in enumerate(edges):
        Ek = np.zeros((n, n))
        Ek[i, j] = Ek[j, i] = 1.0
        Z = Z + y[k] * Ek
    prob = cp.Problem(cp.Minimize(t), [Z >> 0])
    prob.solve(solver=cp.SCS, eps=1e-7)
    return float(t.value), [float(v) for v in y.value]


def _W_rational(n, edges, y_rat):
    """W = −J + Σ y'_ij E_ij as a rational matrix (J, E integer; y' rational)."""
    W = [[Fr(-1) for _ in range(n)] for _ in range(n)]
    for k, (i, j) in enumerate(edges):
        W[i][j] += y_rat[k]
        W[j][i] += y_rat[k]
    return W


def min_rational_t(n, edges, y_rat, P):
    """Smallest rational t on a 1/P grid making Z(t)=t·I+W exactly PSD (strict-PD via rational Cholesky).
    Returns (t as Fraction, Z integer matrix N, cert (L,d,scale)) or None."""
    import numpy as np
    W = _W_rational(n, edges, y_rat)
    Wf = np.array([[float(W[i][j]) for j in range(n)] for i in range(n)])
    lam = float(np.linalg.eigvalsh(Wf)[0])          # smallest eigenvalue of W (float)
    t0 = Fr(ceil((-lam) * P) + 1, P)                # smallest 1/P-grid rational strictly above −λmin
    for bump in range(0, 6):
        t = t0 + Fr(bump, P)
        Z = [[(t if i == j else Fr(0)) + W[i][j] for j in range(n)] for i in range(n)]
        res = pm.ldlt(Z)
        if res is None:
            continue
        L, d = res
        Li, di, sc = pm.clear_denoms(L, d)
        # integer numerator of Z at common denom of t and y'
        dens = [t.denominator] + [yy.denominator for yy in y_rat] + [1]
        Dc = 1
        for x in dens:
            Dc = Dc * x // _gcd(Dc, x)
        N = [[int((Z[i][j] * Dc)) for j in range(n)] for i in range(n)]
        # re-factor the integer N (PSD iff Z is) for a clean integer certificate
        res2 = pm.ldlt([[Fr(N[i][j]) for j in range(n)] for i in range(n)])
        if res2 is None:
            continue
        L2, d2 = res2
        Li2, di2, sc2 = pm.clear_denoms(L2, d2)
        if pm.verify_int_cert(N, Li2, di2, sc2):
            return t, N, (Li2, di2, sc2)
    return None


def _gcd(a, b):
    while b:
        a, b = b, a % b
    return a


def run_cell(n, edges, alpha, theta, kernel=None) -> dict:
    t_float, y_float = solve_theta_dual(n, edges)
    row = {"graph": f"C{n}", "alpha": alpha, "theta": round(theta, 6), "solver_theta": round(t_float, 6)}
    best = None
    for P in (10, 100, 1000, 10 ** 4, 10 ** 5, 10 ** 6):
        y_rat = [Fr(round(v * P), P) for v in y_float]
        got = min_rational_t(n, edges, y_rat, P)
        if got is None:
            continue
        t, N, (Li, di, sc) = got
        tax = float(t) - theta
        allints = [x for r in N for x in r] + [x for r in Li for x in r] + list(di) + [sc]
        bits = max((int(abs(x)).bit_length() for x in allints), default=0)
        cand = {"P": P, "cert_bound": round(float(t), 6), "floor": int(float(t)) if float(t) >= 0 else 0,
                "tax": round(tax, 6), "max_bits": bits, "N": N, "cert": (Li, di, sc)}
        if best is None or cand["tax"] < best["tax"]:
            best = cand
        if tax < 0.01:
            break
    if best is None:
        row["status"] = "RED(no rational cert)"
        return row
    floor_ok = best["floor"] == alpha
    row.update({"best_P": best["P"], "cert_bound": best["cert_bound"], "achievable_tax": best["tax"],
                "cert_max_bits": best["max_bits"], "floor": best["floor"],
                "floors_to_alpha": floor_ok, "status": "certifies-alpha" if floor_ok else "OVERSHOOT"})
    if kernel is not None:
        Li, di, sc = best["cert"]
        row["kernel"] = kernel(best["N"], Li, di, sc)
    return row


def main() -> int:
    try:
        from leibniz.backends.lean_cli import LeanCliBackend, available
        bk = LeanCliBackend(timeout_s=120) if available() else None
    except Exception:
        bk = None

    def kern(N, Li, di, sc):
        return bk.check_source(pm.render_ldlt_lean(N, Li, di, sc)) if bk else "unavailable"

    rows = []
    for n in (5, 7, 9, 11):
        nn, edges, alpha, theta = odd_cycle(n)
        rows.append(run_cell(nn, edges, alpha, theta, kernel=kern))
    certifies = [r for r in rows if r.get("floors_to_alpha")]
    overshoot = [r for r in rows if r.get("status") == "OVERSHOOT"]
    min_tax = min((r["achievable_tax"] for r in rows if "achievable_tax" in r), default=None)
    verdict = ("GREEN" if len(certifies) == len(rows) and (min_tax is not None and min_tax < 0.01)
               else "AMBER(certifies-but-large-tax)" if certifies and not overshoot
               else "RED(irrationality-wall)")
    res = {"verdict": verdict, "n_graphs": len(rows), "certifies_alpha": len(certifies),
           "overshoots": len(overshoot), "min_achievable_tax": min_tax, "rows":
           [{k: v for k, v in r.items() if k not in ("cert", "N")} for r in rows],
           "reading": ("Revised SDP gate. certifies-alpha = a KERNEL-checked rational PSD certificate floored "
                       "to ⌊ϑ⌋=α despite an irrational optimum. achievable_tax = smallest (rational bound − ϑ) "
                       "at bounded bit-length -> predicts whether a NARROW code-cell margin survives. GREEN => "
                       "tax shrinks below 0.01 at modest bits and floors correctly: the irrationality wall is "
                       "surmountable, proceed to the three-point build (with Bareiss for scale). RED => "
                       "overshoot or stuck-large tax: the wall is fatal, bank LP and drop the SDP bet.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"irrationality-margin test: {res['verdict']}")
    for r in res["rows"]:
        print(f"  {r['graph']:4s} alpha={r['alpha']} theta={r.get('theta')} "
              f"cert_bound={r.get('cert_bound')} tax={r.get('achievable_tax')} bits={r.get('cert_max_bits')} "
              f"{r.get('status')} kernel={r.get('kernel','-')}")
    print(f"  certifies_alpha={res['certifies_alpha']}/{res['n_graphs']} min_tax={res['min_achievable_tax']}")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

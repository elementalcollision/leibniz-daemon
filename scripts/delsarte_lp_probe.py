"""P1 — Delsarte LP dual-certificate probe (post-scout certificate-architecture pivot, measure-before-build).

The novelty-frontier scout killed positive-witness table-BEATING. The external panel's convergent escape:
verify a SMALL certificate from an untrusted solver for the UPPER-bound band. This probe tests the make-or-
break leg of that pivot for unrestricted binary codes A(n,d) (Hamming scheme, Krawtchouk polynomials):

  untrusted LP solver (ortools GLOP, float)  -->  a dual polynomial f = 1 + Σ_{k>=1} f_k K_k
      -->  ROUND to an EXACT INTEGER certificate (q; p_1..p_n),  f_k = p_k/q
      -->  verify with exact integer arithmetic (the SOUND leg; later the kernel):
             p_k >= 0, q > 0, and  q + Σ_k p_k K_k(i) <= 0  for i = d..n
      -->  bound  A(n,d) <= floor( (q + Σ_k p_k K_k(0)) / q ),  K_k(0) = C(n,k)

Delsarte's theorem: any such f with f_k >= 0 and f(i) <= 0 for i in [d,n] proves A(n,d) <= f(0). The LP
solver is UNTRUSTED (it only proposes f); soundness rests entirely on the exact integer re-check, which is
tiny and kernel-decidable (no exponential decide, no maxRecDepth — clearing denominators keeps it integer).

GREEN: for >=1 cell, an exact integer certificate verifies AND its bound reproduces (==) or tightens (<) the
known value. RED: float->rational rounding cannot yield a valid exact certificate (the fragility the panel
flagged). This probe DECIDES whether the negative-certificate pivot is mechanically feasible before any build.

Free-CPU (ortools). No trust touch; never promulgates.
"""
from __future__ import annotations

import json
from fractions import Fraction
from math import comb, floor, prod  # noqa: F401
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "delsarte_lp_probe.json"

# Rock-solid known A(n,d) values (standard binary-code tables). A VERIFIED Delsarte certificate is always a
# valid UPPER bound, so cert_bound < KNOWN[cell] is mathematically impossible for a sound cert -> it flags
# the KNOWN entry as wrong (an oracle error), NOT a discovery. (This is exactly the panel's oracle-wall
# warning; the first draft had KNOWN[(9,5)]=12, a typo for A(10,5)=12 — the cert correctly gave A(9,5)=6.)
KNOWN = {(5, 3): 4, (6, 3): 8, (7, 3): 16, (6, 4): 4, (8, 4): 16,
         (8, 5): 4, (9, 5): 6, (10, 5): 12, (11, 5): 24}


def krawtchouk(k: int, i: int, n: int) -> int:
    """K_k(i) = Σ_{j=0}^{k} (-1)^j C(i,j) C(n-i, k-j) — exact integer."""
    return sum((-1) ** j * comb(i, j) * comb(n - i, k - j) for j in range(k + 1))


def solve_dual_lp(n: int, d: int, slack: float = 0.0):
    """Untrusted: find float f_k >= 0 minimizing f(0) = 1 + Σ f_k C(n,k) s.t. Σ f_k K_k(i) <= -1-slack for
    i=d..n. Returns (float f_1..f_n, float bound) or None."""
    from ortools.linear_solver import pywraplp
    s = pywraplp.Solver.CreateSolver("GLOP")
    if s is None:
        return None
    f = [s.NumVar(0.0, s.infinity(), f"f{k}") for k in range(1, n + 1)]  # f_1..f_n
    for i in range(d, n + 1):
        s.Add(sum(f[k - 1] * krawtchouk(k, i, n) for k in range(1, n + 1)) <= -1.0 - slack)
    s.Minimize(sum(f[k - 1] * comb(n, k) for k in range(1, n + 1)))
    if s.Solve() != pywraplp.Solver.OPTIMAL:
        return None
    fk = [f[k - 1].solution_value() for k in range(1, n + 1)]
    bound = 1.0 + sum(fk[k - 1] * comb(n, k) for k in range(1, n + 1))
    return fk, bound


def verify_integer_cert(n: int, d: int, p: list[int], q: int) -> tuple[bool, int | None, list[str]]:
    """The SOUND leg (exact integers; kernel-checkable). p = [p_1..p_n], f_k = p_k/q. Returns
    (valid, bound, problems)."""
    probs = []
    if q <= 0:
        probs.append("q<=0")
    if any(pk < 0 for pk in p):
        probs.append("some p_k < 0")
    for i in range(d, n + 1):
        lhs = q + sum(p[k - 1] * krawtchouk(k, i, n) for k in range(1, n + 1))  # q*(1 + Σ f_k K_k(i))
        if lhs > 0:
            probs.append(f"f({i})>0: q+Σp_kK_k({i})={lhs}>0")
    if probs:
        return False, None, probs
    f0_num = q + sum(p[k - 1] * comb(n, k) for k in range(1, n + 1))   # q * f(0)
    return True, f0_num // q, []   # floor(f(0)) = floor(f0_num/q)


def rationalize_and_verify(n, d, fk, max_denom=(6, 12, 60, 360, 2520, 27720)):
    """Round the untrusted float f_k to an EXACT integer certificate and verify. Try increasing common
    denominators; accept the first that verifies. Rounds each f_k UP to its denominator grid so the
    (usually K_k(i)-dominated) constraints keep margin; reports the tightest verified bound."""
    best = None
    for D in max_denom:
        fr = [Fraction(x).limit_denominator(D) for x in fk]
        q = 1
        for x in fr:
            q = q * x.denominator // _gcd(q, x.denominator)
        p = [int(x * q) for x in fr]
        ok, bound, _ = verify_integer_cert(n, d, p, q)
        if not ok:
            # nudge each p_k up by one grid step and retry (adds margin to f(i)<=0 when K_k(i)<0 dominates)
            p2 = [pk + (q // D if D else 1) for pk in p]
            ok, bound, _ = verify_integer_cert(n, d, p2, q)
            p = p2
        if ok and (best is None or bound < best[1]):
            best = (p, bound, q, D)
    return best  # (p, bound, q, D) or None


def _gcd(a, b):
    while b:
        a, b = b, a % b
    return a


# Core-Lean (no Mathlib) checker: the kernel recomputes Krawtchouk itself (binomial via Pascal's rule),
# so a wrong K value cannot be smuggled in — exactly the covering-checker posture. `certOK = true` means
# the Delsarte dual conditions hold, i.e. A(n,d) <= f(0) by Delsarte's theorem (the bound-implication is a
# standard bridge lemma to formalize in a later slice, mirroring the pending validCovering->C<=B bridge).
_LEAN_HELPERS = """\
set_option maxRecDepth 10000
def cc : Nat -> Nat -> Nat
  | _, 0 => 1
  | 0, _+1 => 0
  | m+1, k+1 => cc m k + cc m (k+1)
def kraw (n k i : Nat) : Int :=
  (List.range (k+1)).foldl (fun acc j =>
    acc + (if j % 2 == 0 then (1:Int) else (-1)) * (cc i j : Int) * (cc (n-i) (k-j) : Int)) 0
def dot (n i : Nat) (p : List Int) : Int :=
  ((List.range n).zip p).foldl (fun s x => s + x.2 * kraw n (x.1 + 1) i) 0
def certOK (n d q : Nat) (p : List Int) : Bool :=
  (0 < q) && p.all (fun x => 0 <= x) &&
  (List.range (n - d + 1)).all (fun t => (q : Int) + dot n (d + t) p <= 0)"""


def render_cert_lean(n: int, d: int, q: int, p: list[int], bound: int) -> str:
    """Self-contained core-Lean theorem: the exact integer Delsarte dual certificate is VALID (certOK=true)
    => A(n,d) <= bound. The kernel recomputes Krawtchouk; the untrusted LP only proposed (q,p)."""
    plist = "[" + ", ".join(str(x) for x in p) + "]"
    return (f"{_LEAN_HELPERS}\n\ntheorem delsarte_A_{n}_{d}_le_{bound} :\n"
            f"    certOK {n} {d} {q} {plist} = true := by\n  decide\n")


def probe(cells=None) -> dict:
    cells = cells or list(KNOWN.keys())
    rows = []
    for (n, d) in cells:
        r = {"cell": f"A({n},{d})", "n": n, "d": d, "known": KNOWN.get((n, d))}
        sol = solve_dual_lp(n, d)
        if sol is None:
            r["status"] = "lp-infeasible"
            rows.append(r)
            continue
        fk, lp_bound = sol
        r["lp_bound_float"] = round(lp_bound, 3)
        cert = rationalize_and_verify(n, d, fk)
        if cert is None:
            r["status"] = "RED(rounding-failed)"
        else:
            p, bound, q, D = cert
            below = (r["known"] is not None and bound < r["known"])
            r.update({"cert_bound": bound, "q": q, "denom_grid": D,
                      "reproduces_known": (r["known"] is not None and bound == r["known"]),
                      # a verified cert is ALWAYS a valid upper bound; below-known => the KNOWN is wrong,
                      # not a discovery (oracle-suspect). Never reported as a beat from an unvetted table.
                      "oracle_suspect_below_known": below,
                      "status": "verified"})
        rows.append(r)
    verified = [r for r in rows if r.get("status") == "verified"]
    reproduced = [r for r in verified if r.get("reproduces_known")]
    suspect = [r for r in verified if r.get("oracle_suspect_below_known")]
    gate = ("GREEN" if reproduced else
            "AMBER(verified-but-no-known-match)" if verified else "RED(no-valid-cert)")
    return {"gate": gate, "n_cells": len(rows), "verified": len(verified),
            "reproduced": len(reproduced), "oracle_suspect": len(suspect), "rows": rows,
            "reading": ("P1 make-or-break for the certificate pivot. verified = an EXACT integer Delsarte "
                        "dual certificate passed the sound re-check (=> a provably valid A(n,d) upper bound); "
                        "reproduced = its bound == a rock-solid known value. oracle_suspect = cert strictly "
                        "below the hardcoded known (impossible for a sound cert => the KNOWN entry is wrong, "
                        "not a discovery). GREEN => the untrusted-LP -> exact-certificate pipeline is "
                        "mechanically feasible; proceed to the kernel-render leg + a REAL version-pinned "
                        "upper-bound oracle. RED => rational rounding too fragile; need an exact-rational LP.")}


def kernel_check_one(res: dict) -> dict:
    """Render the first reproduced certificate and check it on the real Lean kernel, plus a bogus-cert
    control (must be rejected). Records the verdicts. Needs docker; no-op (records 'unavailable') otherwise."""
    repro = next((r for r in res["rows"] if r.get("reproduces_known")), None)
    if repro is None:
        return {"status": "no reproduced cell to kernel-check"}
    n, d, q, bound = repro["n"], repro["d"], repro["q"], repro["cert_bound"]
    sol = solve_dual_lp(n, d)
    cert = rationalize_and_verify(n, d, sol[0]) if sol else None
    if cert is None:
        return {"status": "re-solve failed"}
    p = cert[0]
    try:
        from leibniz.backends.lean_cli import LeanCliBackend, available
        if not available():
            return {"status": "unavailable (no docker image)"}
        bk = LeanCliBackend(timeout_s=120)
        good = bk.check_source(render_cert_lean(n, d, q, p, bound))
        bogus = render_cert_lean(n, d, q, [0] * n, bound)   # all-zero cert must fail
        bad = bk.check_source(bogus)
        return {"status": "checked", "cell": repro["cell"], "valid_cert_kernel": good,
                "bogus_cert_kernel": bad, "sound": good is True and bad is False}
    except Exception as e:  # pragma: no cover
        return {"status": f"unavailable ({type(e).__name__})"}


def main() -> int:
    res = probe()
    res["kernel"] = kernel_check_one(res)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"Delsarte LP dual-certificate probe: {res['gate']}")
    for r in res["rows"]:
        extra = ""
        if r.get("status") == "verified":
            tag = ("REPRODUCES" if r.get("reproduces_known")
                   else "ORACLE-SUSPECT(known wrong)" if r.get("oracle_suspect_below_known")
                   else "valid-upper-bound")
            extra = f"cert_bound={r['cert_bound']} known={r['known']} {tag}"
        print(f"  {r['cell']:9s} {r.get('status',''):26s} {extra}")
    print(f"  verified={res['verified']} reproduced={res['reproduced']} oracle_suspect={res['oracle_suspect']}")
    k = res["kernel"]
    if k.get("status") == "checked":
        print(f"  kernel: {k['cell']} valid_cert={k['valid_cert_kernel']} bogus_cert={k['bogus_cert_kernel']} "
              f"-> {'SOUND end-to-end' if k['sound'] else 'ALARM'}")
    else:
        print(f"  kernel: {k.get('status')}")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

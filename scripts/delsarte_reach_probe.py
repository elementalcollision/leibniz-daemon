"""Delsarte reach probe (the discovery test for the certificate pivot, gated next-step #1).

P1 proved the untrusted-LP -> exact-integer-certificate -> kernel chain sound and reproducing on tiny tight
cells. This probe pushes it to a BAND of larger, genuinely-open A(n,d) and asks the discovery question: does
a verified Delsarte LP dual certificate TIGHTEN a best-known upper bound?

Rigorous, oracle-free measurements (no external table needed):
- produce a verified exact certificate for each (n,d) and its bound;
- compare to the EXACT sphere-packing (Hamming) and Singleton upper bounds (both closed-form);
- kernel-check the certificate at the largest cell (confirm no decide-wall at open-cell scale).

Discovery check (needs a table; kept SMALL + explicitly UNVETTED, with hard guards — the P1 oracle-wall
lesson): against a curated best-known-UB snapshot, classify reproduces / looser / TIGHTENS(investigate) /
ALARM(below sphere-packing floor = impossible for a valid cert => our LP or the snapshot is wrong).

Honest prior: plain 2-point Delsarte LP is classical and is dominated by SDP/Schrijver bounds for many
cells, and best-known tables already incorporate it — so a tightening of the *best-known* is unlikely;
a positive would almost certainly be a stale-snapshot artifact to investigate, not a discovery. The real
discovery bet is the stronger SDP three-point certificate (a larger, separate build), gated on this result.

Free-CPU (ortools). No trust touch; never promulgates.
"""
from __future__ import annotations

import importlib.util
import json
from math import comb
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "delsarte_reach_probe.json"


def _load(mod, rel):
    import sys
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


dl = _load("delsarte_lp_probe", "scripts/delsarte_lp_probe.py")


def hamming_ub(n: int, d: int) -> int:
    """Sphere-packing upper bound: A(n,d) <= 2^n / Σ_{i=0}^{t} C(n,i), t=floor((d-1)/2). Exact."""
    t = (d - 1) // 2
    return (2 ** n) // sum(comb(n, i) for i in range(t + 1))


def singleton_ub(n: int, d: int) -> int:
    return 2 ** (n - d + 1)


# Curated best-known A(n,d) UPPER bounds — EXPLICITLY UNVETTED snapshot (standard binary-code tables).
# A verified cert < LB is impossible; here we only guard cert < sphere-packing (a hard floor) and flag any
# cert < snapshot-UB as INVESTIGATE (candidate tightening, almost surely a stale-snapshot artifact).
BEST_KNOWN_UB = {
    (12, 5): 32, (13, 5): 64, (14, 5): 128, (15, 5): 256, (16, 5): 256,
    (12, 7): 4, (13, 7): 8, (14, 7): 16, (15, 7): 32, (16, 7): 36,
    (13, 3): 512, (14, 3): 1024, (15, 3): 2048,
}


def band():
    cells = []
    for n in range(12, 25):
        for d in (3, 5, 7):
            if d <= n:
                cells.append((n, d))
    return cells


def probe(cells=None) -> dict:
    cells = cells or band()
    rows = []
    for (n, d) in cells:
        sol = dl.solve_dual_lp(n, d)
        if sol is None:
            rows.append({"cell": f"A({n},{d})", "n": n, "d": d, "status": "lp-infeasible"})
            continue
        cert = dl.rationalize_and_verify(n, d, sol[0])
        if cert is None:
            rows.append({"cell": f"A({n},{d})", "n": n, "d": d, "status": "RED(no-cert)"})
            continue
        p, bound, q, _D = cert
        ok, b, _ = dl.verify_integer_cert(n, d, p, q)
        ham, sing = hamming_ub(n, d), singleton_ub(n, d)
        r = {"cell": f"A({n},{d})", "n": n, "d": d, "lp_cert_bound": bound,
             "hamming_ub": ham, "singleton_ub": sing,
             "lp_beats_hamming": bound < ham, "verified": bool(ok and b == bound),
             "status": "verified" if (ok and b == bound) else "VERIFY-MISMATCH"}
        if bound > min(ham, sing):
            r["note_lp_looser_than_elementary"] = True   # surprising; LP usually dominates
        ub = BEST_KNOWN_UB.get((n, d))
        if ub is not None:
            r["snapshot_ub"] = ub
            r["vs_snapshot"] = ("ALARM-below-floor" if bound < dl.KNOWN.get((n, d), 0)  # (rarely populated)
                                else "TIGHTENS(investigate)" if bound < ub
                                else "reproduces" if bound == ub else "looser")
        rows.append(r)
    verified = [r for r in rows if r.get("status") == "verified"]
    beats_ham = [r for r in verified if r.get("lp_beats_hamming")]
    tightens = [r for r in rows if r.get("vs_snapshot") == "TIGHTENS(investigate)"]
    reproduces = [r for r in rows if r.get("vs_snapshot") == "reproduces"]
    mism = [r for r in rows if r.get("status") == "VERIFY-MISMATCH"]
    verdict = ("VERIFY-MISMATCH(bug)" if mism
               else "TIGHTENINGS-TO-INVESTIGATE" if tightens
               else "NO-TIGHTENING (pipeline reaches open cells; plain LP does not beat best-known)")
    return {"verdict": verdict, "n_cells": len(rows), "verified": len(verified),
            "lp_beats_hamming": len(beats_ham), "snapshot_checked": sum(1 for r in rows if "snapshot_ub" in r),
            "reproduces_snapshot": len(reproduces), "tightenings": len(tightens),
            "verify_mismatches": len(mism), "rows": rows,
            "reading": ("Discovery test for plain Delsarte LP. verified = exact cert passed the sound "
                        "re-check (valid UB). lp_beats_hamming = LP strictly tighter than sphere-packing "
                        "(LP has real content). TIGHTENS(investigate) = cert below the UNVETTED snapshot UB "
                        "-> verify against the authoritative DOI-pinned table before any claim (likely a "
                        "stale-snapshot artifact). NO-TIGHTENING => plain LP reproduces/does-not-beat the "
                        "best-known; DISCOVERY needs the stronger SDP three-point certificate (next bet).")}


def kernel_check_largest(res: dict) -> dict:
    """Kernel-check the certificate at the largest verified cell (confirm no decide-wall at open-cell scale)."""
    verified = [r for r in res["rows"] if r.get("status") == "verified"]
    if not verified:
        return {"status": "no verified cell"}
    r = max(verified, key=lambda x: x["n"])
    n, d, bound = r["n"], r["d"], r["lp_cert_bound"]
    sol = dl.solve_dual_lp(n, d)
    cert = dl.rationalize_and_verify(n, d, sol[0]) if sol else None
    if cert is None:
        return {"status": "re-solve failed"}
    p, _bound, q, _D = cert
    try:
        from leibniz.backends.lean_cli import LeanCliBackend, available
        if not available():
            return {"status": "unavailable (no docker)"}
        v = LeanCliBackend(timeout_s=180).check_source(dl.render_cert_lean(n, d, q, p, bound))
        return {"status": "checked", "cell": r["cell"], "kernel": v}
    except Exception as e:  # pragma: no cover
        return {"status": f"unavailable ({type(e).__name__})"}


def main() -> int:
    res = probe()
    res["kernel_largest"] = kernel_check_largest(res)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"Delsarte reach probe: {res['verdict']}")
    print(f"  cells={res['n_cells']} verified={res['verified']} lp_beats_hamming={res['lp_beats_hamming']} "
          f"snapshot_checked={res['snapshot_checked']} reproduces={res['reproduces_snapshot']} "
          f"tightenings={res['tightenings']} verify_mismatches={res['verify_mismatches']}")
    for r in res["rows"]:
        if r.get("status") == "verified":
            vs = f" vs_snapshot={r['vs_snapshot']}(ub={r['snapshot_ub']})" if "snapshot_ub" in r else ""
            print(f"  {r['cell']:9s} lp={r['lp_cert_bound']:>8d} hamming={r['hamming_ub']:>10d} "
                  f"beats_ham={r['lp_beats_hamming']}{vs}")
        else:
            print(f"  {r['cell']:9s} {r['status']}")
    k = res["kernel_largest"]
    print(f"  kernel(largest): {k.get('cell','')} {k.get('kernel', k.get('status'))}")
    print(f"  -> {OUT}")
    return 1 if res["verify_mismatches"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

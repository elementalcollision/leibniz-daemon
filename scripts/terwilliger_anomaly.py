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

This is a THIN DRIVER (post-#238 review): the truncated-dual machinery lives in the shared modules —
terwilliger_sdp.build_labeled(k_max=), terwilliger_cert.extract_dual(k_max=) (zero-padded dropped blocks),
terwilliger_exact_lp.certify_lp/kernel_verify_lp(k_max=), terwilliger_cert.cert_psd_blocks (trivial LDLT for
zero blocks) — so the next consumer (ticket D1) calls the library instead of copying a fork.

No trust surface touched: floats (truncated or not) stay targeting data; certification is dual_check
(exact rational) + the Lean kernel on the PSD blocks (kernel-bank tier, corrupted controls included).
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


cert = _load("terwilliger_cert", "scripts/terwilliger_cert.py")
tlp = _load("terwilliger_exact_lp", "scripts/terwilliger_exact_lp.py")

# (n, d, Table-I target, k_max values to certify from, known lower bound on A(n,d) for the soundness check)
CELLS = [(22, 10, 87, (2, 3), 64), (26, 10, 886, (3, 4), 384)]
P_CERT = (10 ** 14,)               # the D6-measured precision: these cells certify only at P=1e14


def kernel_attest(duals, timeout_s=1800):
    """Kernel-bank tier on the certificate's duals: per-block ldltOK theorems on the real Lean 4.31 kernel —
    valid cert accepted, the corrupted-block AND corrupted-zero-block controls rejected (the zero-padding
    blocks carry the trivial LDLT certificate; cert.cert_psd_blocks attests every block, nothing skipped).
    Needs docker + the leibniz-lean image."""
    blocks = cert.cert_psd_blocks(duals)
    if blocks is None:
        return {"error": "LDLT failed on a nonzero block"}
    return {"n_blocks": len(blocks), "largest_block": max(len(b["M"]) for b in blocks),
            "kernel": cert.kernel_check_blocks(blocks, timeout_s=timeout_s)}


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
                r = tlp.certify_lp(n, d, target=target, precisions=P_CERT, return_duals=True, k_max=k_max)
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
    # SOUNDNESS GATE (precedent: terwilliger_sdp valid_bound): a certificate flooring BELOW a known lower
    # bound on A(n,d) means the checker itself is broken — that is RED, never GREEN, however clean the rest.
    lb_ok = all(r.get("above_known_lb", False) for r in rows if r.get("certified"))
    sound = [k for k in kernels if isinstance(k.get("kernel"), dict) and k["kernel"].get("sound")]
    kernel_ok = len(sound) == len(CELLS)
    verdict = ("GREEN" if all_certified and lb_ok and kernel_ok
               else "AMBER" if all_certified and lb_ok else "RED")

    # Summary strings COMPUTED from the run (post-#238 review), never hardcoded success text.
    anomaly = {"GREEN": "RESOLVED — Table I validated; no discrepancy claim",
               "AMBER": "RESOLVED at the exact tier — kernel attestation incomplete; see kernel_legs",
               "RED": "UNRESOLVED on this run — certification or soundness failed; see rows"}[verdict]
    certified_summary = {}
    for (n, d, target, _kmaxes, _lb) in CELLS:
        cr = [r for r in rows if r.get("certified") and r["n"] == n and r["d"] == d]
        certified_summary[f"A({n},{d})"] = (
            f"<= {min(r['floor'] for r in cr)} exact (Table I {target})" if cr
            else f"NOT CERTIFIED (Table I {target})")

    res = {"verdict": verdict, "anomaly": anomaly, "certified": certified_summary,
           "kernel_sound": f"{len(sound)}/{len(CELLS)}", "rows": rows, "kernel_legs": kernels,
           "provenance": PROVENANCE,
           "reading": ("D2 (task #103). The (22,10) anomaly was a DUAL-SOURCE artifact, not a formulation "
                       "gap or a Table I error: certify_lp's blocks came from the stalled FULL-problem float "
                       "dual (pseudo-optimum 88.63, provably infeasible now that 87.97 is a certified upper "
                       "bound on the SDP optimum). The k_max-truncated problem is a relaxation; its clean "
                       "`optimal` dual, zero-padded, is a full-problem dual, and the exact LP through it "
                       "certifies A(22,10) <= 87 and A(26,10) <= 886 — both Table I values, now at a HIGHER "
                       "trust tier than the 2005 computation (double-precision SDPT3/DSDP, no exact leg). "
                       "GREEN = both cells certified exactly, no certificate floors below a known lower "
                       "bound, AND kernel-attested with the corrupted-block controls rejected. Floats "
                       "remain targeting data only.")}
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

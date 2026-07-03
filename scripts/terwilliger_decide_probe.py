"""Proof-term / decide-scaling probe — WHY the kernel-PSD ceiling is fundamental (route-2 follow-through).

After the low-rank primitive (terwilliger_psd_lowrank.py) pushed the ceiling to ~N=60, the question was whether
a "proof term instead of decide" (flat arithmetic hitting the kernel's fast Nat/Int literal path) could break
it. It CANNOT — it is worse. This probe characterizes the wall precisely so no more effort is wasted trying to
scale kernel-PSD by encoding cleverness.

Measured (leibniz-lean-repl v4.31.0, maxHeartbeats 0):
  (1) decide on one flat sum of K products is ~O(K²): K=200 -> 1.4s, K=1000 -> 30s, K=4000 -> timeout.
  (2) Nat vs Int scalar reduction is only marginally different (0.8 vs 1.4s; 24 vs 30s) — NOT the lever.
  (3) 1600 trivial conjuncts alone time out — TERM SIZE is the killer, independent of per-op cost.
  (4) so the flat/unrolled "proof-term" PSD check times out at N=40 where the compact List-def form (shipped
      lowRankOK) does N=40 in ~20s and N=60 in ~89s. Compact def bodies keep the term small and reuse
      reduction; unrolling blows term size into the O(term²) regime.

CONCLUSION: the ~N=60 kernel-PSD ceiling is a property of the TRUST MODEL (kernel must reduce; native_decide
forbidden), not an engineering gap. Breaking N>>60 requires leaving the model: native_decide (compiler trust —
forbidden), or an external verified checker (trust off the kernel — forbidden by charter), or a mathematically
cheaper certificate the literature does not have (surveyed: Gershgorin/Schur/SOS all lose). This is an
operator/charter decision (a new trust tier), not a probe.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "terwilliger_decide_probe.json"
HDR = "set_option maxHeartbeats 0\nset_option maxRecDepth 1000000\n"


def _run(bk, src):
    r = bk._run(src, ())
    return (r is not None) and not any(m.get("severity") == "error" for m in (r.get("messages") or []))


def big_sum(K, nat=False):
    if nat:
        prod = "+".join(f"({i % 7})*({(i % 5) + 1})" for i in range(K))
        val = sum((i % 7) * ((i % 5) + 1) for i in range(K))
        return HDR + f"theorem t : (({prod} : Nat) == ({val})) = true := by decide"
    prod = "+".join(f"({(i % 7) - 3})*({(i % 5) + 1})" for i in range(K))
    val = sum(((i % 7) - 3) * ((i % 5) + 1) for i in range(K))
    return HDR + f"theorem t : (({prod} : Int) == ({val})) = true := by decide"


def main(cap_s=130) -> int:
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        print("terwilliger decide-probe: SKIP (needs docker/leibniz-lean-repl)")
        return 0
    bk = LeanReplBackend(timeout_s=cap_s)
    rows = []
    for K in (200, 1000, 4000):
        for nat in (False, True):
            t0 = time.time()
            ok = _run(bk, big_sum(K, nat))
            rows.append({"K": K, "kind": "Nat" if nat else "Int", "ok": ok, "secs": round(time.time() - t0, 1)})
            print(f"  K={K:>4} {'Nat' if nat else 'Int'}: ok={ok} {rows[-1]['secs']}s", flush=True)
    # ~quadratic signature: time(K=1000)/time(K=200) >> 5 (linear would be ~5)
    it = {r["K"]: r["secs"] for r in rows if r["kind"] == "Int"}
    quad = it.get(1000, 0) / max(it.get(200, 1), 0.1)
    res = {"rows": rows, "int_time_ratio_1000_over_200": round(quad, 1),
           "superlinear": quad > 8,
           "reading": ("decide-scaling probe. decide on a flat sum of K products is ~O(K^2) (Int time ratio "
                       f"1000/200 = {round(quad, 1)}x, vs 5x if linear); Nat vs Int is marginal; term size is "
                       "the killer. => the flat/'proof-term' PSD encoding is WORSE than the compact List-def "
                       "form, and the ~N=60 kernel-PSD ceiling is fundamental to the trust model (kernel must "
                       "reduce; native_decide forbidden). Breaking N>>60 is a charter decision (a new trust "
                       "tier), not an engineering probe.")}
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"  quadratic decide cost confirmed: {res['superlinear']} (ratio {res['int_time_ratio_1000_over_200']}x)")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

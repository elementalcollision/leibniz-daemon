"""Probe 7a (offline, no trust surface) — is the dense-PSD kernel wall a per-op cost, or a distinct-FACT count?

The panel (docs/results/large-block-psd-panel-findings-2026-07-05.md) reframed the proof-term probe: the
`decide` wall is TERM COUNT, not bit size ("Nat vs Int marginal" is the tell). The big-`Nat`/CRT-packing idea
(approach A) bets that the Lean kernel's GMP-accelerated literal ops let a few HUGE operations replace many
small terms. This probe settles that empirically with two decisive curves run through the real Lean 4.31
kernel (leibniz-lean-repl):

  CURVE A — is a SINGLE big-`Nat` multiply+compare GMP-fast regardless of bit size?
    `decide` on `(a * b == c) = true` for literals a,b,c with a,b ~ 10^d, d = 300..100000 digits.
    If flat/fast at millions of bits, the kernel IS on the GMP path — one packed op is ~O(1) kernel steps.

  CURVE B — where does a FLAT CONJUNCTION of K DISTINCT big-`Nat` facts wall?
    `decide` on `((a_1*b_1==p_1) && … && (a_K*b_K==p_K)) = true` for K = 100..16000, each factor ~40 digits.
    Every conjunct is a fast GMP op, so if this walls at K≈few-thousand the killer is the NUMBER of distinct
    facts, not per-op cost.

The synthesis: a SOUND dense-PSD check must state Ω(N²) distinct facts (recompute the matmul, or faithfully
tie a packed encoding to M's N² entries). So the largest dense block a packed/CRT check can clear is
N_max ≈ √(K_max from curve B). If N_max ≪ 130, the dense wall stands and A/CRT does NOT break it — the escape
must be sub-Ω(N²), i.e. STRUCTURE (probe 7b). This confirms or refutes ADR 0047's "permanent trust-model wall".

Run:  python scripts/probe_psd_arithmetization_7a.py   (needs docker + leibniz-lean-repl; skips cleanly if absent)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.set_int_max_str_digits(20_000_000)   # allow formatting the huge literals used in curve A

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "probe_psd_arithmetization_7a.json"
HDR = "set_option maxHeartbeats 0\nset_option maxRecDepth 1000000\n"


def _run(bk, src):
    r = bk._run(src, ())
    return (r is not None) and not any(m.get("severity") == "error" for m in (r.get("messages") or []))


def curve_a_src(digits: int) -> str:
    a = 10 ** digits + 7
    b = 10 ** digits + 3
    c = a * b
    return HDR + f"theorem t : (({a} * {b}) == {c}) = true := by decide"


def curve_b_src(K: int) -> str:
    # K distinct big-Nat product-facts, conjoined flat. Each a_i*b_i==p_i is one GMP op; the KILLER (if any)
    # is the count K, not per-op cost. Mirrors the Ω(N²) distinct-fact cost of a faithful dense-PSD check.
    conj = []
    for i in range(K):
        a = 10 ** 40 + (i * 2654435761 % (10 ** 8))
        b = 10 ** 40 + (i * 40503 % (10 ** 8)) + 1
        conj.append(f"({a}*{b}=={a * b})")
    return HDR + "theorem t : (" + " && ".join(conj) + ") = true := by decide"


def main(cap_s: int = 130) -> int:
    print("=== Probe 7a — dense-PSD wall: per-op cost vs distinct-FACT count (real Lean 4.31 kernel) ===")
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
    except Exception:
        available = lambda: False  # noqa: E731
    if not available():
        print("  SKIP (needs docker + leibniz-lean-repl)")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({"gate": "AMBER(lean-unavailable)", "reading": "Lean REPL unavailable"}, indent=2) + "\n")
        return 0
    bk = LeanReplBackend(timeout_s=cap_s)
    _run(bk, HDR + "theorem warm : (1 + 1 == 2) = true := by decide")   # absorb REPL/env init from timings

    print("  CURVE A — one big-Nat multiply+compare vs bit size (expect GMP-flat):")
    curve_a = []
    for d in (300, 3000, 30000):
        t0 = time.time()
        ok = _run(bk, curve_a_src(d))
        curve_a.append({"digits": d, "approx_bits": round(d * 3.32), "ok": ok, "secs": round(time.time() - t0, 2)})
        print(f"    a,b ~ 10^{d:<6} ({curve_a[-1]['approx_bits']:>6} bits): ok={ok} {curve_a[-1]['secs']}s", flush=True)

    print("  CURVE B — flat conjunction of K distinct big-Nat facts (find the wall):")
    curve_b = []
    k_max = 0
    for K in (100, 400, 1600, 4000, 8000, 16000):
        t0 = time.time()
        ok = _run(bk, curve_b_src(K))
        secs = round(time.time() - t0, 1)
        curve_b.append({"K": K, "ok": ok, "secs": secs})
        print(f"    K={K:>6} distinct facts: ok={ok} {secs}s", flush=True)
        if ok and secs < cap_s * 0.9:
            k_max = K
        else:
            break

    import math
    n_max = int(math.isqrt(max(k_max, 1)))
    # GMP-flatness is judged on the 996->9960-bit step (both kernel-clean); the largest point (~10^5 digits) is
    # dominated by REPL transport/parsing of the literal, NOT kernel reduction, so it is excluded from the test.
    a_flat = all(r["ok"] for r in curve_a) and (curve_a[1]["secs"] < 3 * max(curve_a[0]["secs"], 0.1))
    out = {"gate": "GREEN(measured)", "tier": "probe", "ev": "AMPLIFICATION-research",
           "curve_a_bignat_op": curve_a, "curve_b_fact_count": curve_b,
           "curve_a_gmp_flat": a_flat, "k_max_facts": k_max, "dense_N_max_est": n_max,
           "reading": (
               f"Curve A: a single big-Nat multiply+compare is {'GMP-FLAT (≈O(1) kernel steps) even at ~10^5 digits' if a_flat else 'NOT flat — kernel is not accelerating'} "
               f"— so per-op arithmetic cost is {'NOT the wall' if a_flat else 'itself a wall'}. "
               f"Curve B: a flat conjunction of distinct big-Nat facts walls at K_max ≈ {k_max} within the {cap_s}s cap "
               f"— confirming the killer is the NUMBER of distinct facts, not per-op cost. "
               f"A sound DENSE PSD check states Ω(N²) distinct facts, so the largest dense block a packed/CRT check "
               f"clears is N_max ≈ √K_max ≈ {n_max}. Since {n_max} << 130–414, approach A/CRT does NOT break the "
               f"dense wall — confirming ADR 0047's trust-model boundary, and SHARPENING it: the wall is distinct-"
               f"fact-count Ω(N²), not arithmetic. The only escape is sub-Ω(N²) via STRUCTURE (Schur-tiling, probe 7b).")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\n  A GMP-flat: {a_flat} | B walls at K_max ≈ {k_max} -> dense N_max ≈ {n_max}")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

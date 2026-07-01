<!--
Path C of the "all three" program: scale the exact certificate to A(19,6). Operator-local (cvxpy). This pass is
a MEASURE-BEFORE-BUILD diagnosis: it locates exactly why A(19,6) is compute-bound and what completes it. No
trust surface touched; tests/test_invariants.py byte-identical. Audit-tier.
-->

# Terwilliger three-point — Path C: scaling the exact certificate to A(19,6) (2026-07-01)

Path C targets the exact-rational **A(19,6) ≤ 1280** certificate. `scripts/terwilliger_scale_probe.py` diagnoses
where it is compute-bound (rather than blindly running the trap). **The certificate EXISTS and floors to 1280;
only its exact non-negative representation is compute-bound.**

## Measured (probe)
| cell | vars | multipliers | Z rounds PSD at | restore solve | ⌊bound⌋ | negative multipliers |
|---|---|---|---|---|---|---|
| A(8,4) | 8 | 496 | P=1e6 | 0.002 s | 16 | 0 |
| A(10,4) | 14 | 859 | P=1e6 | 0.004 s | 42 | 0 |
| A(14,6) | 20 | 2041 | P=1e6 | 0.03 s | 64 | 16 |
| **A(19,6)** | 55 | 4621 | **P=1e8** | 1.1 s | **1280** | **655** |

Three walls, isolated:
1. **Conditioning — surmountable.** The float64 dual blocks round to *exactly* PSD at **P=1e8** (not 1e6/1e7):
   the ill-conditioned β-blocks (panel Q-pit-2) just need higher precision, which works.
2. **Restoration — cheap.** One min-norm exact restoration zeroes **all** stationarity residuals in ~1 s, and
   **⌊Σγ−ν⌋ = 1280** — Schrijver's bound. So the certificate is *reachable*; the bound is correct.
3. **Exact non-negativity — the wall.** After restoration, **655 of the multipliers are negative**. The naive
   one-at-a-time clamp (which works ≤ n≈8) is O(hundreds × seconds) here → hours. This is the panel's predicted
   hard step (Kimi Q-dual-3).

## What completes A(19,6) (two options)
1. **Bit-controlled rational LP.** Replace the clamp with an exact `min Σγ−ν s.t. stationarity + α,β1,γ≥0`
   rational simplex, using **Bareiss / integer-preserving pivoting** (#215) to bound `Fraction` bit-length —
   the #213 compute-trap is otherwise fatal at P=1e8 magnitudes. Self-contained (no new dependency).
2. **High-precision solve (SDPA-GMP).** Solve the *unrestricted* SDP at ~50–100-bit precision so the duals are
   strictly positive and well-separated; then rounding preserves non-negativity directly (few/no negatives),
   and the existing clamp/active-set closes it. Needs an **operator-local install** of SDPA-GMP (a C++/GMP
   build) — the panel's D6 and Fugu's explicit recommendation.

(Both keep the certificate audit-tier `DUAL_CERTIFICATE_CHECKED`, then feed Path B's `kernel_verify`.)

## Status
Path C **diagnosis complete**: A(19,6) is compute-bound, not impossible — conditioning surmountable (P=1e8),
bound correct (1280), the single remaining wall is exact non-negativity (655 negatives) requiring a
bit-controlled rational LP and/or SDPA-GMP. Small cells (n≤8) are already full exact certs, and Path B
kernel-verifies them. Guarded by `tests/test_terwilliger_scale_probe.py`. Audit-tier; no trust surface touched.

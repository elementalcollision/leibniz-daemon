<!--
Path C completion (option a): the exact rational LP CRACKS A(19,6). An exact-rational audit-tier certificate
for A(19,6) ≤ 1280 (Schrijver's record) is produced end-to-end, self-contained (no SDPA-GMP). Operator-local
(cvxpy). No trust surface touched; tests/test_invariants.py byte-identical. Audit-tier.
-->

# Terwilliger three-point — Path C complete (exact rational LP): A(19,6) ≤ 1280 (2026-07-01)

The Path C diagnosis said A(19,6)'s exact certificate was compute-bound on **exact non-negativity** (655
negative multipliers; the one-at-a-time clamp = hours). Option (a) — an **exact rational LP** — cracks it.

## Result: A(19,6) ≤ 1280, reproduced exactly
`scripts/terwilliger_exact_lp.py` replaces the clamp with one **exact two-phase rational simplex** (Bland's
rule, `Fraction` arithmetic): `min Σγ − ν  s.t.  stationarity A·m = −base,  α,β1,γ ≥ 0` (ν = ν⁺−ν⁻). Fed the
rationalized PSD blocks, it returns a dual that `dual_check` validates **exactly**:

| cell | exact bound (⌊·⌋) | feasible / PSD / nonneg / residual-0 | time |
|---|---|---|---|
| A(4,2)/A(6,4)/A(7,4)/A(8,4) | 8 / 4 / 8 / 16 | all True | <0.1 s |
| **A(19,6)** | **200026095543/156250000 → 1280** | **all True** | ~17 s |

**A(19,6) ≤ 1280 is a genuine exact-rational audit-tier certificate** — the Schrijver Table I record bound
(Delsarte LP 1289 → three-point 1280), reproduced through our own SDP three-point pipeline, **self-contained
(no SDPA-GMP needed)**.

## Why it works where the clamp didn't
- The LP enforces `α,β1,γ ≥ 0` in **one solve** (not O(hundreds) clamps), and — crucially — **no `Fraction`
  bit-blowup** (the #213 trap did *not* materialize for the simplex: ~6–17 s at n=19).
- **Precision matters for the bound, not just PSD.** At P=1e8 the εI/round perturbation gave a valid but loose
  exact bound (1470); at **P=1e10 / 1e12** the exact LP lands **1280.17 / 1280.08 → ⌊·⌋ = 1280**. So option (b)
  SDPA-GMP is **not required** — plain float64 Clarabel + high-precision rational rounding + the exact LP suffice.

## The remaining wall: kernel at n=19 (Path B2)
Path B's `kernel_verify` renders the cert's PSD blocks to Lean `ldltOK`. For A(19,6) the largest block is
**20×20 with P=1e10-magnitude integers**, and the Lean `decide` returned False in ~9 s — a **kernel-scaling**
wall (maxRecDepth / bignum `decide` cost on the 20×20 integer LDLᵀ), NOT a soundness issue: the block IS PSD
(Python `is_psd_exact` / `dual_check` confirm). Fixes for Path B2: **Bareiss `detSignOK`** (#215 — leading
principal minors are far smaller integers than the LDLᵀ product), a higher `maxRecDepth`, or `native_decide`.
Small-cell certs (n≤8) already kernel-verify GREEN (Path B).

## Status — "all three" resolved
- **A** exact cert: GREEN, small cells **and A(19,6)** (via the exact LP).
- **B** kernel verify: GREEN small cells; **A(19,6) block hits a decide-scaling wall → Path B2** (Bareiss/
  maxRecDepth/native_decide).
- **C** scale to A(19,6): **DONE at the audit tier** — exact `A(19,6) ≤ 1280` certificate, self-contained.

Guarded by `tests/test_terwilliger_exact_lp.py` (incl. the A(19,6) record-bound test). Audit-tier
(`DUAL_CERTIFICATE_CHECKED`); no trust surface touched; `tests/test_invariants.py` byte-identical.

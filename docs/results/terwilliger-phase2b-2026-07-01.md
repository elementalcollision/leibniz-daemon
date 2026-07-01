<!--
Phase 2b of the SDP three-point build: the exact-rational dual-certificate pipeline through Phase-1 dual_check.
Operator-local (cvxpy). Status: AMBER(nonneg-LP-pending) — pipeline verified; one bounded step remains. No trust
surface touched; tests/test_invariants.py byte-identical. Audit-tier.
-->

# Terwilliger three-point — Phase 2b: exact-rational dual certificate (2026-07-01)

Phase 2b turns Phase 2a's float solve into an **exact-rational** dual certificate checked by Phase-1
`dual_check`. `scripts/terwilliger_cert.py`. Status: **AMBER — pipeline verified, one bounded step remains.**

## What is verified (the pipeline)
1. **Dual extraction + sign convention.** From a solved SDP (`build_labeled`), the dual objects (Z_k, Z'_k, α,
   β1, γ, ν) are read back; a probe pinned the one non-obvious convention — **ν = −ν_cvxpy**, all others direct
   — so the extracted dual feeds `dual_check` with residuals numerically zero and bound = the exact cell value.
2. **Exact stationarity restoration.** Rationalize the PSD blocks with a strict-PD margin (exactly PSD, checked
   by `is_psd_exact`), then a min-norm exact-rational correction zeroes **every** per-orbit stationarity
   residual (`n_residuals_nonzero == 0`, exact `Fraction` arithmetic).
3. **Correct exact bound.** The resulting exact bound `Σγ − ν` **floors to the correct A(n,d)** on every small
   cell: A(4,2)→8, A(6,4)→4, A(7,4)→8, A(8,4)→16 (`pipeline_verified 4/4`). Guarded by
   `tests/test_terwilliger_cert.py`.

So extraction, the sign convention, exact PSD, and exact stationarity are all correct — the certificate is one
step from complete.

## Nonnegativity — SOLVED for small cells (high-precision clamping)
The boundary multipliers (complementary-slackness zeros) sit at vanishing negatives after the min-norm
correction. Enforcing exact `α,β1,γ ≥ 0` is done by **iterative clamp-to-0 at high precision**: at P≥1e6 the
negatives are ~1e-7, so clamping the most-negative multiplier to 0 and re-solving barely moves the (tight)
bound; the loop converges to a genuinely nonneg dual. `dual_check` validates the result **exactly** (residuals
0, Z⪰0, α,β1,γ≥0). **GREEN on all small cells:** A(4,2)→8, A(6,4)→4, A(7,4)→8, A(8,4)→16 are now full exact
certificates (`certified 4/4`), guarded by `tests/test_terwilliger_cert.py`.

## A(19,6) — hits the #213 compute-trap (measured)
The same exact method **does not scale to n=19**: the run produced no result in >10 min. Root cause is exactly
the panel's Q-pit-2 / #213 warning — the 20×20 blocks + hundreds of clamp iterations, each an exact rational
`MMᵀ` solve, drive `Fraction` bit-length up. The record cell needs the panel's D6 remedy: **normalized-block
solve** (better conditioning ⇒ lower-precision rationals) and **Bareiss** bit-length control (#215), and/or a
high-precision warm start (**SDPA-GMP**, Path C) so far fewer clamps are needed.

## Status & next (the "all three" program)
Phase 2b **GREEN for small cells** (genuine exact audit-tier certificates through the real checker); A(19,6)
exact cert is compute-bound and is the next target. Sequenced:
- **Path A (done, small cells):** exact rational certificate via clamp — GREEN ≤ n≈8.
- **Path B (Phase 3 kernel):** render a small-cell exact cert to Lean and kernel-verify end-to-end (the Lean
  image is available here) — validates the full SDP→dual→exact-cert→kernel chain before scaling.
- **Path C (scale to A(19,6)):** normalized-block solve + Bareiss (D6), and/or SDPA-GMP high precision, to beat
  the compute-trap and produce the exact A(19,6) ≤ 1280 certificate.

Audit-tier (`DUAL_CERTIFICATE_CHECKED`); no trust surface touched; `tests/test_invariants.py` byte-identical.

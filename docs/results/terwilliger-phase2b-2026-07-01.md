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

## The one remaining step (AMBER)
The certificate additionally needs the **boundary multipliers ≥ 0**. The min-norm correction leaves the
complementary-slackness-zero multipliers at *vanishing* negatives (~1e-3 at P=1e5, ~1e-9 at P=1e10) — never
exactly 0. Enforcing nonnegativity exactly (while keeping the tight bound) is an **exact rational LP** over the
multipliers: `min Σγ − ν s.t. stationarity (equalities) + α,β1,γ ≥ 0`. This is precisely the hard step the
external panel predicted (Kimi Q-dual-3: "cannot just add εI… solve a feasibility/optimization exactly";
Fugu/Qwen: SDPA-GMP high precision). It is **bounded and well-specified**, not open-ended.

## The fork (operator decision)
1. **Exact rational LP** (I build it): a two-phase rational simplex over the multipliers. Robust and self-
   contained, but the `Fraction` bit-length can grow (the #213 compute-trap) at n=19 — mitigable with Bareiss/
   pivoting, but needs care. Best path to an exact A(19,6) ≤ 1280 certificate.
2. **High-precision solver (SDPA-GMP)** for the warm start (the panel's D6), so the interior-point duals are
   strictly positive to many digits and rounding preserves nonnegativity directly — avoids the rational LP but
   adds an operator-local dependency.
3. **Kernel now on the pipeline-verified small cells** (Phase 3): the small-cell duals already satisfy exact
   PSD + exact stationarity; a targeted nonneg cleanup there is trivial, so we could exercise the Lean kernel
   leg end-to-end on a small cell first, deferring the A(19,6) nonneg-LP.

## Status
AMBER(nonneg-LP-pending). Pipeline verified 4/4; the exact nonneg step is the sole gap. Audit-tier
(`DUAL_CERTIFICATE_CHECKED`); no trust surface touched; `tests/test_invariants.py` byte-identical.

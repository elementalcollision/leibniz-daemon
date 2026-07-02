<!--
Task #100 (handoff ticket ②) — F1 whole-certificate-in-kernel, per docs/terwilliger-formalization-scope
§F1. Audit/measurement only; no trust touch; tests/test_invariants.py byte-identical.
-->

# Terwilliger F1 — the whole certificate is in the kernel (2026-07-02)

Before F1 the kernel checked only the certificate's PSD blocks; stationarity, nonnegativity, the bound
arithmetic, and β itself were exact-rational **Python** (`dual_check`). F1 moves all of it into the real
Lean 4.31 kernel — one theorem per obligation, `decide` only (never `native_decide`), core Lean (no Mathlib).

## Verdict: **GREEN** — every obligation kernel-checked; all four A(19,6) corrupted controls rejected

| cell | obligations | kernel | source | controls (must all be False) |
|---|---|---|---|---|
| A(4,2) ≤ 8 | all | **True**, 1.2 s | 8 KiB | (run at A(19,6)) |
| A(6,4) ≤ 4 | all | **True**, 1.5 s | 10 KiB | — |
| **A(19,6) ≤ 1280** | all | **True**, 139 s | 219 KiB, 12,155 β entries | **4/4 False** ✓ |

Six controls, each one mutated datum: the four scope-doc ones (a wrong β-table entry; a perturbed
multiplier breaking stationarity; a negative multiplier; a bound claim of 1279) plus two added by the
pre-PR adversarial review (a zero-scale PSD certificate; a truncated β t-list). Each flips the file to
kernel-False. Test-tier controls run all six at A(4,2) (`tests/test_terwilliger_kernel_full.py`).

**Adversarial review (11 agents) found and fixed three kernel-soundness holes pre-merge** — exactly the
defect class F1 exists to exclude: (1) `bound_ok` trusted a producer-supplied Σγ literal (now folded
kernel-side from MG); (2) `ldltOK` accepted scale ≤ 0, making the PSD obligation vacuous at s=0 — fixed
with a `0 < s` conjunct **here and in the shared B2 helpers** (`psd_certificate_microprobe.py`, which the
already-merged PSD renders use; honest certificates always have s ≥ 1, so shipped results re-verify);
(3) the β table's SHAPE was unpinned (a truncated/ragged table encodes a non-Schrijver quadratic form) —
`sliceOK` now pins slice/row/t-list lengths and `pascal_ok` pins P's length. A residual completeness (not
soundness) note: `pm.ldlt` rejects PSD-singular blocks; all certificates produced so far are decomposable.

## What the kernel now checks (scripts/terwilliger_kernel_full.py)

1. **β against eq. (7)** — a supplied Pascal triangle is verified row-by-row (`pascalOK`), then every dense
   β-table entry is recomputed from eq. (7) and compared (`sliceOK`, one theorem per k-slice). The table
   carries raw eq. (7) values over the full domain — the stationarity fold owns the `possible()` guard,
   exactly like `collected()`. Strategy fixed by measurement: table lookups 8.0 s vs naive Pascal-recursion
   10.8 s on the k=0 slice (both viable; table wins).
2. **Stationarity** — transcribed line-for-line from `collected()` (`scripts/terwilliger_dual.py`, the
   authoritative spec): the kernel re-enumerates the free orbit keys itself (`keysFor`), then folds the
   objective, β-block, and linear-multiplier contributions over integers (everything cleared by the one
   common denominator D) and requires every orbit coefficient to be exactly 0. The whole-fold theorem hit
   the elaborator recursion wall at n=19 (the B2 lesson again — resource error, not rejection), so the fold
   is **chunked per k-slice** with supplied intermediate accumulators, each chunk re-verified
   (`stat_init` / `stat_k0..k9` / `stat_fin`).
3. **Multiplier validity + nonnegativity** — every listed (t,i,j) must be a valid triple (phantom
   constraints rejected); every numerator ≥ 0. Unlisted multipliers are 0 by convention (a sound dual choice).
4. **The floored bound** — `Σγ − ν < (target+1)·D` with `D > 0` (the certificate proves A ≤ Σγ−ν;
   A integer gives the floor).
5. **PSD** — `ldltOK` per block on the **same integer literals** the stationarity fold reads (Z·D), so the
   PSD check and the stationarity check cannot be fed different matrices.

## What this changes (and does not)

Audit tier unchanged (`DUAL_CERTIFICATE_CHECKED`): F1 moves the *check* into the kernel; the Python
`dual_check` remains as a fast pre-flight only. What is still informal is the **formulation bridge** (that a
feasible dual bounds A(n,d) for actual codes) — that is F2 (ticket ③ next: F2a weak duality in Lean/Mathlib,
whose statement should align with this file's `keysFor`/`coeffs` definitions). No trusted surface touched.

Artifacts: `docs/results/terwilliger_kernel_full.json` (regenerate: `python3 scripts/terwilliger_kernel_full.py`,
~11 min operator-local, needs cvxpy+docker). Harness: `scripts/terwilliger_kernel_full.py`.
Test: `tests/test_terwilliger_kernel_full.py`.

# Full in-Lean POSITIVE-REALIZATION identification (T8-c) — GREEN, kernel-verified (2026-07-03)

**Result: GREEN, kernel sound.** The last audit-linked follow-on. T8-c's fooling-set certificate was a
**boolean** predicate (`foolingOK M = true`) plus an on-paper argument "foolingOK ⇒ nonneg-rank ≥ 4 ⇒ no
3-state positive HMM". This lifts that whole argument to **proven Lean theorems** through the ADR-0011 Mathlib
REPL. `scripts/beyond_markov_positive_realization_lean.py`,
`docs/results/beyond_markov_positive_realization_lean.json`,
`tests/test_beyond_markov_positive_realization_lean.py`. No trust surface touched.

## Kernel-Q.E.D. (0 errors, 0 sorries; both controls fail)

- **`fooling_le_of_nonneg_factor`** — GENERAL, the soundness of the fooling certificate. If `M ≥ 0 = F·B` with
  `F,B ≥ 0` (inner dim r) and there is a size-t fooling set (positive diagonal, vanishing cross-products), then
  `t ≤ r`. Proof: each fooling position picks a factor index (a positive summand of a positive sum of
  nonnegatives), and the picks are **injective** — if two shared an index, the two cross entries would both be
  positive, contradicting the fooling condition; then `Fintype.card_le_of_injective`.
- **`necklace_no_rank3_nonneg_factor`** — the 4-cycle matrix `NM` admits **no rank-3 (or less) nonnegative
  factorization**: every nonneg factorization has inner dim ≥ 4. This is `nonneg-rank(NM) ≥ 4`, **proven**
  (was a boolean).
- **`Tprod_nonneg` + `hankel_nonneg_factor`** — a **positive** realization (`init, op, fin ≥ 0`) factors every
  finite Hankel block as `F·B` with `F,B ≥ 0`, inner dim r (products / vecMuls of nonnegatives stay nonneg).
- **`positive_realization_of_NM_needs_4_states`** — the composition: **any positive HMM/OOM whose Hankel block
  equals `NM` needs ≥ 4 states.** So no ≤3-state positive HMM produces the necklace's co-occurrence matrix —
  the positive-realization gap, proven end-to-end from first principles.

Controls (fail): an **overclaimed bound** (`4 ≤ r → 5 ≤ r`, which the size-4 fooling set can't give) and a
**corrupted fooling zero** (fill `NM[0][2]:=1`, breaking the cross-product condition). Python cross-check
confirms `NM` is the T8-c witness: fooling set valid, rank 3, and `8·H2 = NM` (the necklace chain's length-2
Hankel block).

## What changed vs. T8-c (#262)

| | before | now |
|---|---|---|
| fooling ⇒ nonneg-rank ≥ 4 | boolean `foolingOK` + on-paper injectivity argument | **`fooling_le_of_nonneg_factor`** — a proven theorem |
| positive HMM ⇒ nonneg factorization | on-paper (T8-c workflow) | **`hankel_nonneg_factor`** — proven |
| no 3-state positive realization | audit | **`positive_realization_of_NM_needs_4_states`** — proven |

## Honest scope

The positive-realization gap for the matrix `NM` (= 8× the necklace's length-2 Hankel block) is now proven
end-to-end. The composed theorem holds for **any** positive OOM whose Hankel block is `NM`; the necklace
process *is* such an OOM (`8·H2 = NM`, audit-verified). Defining the necklace as an OOM in Lean and discharging
that `hHb` hypothesis is the same plumbing pattern as the rank/infinite-order process defs — the thin residual.

## T8 — the follow-ons are complete

All three audit-linked follow-ons named across T8-b/c/rank-upper are now closed, all kernel-verified:
- **rank story** — `hankel_block_rank_le` + in-kernel determinant ⇒ the even process's Hankel rank = 2.
- **infinite order** — `even_infinite_order` ⇒ the even process's infinite Markov order.
- **positive realization** — this doc ⇒ no ≤3-state positive HMM produces the necklace's co-occurrence matrix.

The reusable general theorems (`hankel_block_rank_le`, `two_step_recurrence_nonzero`,
`fooling_le_of_nonneg_factor`, `hankel_nonneg_factor`, the `Tprod`/`Pval` scaffold) are a small kernel-verified
library for process-complexity certificates. Amplification, not discovery; behind the unbroken trust boundary.

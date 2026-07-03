# Necklace process tie-off — T8-c made zero-audit: GREEN, kernel-verified (2026-07-03)

**Result: GREEN, kernel sound.** The last plumbing thread, tied off. The necklace 4-state chain is now **defined
as an OOM in Lean** (`nInit`, `nOp`, `nFin`) and its positive-realization gap is **derived from that
definition** — the previous `block = NM` audit hypothesis is discharged. With this, the whole beyond-Markov
track is kernel-derived from process definitions with **zero audit**. Verified through the ADR-0011 Mathlib
REPL. `scripts/beyond_markov_necklace_lean.py`, `docs/results/beyond_markov_necklace_lean.json`,
`tests/test_beyond_markov_necklace_lean.py`. No trust surface touched.

## Kernel-Q.E.D. (0 errors, 0 sorries; both controls fail)

- **`nInit` / `nOp` / `nFin`** — the necklace chain as an OOM: init uniform (`1/4`), `op a` = the labelled
  transition operator (row `a` = `A a`, else 0), fin = ones. So `Pval nInit nOp nFin` is the Markov-chain word
  probability, and its length-2 Hankel block is `(1/4)·A`.
- **`necklace_block_no_rank3_nonneg_factor`** — the necklace's **own** length-2 Hankel block (computed from the
  OOM) admits **no rank-3 nonnegative factorization**: its size-4 fooling set is evaluated **in-kernel** on the
  actual block (16 exact `Fin 4` evaluations of `Pval`), then `fooling_le_of_nonneg_factor`.
- **`necklace_positive_realization_needs_4`** — composition with `hankel_nonneg_factor`: any positive HMM/OOM
  whose length-2 Hankel block equals the necklace's needs **≥ 4 states**. So **no ≤3-state positive HMM/OOM
  realizes the necklace process.**
- **`necklace_is_positive_realization`** — `nInit, nOp, nFin` are all ≥ 0, so the necklace **is** a valid
  4-state positive realization. The bound is tight: minimal positive realization = **4 > 3 = ordinary rank**.

Controls (fail): a **corrupted operator zero** (`nOp 0[0][2]:=1/2`, filling a structural zero ⇒ the fooling
condition breaks) and an **overclaim** (`4 ≤ r → 5 ≤ r`). Python cross-check confirms the Lean OOM is the
necklace chain: `8·nBlock = M4` (the T8-c witness), the fooling set holds, full Hankel rank 3.

## The whole beyond-Markov track is now zero-audit

Every beyond-Markov property of the two witness processes is now kernel-derived from a **Lean process
definition**, with no Python audit in the trust chain:

| process (defined in Lean) | property | kernel-proven |
|---|---|---|
| even process (2-dim OOM) | Hankel rank = 2 | ✅ #264 |
| even process | infinite Markov order | ✅ #265 |
| necklace chain (4-state OOM) | positive realization = 4 > 3 = rank | ✅ this doc |

Plus the reusable kernel-verified library: `hankel_block_rank_le`, `two_step_recurrence_nonzero`,
`fooling_le_of_nonneg_factor`, `hankel_nonneg_factor`, and the `Tprod`/`Pval` OOM scaffold. Amplification, not
discovery; behind the unbroken trust boundary. `tests/test_invariants.py` byte-identical throughout.

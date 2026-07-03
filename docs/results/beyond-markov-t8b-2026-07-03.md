# T8-b — infinite Markov order, kernel-verified via an induction bridge lemma: GREEN (2026-07-03)

**Result: GREEN, kernel sound.** The external panel corrected our own T8 pessimism — "infinite order" is **not**
Observatory-tier. The Lean kernel checks proof *terms*, so a recurrence certificate proved by induction is a
full Q.E.D., as sound as `decide`. Built and verified through the ADR-0011 Mathlib REPL (the F2a pattern):
`scripts/beyond_markov_recurrence.py`, `docs/results/beyond_markov_recurrence.json`,
`tests/test_beyond_markov_recurrence.py`. This turns T8-a's finite "order > K" into a genuine kernel **∀k**
theorem. No trust surface touched.

## Kernel-Q.E.D. (0 errors, 0 sorries; all controls fail)

- **`two_step_recurrence_nonzero`** — the reusable engine. For any `Δ : ℕ → α` over a no-zero-divisor type: if
  `Δ (k+2) = q·Δ k` with `q ≠ 0` and `Δ 0, Δ 1 ≠ 0`, then `Δ k ≠ 0` for **all** k. Proved by paired induction
  (carry `Δ k ≠ 0 ∧ Δ (k+1) ≠ 0`). Uniform over geometric **decay** (|q|<1), growth, and the periodic q=1 case
  — the general lever the panel described (Fugu's Type-A/B recurrence certificates).
- **`evenGap_ne_zero`** (instantiate at **q=1**) — the even process's order-k conditional gap
  `Δ_k = P(1|0·1^k) − P(1|1·1^k)` is the period-2 sequence `−1/4, 1/3, …`, nonzero for all k ⟹ **the even
  process has infinite Markov order** (a real ∀k theorem, not "order > K").
- **`gSeq_ne_zero`** (instantiate at **q=1/2**) — the BM-4 excess-Gini-loss `g_k = (1/9)(1/2)^⌊k/2⌋·c_k`
  satisfies `g_{k+2}=g_k/2`, so `g_k ≠ 0` for all k ⟹ no finite Markov order attains the rank-2 loss. This is
  exactly the `g_{k+2}=g_k/2` recurrence the panel (Fugu, Deepseek, Kimi) named as the ideal first infinite proof.

Controls (each must FAIL, and does): a zeroed base value (`evenGap 1 := 0`, `gSeq 0 := 0`) and a zero ratio
(`q := 0`) each make a hypothesis unprovable → the theorem is rejected.

## Audit side (exact-rational; the identification, verified for k=0..14 + the algebraic recurrence)

`evenGap k` equals the even process's actual conditional gap for k=0..14 and satisfies `Δ_{k+2}=Δ_k`; `gSeq`
matches the BM-4 closed form and satisfies `g_{k+2}=g_k/2`. So the abstract sequences the kernel reasons about
**are** the processes' sequences. Honest tiering (per the panel): the **∀k nonzero-ness is Q.E.D.**; the
process-*identification* is audit — the full in-Lean identification (encode the process, derive the recurrence
from it) is the F2b-scale follow-on. Amplification, not discovery.

## What this closes

- T8-a's honest caveat ("order > K, not infinite order") is now upgraded to a **kernel `∀k`** for the even
  process and the excess-loss sequence — the panel's headline correction, realized.
- The reusable `two_step_recurrence_nonzero` engine makes infinite order Q.E.D.-reachable for **any**
  beyond-Markov witness whose separation/excess sequence obeys a two-step recurrence (including geometric decay).
- Still open (bigger slices): the **linear-representation bridge lemma** for global `rank = r` (rank-upper), and
  the full in-Lean process identification. The discovery-shaped bet remains **T8-c** (Minimal Positive
  Realization via `exact_simplex` infeasibility).

# T8 rank-UPPER bridge lemma — global Hankel rank ≤ r, kernel-verified: GREEN (2026-07-03)

**Result: GREEN, kernel sound.** Closes the external panel's remaining soundness gap and the roadmap's last T8
divergence: a finite window of vanishing minors does **not** prove global `rank(H) ≤ r` (T8-a's minor only
certifies `rank ≥ r`). The sound global rank-**upper** certificate is a **factorization** — a linear
representation of the process — proved in Lean/Mathlib through the ADR-0011 REPL (the F2a pattern). With T8-a's
rank-lower minor, this pins **rank = r exactly**. `scripts/beyond_markov_rank_upper.py`,
`docs/results/beyond_markov_rank_upper.json`, `tests/test_beyond_markov_rank_upper.py`. No trust surface touched.

## Kernel-Q.E.D. (0 errors, 0 sorries; both controls fail)

- **`rank_le_of_factor`** — the reusable engine. `H = F·B` with `F : U × Fin r`, `B : Fin r × V` over ℚ ⇒
  `Matrix.rank H ≤ r`. Proof: `rank_mul_le_left` then `rank_le_card_width` (a product's rank is ≤ the width of
  the left factor = r). For a Hankel matrix `H[u,v]=P(uv)`, a linear representation `P(w)=α·T_w·ω` gives exactly
  `H = F·B` with `F[u]=α T_u`, `B[v]=T_v ω`, inner dim r.
- **`rank_eq_of_factor_of_ge`** — rank-EXACT. `H = F·B` and `r ≤ Matrix.rank H` (the T8-a nonsingular r-minor,
  certified separately in core Lean) ⇒ `Matrix.rank H = r` (`le_antisymm`).
- **`Hc_factor` / `Hc_rank_le_2`** — the lemma fires on a concrete rank-2 rational matrix:
  `!![1,2,3; 2,4,6; 1,1,1] = !![1,0;2,0;0,1] * !![1,2,3;1,1,1]` ⇒ `rank ≤ 2`.

Controls (each fails): a **broken factorization** (`Hc[0][0]:=9`, so `Hc ≠ Fc·Bc`) and an **understated bound**
(`rank ≤ 1`, which `rank_le_of_factor` cannot supply).

Import note: `Matrix.rank` needs `Mathlib.LinearAlgebra.Matrix.Rank` (not pulled by `Mathlib.Tactic`); and
`H.rank` dot-notation resolves to `Function.rank` (Matrix unfolds to a function type) — write `Matrix.rank H`.

## Audit side (exact-rational): the lemma applies to a real beyond-Markov process

The **even process's** word-Hankel factors through ℚ² straight from its 2-dim OOM: `F[u]=π T_u`, `B[v]=T_v 1`,
and `H[u,v]=P(uv)=F[u]·B[v]` verified for all words up to length 3 ⇒ `rank(H) ≤ 2`. With a nonsingular 2×2
Hankel minor (det `1/18` ≠ 0, T8-a) ⇒ **rank(H) = 2 exactly**. Honest tiering (per the panel): the lemma is
Q.E.D.; the process's factorization is audit (full in-Lean identification is the F2b-scale follow-on).
Amplification, not discovery.

## What this closes

The beyond-Markov track (T8) now has the **complete rank story**, all kernel-verified and behind the unbroken
trust boundary:
- **rank ≥ r** — a nonsingular r-minor (T8-a, core-Lean `decide`).
- **rank ≤ r** — a linear-representation factorization (this lemma, Mathlib).
- **rank = r** — the two composed (`rank_eq_of_factor_of_ge`).
- **infinite Markov order** — a recurrence + induction bridge (T8-b).
- **positive realization > linear dimension** — a fooling-set certificate (T8-c, resolved as amplification).

All five are sound, kernel-verified, and honestly labeled amplification. The remaining slice is the F2b-scale
full in-Lean process identification (encode a process, derive its representation/recurrence from it) — the same
open follow-on named across T8-b/T8-c.

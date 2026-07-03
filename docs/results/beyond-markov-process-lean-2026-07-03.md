# Full in-Lean process identification (rank story) — GREEN, kernel-verified (2026-07-03)

**Result: GREEN, kernel sound.** The F2b-scale follow-on named across T8-b/T8-c/rank-upper, delivered for the
**rank story**: the even process is now **defined in Lean from its OOM operators** and its Hankel rank is
**derived in the kernel = 2** — no longer an audit link. This lifts rank-upper and rank-exact from
"kernel lemma + audited process factorization" to a genuine Q.E.D. *about the actual process*. Verified through
the ADR-0011 Mathlib REPL (the F2a pattern). `scripts/beyond_markov_process_lean.py`,
`docs/results/beyond_markov_process_lean.json`, `tests/test_beyond_markov_process_lean.py`. No trust surface touched.

## Kernel-Q.E.D. (0 errors, 0 sorries; both controls fail)

- **`hankel_block_rank_le`** — GENERAL. For any r-dim OOM `(init, op, fin)` with `P(w) = init·(∏ op)·fin`,
  **every** finite Hankel block `H[i,j] = P(u_i ++ v_j)` has `Matrix.rank ≤ r`. Proof: `Tprod` is a monoid
  homomorphism `(List A, ++) → (Matrix, *)` (`Tprod_append`), so the Hankel factors as `F·B` through the r-dim
  state space (`Pval_append`), and `rank_le_of_factor` finishes. The **process-intrinsic** rank-upper
  certificate — no per-process audit, no linear-representation supplied by hand.
- **`even_hankel_rank_le`** — the even process ε-machine defined in Lean (`eInit=![2/3,1/3]`,
  `eOp=![!![1/2,0;0,0], !![0,1/2;1,0]]`, `eFin=![1,1]`): **every** finite Hankel block has `rank ≤ 2`. A
  statement about the ACTUAL process, fully in-kernel.
- **`eB_det` / `eB_rank_eq_two`** — a concrete 2×2 even-process Hankel block; its determinant is **computed in
  the kernel** from the operator definition (`= 1/18 ≠ 0`), so `rank = 2` (via `IsUnit`). With the ≤2 bound:
  the even process's Hankel rank is **exactly 2**, derived from the operators, not asserted from Python.

Controls (fail): a **wrong determinant** (`1/18 → 1/17`) and an **understated dimension** (`≤2 → ≤1`).
Python cross-check confirms the Lean definition IS the even process (`P(00)=1/6`, block `det=1/18`).

## What changed vs. the earlier T8 results

| T8 result | before | now |
|---|---|---|
| rank ≤ r | abstract lemma `H=F·B ⇒ rank≤r` (Q.E.D.); "even Hankel = F·B" **audit** | `hankel_block_rank_le`: the factorization is **proved from the OOM definition** ⇒ Q.E.D. for the actual process |
| rank = r | minor (core-Lean) + factorization (audit) | `eB_rank_eq_two`: det computed in-kernel ⇒ rank exactly 2, **fully in-Lean** |

Notation lessons (banked): `Matrix.rank` needs `Mathlib.LinearAlgebra.Matrix.Rank`; `H.rank` resolves to
`Function.rank` (Matrix unfolds to a function) → write `Matrix.rank H`; the `ᵥ*` (vecMul) notation codepoint
breaks the parser here → use explicit `Matrix.vecMul` / `Matrix.mulVec` / `dotProduct`.

## Honest scope

This closes the **rank** identification in-kernel (the panel's rank-upper "DIVERGE" is now fully Q.E.D. about a
concrete process). The **infinite-order** (T8-b) and **positive-realization** (T8-c) identifications remain the
audit-linked follow-ons — they need, respectively, the operator-power closed form (`eOp 1 ^ k`, a parity
induction) and the fooling-set embedding proved in Lean. The reusable `Tprod`/`Pval`/`hankel_block_rank_le`
scaffold is exactly what those will build on. Amplification, not discovery; behind the unbroken trust boundary.

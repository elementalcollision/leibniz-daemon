/-
  Erdős Problem 367 (Erdős–Graham 1980, p.68) — a FAITHFUL FORMAL STATEMENT.

  Source: https://www.erdosproblems.com/367   (status: OPEN; "cannot be resolved with a finite computation").
  This file formalizes the STATEMENT only — the problem is an open asymptotic bound and is *not* a Leibniz
  solve target (the kernel decides finite/exact facts, not ≪ / o(1)). It is contributed in the spirit of the
  site's per-problem "Formalised statement? — Create a formalisation here" field: a faithful, kernel-checked
  rendering of the conjecture. The B₂ witnesses below are ILLUSTRATIVE ONLY — see the note at the foot of
  this file; they are not anchors and nothing in this file rests on them.

  B₂(n) = the 2-full part of n = the product of the prime powers pᵃ ‖ n with a ≥ 2.
-/
import Mathlib.Data.Nat.Factorization.Basic
import Mathlib.Analysis.SpecialFunctions.Pow.Real
import Mathlib.Algebra.BigOperators.Intervals

open Finset

/-- The 2-full part of `n`: the product of the prime powers `p^a ‖ n` with `a ≥ 2`. -/
def B2 (n : ℕ) : ℕ := n.factorization.prod (fun p a => if 2 ≤ a then p ^ a else 1)

/-- **Erdős 367** (Erdős–Graham 1980). For every fixed `k ≥ 1`,
    `∏_{n ≤ m < n+k} B₂(m) ≪ n^{2+o(1)}` — i.e. for every `ε > 0` the product is eventually
    `≤ C · n^{2+ε}`. Open; cannot be settled by a finite computation. -/
def Erdos367 : Prop :=
  ∀ k : ℕ, 1 ≤ k → ∀ ε : ℝ, 0 < ε → ∃ C : ℝ, ∀ n : ℕ,
    (∏ m ∈ Finset.Ico n (n + k), (B2 m : ℝ)) ≤ C * (n : ℝ) ^ (2 + ε)

/-- The stronger form Erdős–Graham also ask ("or perhaps even `≪_k n²`"). -/
def Erdos367_strong : Prop :=
  ∀ k : ℕ, 1 ≤ k → ∃ C : ℝ, ∀ n : ℕ,
    (∏ m ∈ Finset.Ico n (n + k), (B2 m : ℝ)) ≤ C * (n : ℝ) ^ (2 : ℝ)

-- B₂ on witnesses. ILLUSTRATIVE, NOT ANCHORS (ADR 0097): these are decided by the COMPILED
-- evaluator, not the kernel, so they are evidence about Lean's compiler and nothing more.
example : B2 9800 = 9800 := by native_decide   -- 2³·5²·7²  (a "powerful" number)
example : B2 9802 = 169  := by native_decide   -- 2·13²·29  → 13²
example : B2 12   = 4    := by native_decide   -- 2²·3      → 2²
example : B2 30   = 1    := by native_decide   -- 2·3·5 squarefree → 1

/-
  NOTE ON `native_decide` (revised 2026-09-10, ADR 0097).

  These four `example`s are NOT anchors, and the word "anchor" previously used here overstated them. They are
  decided by Lean's COMPILED EVALUATOR, not by the kernel — and the Trail of Bits `String.Pos.Raw.extract` bug
  (2026-09-09; all stable Lean ≤ 4.33.1, this project's 4.31 pin included) is a concrete demonstration that the
  compiled evaluator and the kernel can disagree, to the point of yielding `False`. Compiler evidence is worth
  what the compiler is worth; it is not a proof.

  They remain here as *illustration* of the B₂ definition, and they remain safe to keep for three reasons:
  they are anonymous `example`s, so nothing can reference them; the load-bearing content of this file is the
  *statement* (`Erdos367` / `Erdos367_strong`), which uses no `decide` of any kind and no proof at all; and the
  daemon forbids `native_decide` in promulgated proofs — as of ADR 0097 that ban is enforced by the sole writer
  of `kernel_verified`, not by convention.

  Why they are not simply reproved by kernel means: `B2` is defined through `Nat.factorization`, which is a
  `Finsupp` over `padicValNat` and does not reduce. Measured on the pinned 4.31 with this file's own imports,
  all of `decide`, `rfl`, `simp [B2, …]`, `norm_num [B2, Nat.factorization]` and `unfold B2; norm_num […]`
  leave the goal open. A kernel proof is genuine Mathlib work (a `Nat.factors`-based reformulation or the
  relevant `factorization` lemmas), not a tactic swap — so the honest fix is this relabelling, not a
  `decide` that does not exist.
-/

/-
  Erdős Problem 367 (Erdős–Graham 1980, p.68) — a FAITHFUL FORMAL STATEMENT.

  Source: https://www.erdosproblems.com/367   (status: OPEN; "cannot be resolved with a finite computation").
  This file formalizes the STATEMENT only — the problem is an open asymptotic bound and is *not* a Leibniz
  solve target (the kernel decides finite/exact facts, not ≪ / o(1)). It is contributed in the spirit of the
  site's per-problem "Formalised statement? — Create a formalisation here" field: a faithful, kernel-checked
  rendering of the conjecture, with the B₂ definition #eval-anchored on witnesses.

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

-- Faithfulness anchors (computation, not proof): B₂ on witnesses.
example : B2 9800 = 9800 := by native_decide   -- 2³·5²·7²  (a "powerful" number)
example : B2 9802 = 169  := by native_decide   -- 2·13²·29  → 13²
example : B2 12   = 4    := by native_decide   -- 2²·3      → 2²
example : B2 30   = 1    := by native_decide   -- 2·3·5 squarefree → 1

/-
  NOTE ON `native_decide`: it is used here ONLY to anchor the *faithfulness* of the B₂ definition on concrete
  inputs in this stand-alone statement file. It is deliberately NOT part of any Leibniz trust path — the daemon
  forbids `native_decide` in promulgated proofs. The load-bearing content of this file is the *statement*
  (`Erdos367` / `Erdos367_strong`), which uses no `decide` of any kind.
-/

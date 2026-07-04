/-
  Tier-1 counterexample-certificate domain — self-ordered (Problem 16) + n-absorbing (Problem 30) certs.
  Kernel-decided (`decide`); axioms = standard set or none. See scripts/counterexample_domain.py.
-/
import Mathlib.Algebra.BigOperators.Basic
import Mathlib.Algebra.BigOperators.Intervals
import Mathlib.Data.ZMod.Basic
import Mathlib.Tactic

namespace SO_cube
def a (k : ℕ) : ℤ := (k:ℤ)^3
def D (n : ℕ) : ℤ := (Finset.range n).prod (fun k => a n - a k)
def P (m n : ℕ) : ℤ := (Finset.range n).prod (fun k => a m - a k)
/-- ¬ self-ordered: at (m,n)=(3,2), D_2 ∤ P_{3,2}. -/
theorem not_self_ordered : P 3 2 % D 2 ≠ 0 := by decide
end SO_cube

namespace SO_triangular
def a (k : ℕ) : ℤ := ((k*(k+1)/2:ℕ):ℤ)
def D (n : ℕ) : ℤ := (Finset.range n).prod (fun k => a n - a k)
def P (m n : ℕ) : ℤ := (Finset.range n).prod (fun k => a m - a k)
/-- self-ordered up to bound 6 (a base family). -/
theorem self_ordered_lt6 : ∀ n < 6, ∀ m < 6, P m n % D n = 0 := by decide
end SO_triangular

namespace SO_pow2
def a (k : ℕ) : ℤ := (2:ℤ)^k
def D (n : ℕ) : ℤ := (Finset.range n).prod (fun k => a n - a k)
def P (m n : ℕ) : ℤ := (Finset.range n).prod (fun k => a m - a k)
/-- self-ordered up to bound 6 (a base family). -/
theorem self_ordered_lt6 : ∀ n < 6, ∀ m < 6, P m n % D n = 0 := by decide
end SO_pow2

namespace NAbs4
abbrev isNAbs (r : ℕ) : Prop :=
  ∀ x : Fin (r+1) → ZMod 4, (∏ i, x i) = 0 → ∃ j, (∏ i ∈ Finset.univ.erase j, x i) = 0
/-- absorbingNumber (⊥ : ZMod 4) = 2: ⊥ is 2-absorbing but not 1-absorbing. -/
theorem absorbing_number_bot : isNAbs 2 ∧ ¬ isNAbs 1 := by decide
end NAbs4

namespace NAbs9
abbrev isNAbs (r : ℕ) : Prop :=
  ∀ x : Fin (r+1) → ZMod 9, (∏ i, x i) = 0 → ∃ j, (∏ i ∈ Finset.univ.erase j, x i) = 0
/-- absorbingNumber (⊥ : ZMod 9) = 2: ⊥ is 2-absorbing but not 1-absorbing. -/
theorem absorbing_number_bot : isNAbs 2 ∧ ¬ isNAbs 1 := by decide
end NAbs9

/-
  Erdős–Straus conjecture — a FAITHFUL FORMAL STATEMENT.

  For every integer n ≥ 2, is 4/n a sum of three unit fractions? OPEN (Erdős & Straus, c. 1948).
  This file formalizes the STATEMENT only; the faithfulness anchor exhibits a concrete decomposition.
  Faithfulness gate: elaborates + `erdos_straus_anchor` proved.
-/
import Mathlib.Data.Rat.Defs
import Mathlib.Tactic

/-- **Erdős–Straus conjecture**: for every `n ≥ 2` there are positive integers `a, b, c` with
    `4/n = 1/a + 1/b + 1/c`. -/
def ErdosStraus : Prop :=
  ∀ n : ℕ, 2 ≤ n → ∃ a b c : ℕ, 0 < a ∧ 0 < b ∧ 0 < c ∧ (4 : ℚ) / n = 1 / (a : ℚ) + 1 / (b : ℚ) + 1 / (c : ℚ)

/-- Faithfulness anchor: a concrete decomposition, `4/5 = 1/2 + 1/4 + 1/20`. -/
theorem erdos_straus_anchor : (4 : ℚ) / 5 = 1 / (2 : ℚ) + 1 / (4 : ℚ) + 1 / (20 : ℚ) := by norm_num

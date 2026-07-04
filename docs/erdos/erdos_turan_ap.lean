/-
  Erdős–Turán conjecture on arithmetic progressions — a FAITHFUL FORMAL STATEMENT.

  If the reciprocals of a set of positive integers sum to infinity, the set contains arbitrarily long
  arithmetic progressions. OPEN (Erdős & Turán, 1936; the primes case is Green–Tao).
  Faithfulness gate: elaborates + `et_ap_anchor` proved (the AP-in-a-set clause behaves).
-/
import Mathlib.Analysis.PSeries
import Mathlib.Tactic

/-- **Erdős–Turán on APs**: if `∑_{a ∈ A} 1/a` diverges (A ⊆ ℤ₊), then A contains arbitrarily long
    arithmetic progressions. -/
def ErdosTuranAP : Prop :=
  ∀ A : Set ℕ, (∀ a ∈ A, 0 < a) → ¬ Summable (fun a : A => (1 : ℝ) / (a : ℝ)) →
    ∀ k : ℕ, ∃ a d : ℕ, 0 < d ∧ ∀ i < k, (a + i * d) ∈ A

/-- Faithfulness anchor: the AP-in-a-set clause behaves — {0,2,4} contains the 3-term AP `0,2,4`. -/
theorem et_ap_anchor : ∃ a d : ℕ, 0 < d ∧ ∀ i < 3, (a + i * d) ∈ ({0, 2, 4} : Set ℕ) := by
  refine ⟨0, 2, by norm_num, ?_⟩
  intro i hi
  interval_cases i <;> norm_num

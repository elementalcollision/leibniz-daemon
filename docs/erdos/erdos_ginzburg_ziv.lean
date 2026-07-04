/-
  Erdős–Ginzburg–Ziv theorem — a FAITHFUL FORMAL STATEMENT.

  Among any 2n−1 integers there are n whose sum is divisible by n. RESOLVED (Erdős, Ginzburg & Ziv, 1961).
  Faithfulness gate: elaborates + `egz_anchor` proved (the n = 1 instance).
-/
import Mathlib.Algebra.BigOperators.Fin
import Mathlib.Tactic

/-- **Erdős–Ginzburg–Ziv**: for every `n ≥ 1` and every family of `2n−1` integers, some `n` of them have a
    sum divisible by `n`. -/
def ErdosGinzburgZiv : Prop :=
  ∀ n : ℕ, 0 < n → ∀ a : Fin (2 * n - 1) → ℤ,
    ∃ S : Finset (Fin (2 * n - 1)), S.card = n ∧ (n : ℤ) ∣ ∑ i ∈ S, a i

/-- Faithfulness anchor: the `n = 1` instance (2·1−1 = 1 integer; a size-1 subset; `1 ∣` anything). -/
theorem egz_anchor : ∀ a : Fin (2 * 1 - 1) → ℤ,
    ∃ S : Finset (Fin (2 * 1 - 1)), S.card = 1 ∧ (1 : ℤ) ∣ ∑ i ∈ S, a i :=
  fun _ => ⟨Finset.univ, by simp, one_dvd _⟩

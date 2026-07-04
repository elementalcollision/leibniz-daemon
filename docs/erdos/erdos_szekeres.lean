/-
  Erdős–Szekeres theorem — a FAITHFUL FORMAL STATEMENT, PROVED via Mathlib.

  An injective sequence of reals of length > r·s has a strictly-increasing subsequence of length > r or a
  strictly-decreasing one of length > s. RESOLVED (Erdős & Szekeres, 1935); it is `erdos_szekeres` in Mathlib.
  Faithfulness gate: elaborates + `erdos_szekeres_proof` (the statement IS a Mathlib theorem — proved, not
  merely stated).
-/
import Mathlib.Combinatorics.ErdosSzekeres

/-- **Erdős–Szekeres**: an injective `f : Fin n → ℝ` with `r·s < n` has a strictly-increasing subsequence of
    length `> r` or a strictly-decreasing subsequence of length `> s`. -/
def ErdosSzekeres : Prop :=
  ∀ (r s n : ℕ), r * s < n → ∀ (f : Fin n → ℝ), Function.Injective f →
    (∃ t : Finset (Fin n), r < t.card ∧ StrictMonoOn f ↑t) ∨
    (∃ t : Finset (Fin n), s < t.card ∧ StrictAntiOn f ↑t)

/-- Faithfulness anchor: the statement is exactly Mathlib's `erdos_szekeres` — hence PROVED. -/
theorem erdos_szekeres_proof : ErdosSzekeres :=
  fun _ _ _ h f hf => erdos_szekeres h f hf

/-
  Erdős Problem 477 (tiling complement) — a FAITHFUL FORMAL STATEMENT.

  Erdős & Graham asked whether the value set of an integer polynomial of degree ≥ 2 can have a "tiling
  complement" in ℤ. Peng, Tao, Wang, Yu & Liu (2026) answer YES for the thirteenth powers: there is a set
  A ⊂ ℤ such that every integer is uniquely `a + m¹³`. This file formalizes the STATEMENT only (the resolution
  is a Brownawell–Masser + Heath-Brown argument, out of scope for a kernel `decide`); the sanity lemma is a
  faithfulness anchor showing the definition really captures *unique* representation.

  Source statement: Peng et al. (2026), "Erdős problem 477", §1.1, Theorem 1.1 (from the public pipeline-math
  repository). Faithfulness gate: elaborates + `tiling_sanity` proved (no sorry).
-/
import Mathlib.Data.Int.Basic
import Mathlib.Tactic

/-- `A ⊂ ℤ` is a **tiling complement** for `B ⊂ ℤ` if every integer `n` has a *unique* representation
    `n = a + b` with `a ∈ A`, `b ∈ B`. -/
def IsTilingComplement (A B : Set ℤ) : Prop :=
  ∀ n : ℤ, ∃! p : ℤ × ℤ, p.1 ∈ A ∧ p.2 ∈ B ∧ p.1 + p.2 = n

/-- **Erdős 477** (Erdős–Graham; resolved affirmatively by Peng, Tao, Wang, Yu & Liu, 2026):
    the set of thirteenth powers has a tiling complement in ℤ. -/
def Erdos477 : Prop := ∃ A : Set ℤ, IsTilingComplement A {b : ℤ | ∃ m : ℤ, b = m ^ 13}

/-- Faithfulness anchor: the definition captures *unique* representation — `ℤ = univ ⊕ {0}` tiles. -/
theorem tiling_sanity : IsTilingComplement Set.univ {(0 : ℤ)} := by
  intro n
  refine ⟨(n, 0), ⟨trivial, rfl, by ring⟩, ?_⟩
  rintro ⟨a, b⟩ ⟨-, hb, hab⟩
  simp only [Set.mem_singleton_iff] at hb
  subst hb
  simp only [add_zero] at hab
  subst hab
  rfl

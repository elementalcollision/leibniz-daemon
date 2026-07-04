/-
  F2b engine lemma (F2b-M2): block-diagonal PSD-iff, kernel-DISCHARGED.
  #print axioms = [propext, Classical.choice, Quot.sound] (clean).
  Imports: Mathlib.LinearAlgebra.Matrix.PosDef, Mathlib.Data.Matrix.Block, Mathlib.Tactic
-/
import Mathlib.LinearAlgebra.Matrix.PosDef
import Mathlib.Data.Matrix.Block
import Mathlib.Tactic

theorem block_diag_posSemidef_iff {m n : Type*} [Fintype m] [Fintype n]
    (A : Matrix m m ℝ) (D : Matrix n n ℝ) :
    (Matrix.fromBlocks A 0 0 D).PosSemidef ↔ A.PosSemidef ∧ D.PosSemidef := by
  have key : ∀ (x : m → ℝ) (y : n → ℝ),
      star (Sum.elim x y) ⬝ᵥ (Matrix.fromBlocks A 0 0 D).mulVec (Sum.elim x y)
        = star x ⬝ᵥ A.mulVec x + star y ⬝ᵥ D.mulVec y := by
    intro x y
    simp only [Matrix.fromBlocks_mulVec, Matrix.zero_mulVec, add_zero, zero_add,
               Sum.elim_comp_inl, Sum.elim_comp_inr]
    simp [dotProduct, Fintype.sum_sum_type]
  constructor
  · intro h
    have hH := Matrix.isHermitian_fromBlocks_iff.mp h.1
    refine ⟨Matrix.PosSemidef.of_dotProduct_mulVec_nonneg hH.1 (fun x => ?_),
            Matrix.PosSemidef.of_dotProduct_mulVec_nonneg hH.2.2.2 (fun y => ?_)⟩
    · have hx := h.dotProduct_mulVec_nonneg (Sum.elim x 0)
      rw [key x 0] at hx; simpa using hx
    · have hy := h.dotProduct_mulVec_nonneg (Sum.elim 0 y)
      rw [key 0 y] at hy; simpa using hy
  · rintro ⟨hA, hD⟩
    apply Matrix.PosSemidef.of_dotProduct_mulVec_nonneg
    · rw [Matrix.isHermitian_fromBlocks_iff]
      exact ⟨hA.1, by simp, by simp, hD.1⟩
    · intro w
      have hsplit := key (w ∘ Sum.inl) (w ∘ Sum.inr)
      have hw : Sum.elim (w ∘ Sum.inl) (w ∘ Sum.inr) = w := by ext i; cases i <;> rfl
      rw [hw] at hsplit
      rw [hsplit]
      exact add_nonneg (hA.dotProduct_mulVec_nonneg _) (hD.dotProduct_mulVec_nonneg _)

#print axioms block_diag_posSemidef_iff

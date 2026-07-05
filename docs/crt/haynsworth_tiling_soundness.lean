/-
  Haynsworth / block-LDLᵀ tiling soundness — the once-proved lemma the large-block-PSD Schur-tiling path needs
  (ADR 0047 Option-3 "Half 1"; recorded follow-on from docs/results/psd-arithmetization-probe-findings-2026-07-05.md).

  Context. Leibniz kernel-certifies PSD-ness of Terwilliger-SDP dual blocks, but `decide` walls at ~order-60
  (fact-count Ω(N²); probes 7a/7c). The panel's charter-clean escape for order-130–414 blocks is to TILE:
  factor the block M = Lᴴ D L with D block-diagonal in ≤60-order pivots Bᵢ, kernel-decide each `Bᵢ ⪰ 0` with
  the existing `lowRankOK` primitive, kernel-RECOMPUTE the factorization identity (fail-closed — the factor
  (L,D) is an untrusted input the kernel never trusts), and conclude `M ⪰ 0` from a ONCE-PROVED lemma. This
  file is that lemma. Crucially it needs NO Schur-complement iff (Mathlib has none): the block-LDLᵀ identity
  makes M a SUM of CONGRUENCES of the pivots, and congruence + sum both preserve PSD.

  Trust note. This is a pure Mathlib theorem over ℝ — it touches NO trust surface (no `trust.py`/`verifiers.py`;
  it would merely be USED by a future, separately operator-gated tiling primitive). Kernel-verified axiom-clean
  (`#print axioms` = the standard set). LLMs propose nothing here; the Lean kernel checks the proof.
-/
import Mathlib.LinearAlgebra.Matrix.PosDef

open Matrix

/-- **Congruence preserves PSD** (the atomic step). If `D ⪰ 0` and `M = Lᴴ D L`, then `M ⪰ 0` — for ANY `L`,
    with no rank/positivity assumption on the factor. This is why the tiling certificate is fail-closed: the
    kernel recomputes the identity `M = Lᴴ D L`; a corrupted factor cannot make a non-PSD `M` pass. -/
theorem psd_of_congruence {n : Type*} [Fintype n] [DecidableEq n]
    {D L M : Matrix n n ℝ} (hD : D.PosSemidef) (hM : M = Lᴴ * D * L) : M.PosSemidef := by
  subst hM
  exact hD.conjTranspose_mul_mul_same L

/-- **Block-LDLᵀ / Haynsworth tiling soundness.** If `M` is a finite SUM of congruences of PSD pivots,
    `M = ∑ i ∈ s, (C i)ᴴ * B i * C i` with every `B i ⪰ 0`, then `M ⪰ 0`. This is exactly the Schur-tiling
    certificate: the pivots `B i` are the ≤60-order diagonal blocks (each kernel-decided PSD), the `C i` are the
    block-triangular factor rows, and `M` is the order-N block whose PSD-ness is thereby reduced to the small
    pivots + one recomputed identity — never forming the monolithic Ω(N²) `decide` goal that walls. -/
theorem psd_of_sum_congruence {n : Type*} [Fintype n] [DecidableEq n] {ι : Type*} (s : Finset ι)
    (B C : ι → Matrix n n ℝ) (hB : ∀ i ∈ s, (B i).PosSemidef)
    {M : Matrix n n ℝ} (hM : M = ∑ i ∈ s, (C i)ᴴ * B i * C i) : M.PosSemidef := by
  subst hM
  refine Finset.sum_induction _ (fun A : Matrix n n ℝ => A.PosSemidef)
    (fun _ _ ha hb => ha.add hb) Matrix.PosSemidef.zero ?_
  intro i hi
  exact (hB i hi).conjTranspose_mul_mul_same (C i)

#print axioms psd_of_congruence
#print axioms psd_of_sum_congruence

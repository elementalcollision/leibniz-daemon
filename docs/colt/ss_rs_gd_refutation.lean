/-
  SS-RS-GD refutation (Yun-Sra-Jadbabaie, COLT 2021 open problem) — kernel-verified core.
  Independent Leibniz attestation of a pipeline-math (GPT-5.5-Pro) resolution.
  Every theorem: #print axioms = [propext, Classical.choice, Quot.sound].
-/
import Mathlib.Tactic


namespace SSRSGD

noncomputable def lamRS (q : ℝ) : ℝ :=
  ((q^6 - 6*q^5 + 15*q^4 + 12*q^3 + 15*q^2 - 6*q + 1)/32)^2
noncomputable def lamSS (q : ℝ) : ℝ :=
  (q^12 - 24*q^11 + 186*q^10 - 504*q^9 + 399*q^8 + 528*q^7 + 876*q^6
    + 528*q^5 + 399*q^4 - 504*q^3 + 186*q^2 - 24*q + 1)/2048
noncomputable def muRS (q : ℝ) : ℝ :=
  (q+1)^4 * (q^4 + 4*q^3 - 42*q^2 + 4*q + 1)/16384
def gg (q : ℝ) : ℝ := 42*q^2 - q^4 - 4*q^3 - 4*q - 1

/-- Lemma 1.6, eq (1.8): the exact gap identity. -/
theorem gap_identity (q : ℝ) :
    lamSS q - lamRS q = (1 - q)^6 * (q + 1)^2 * gg q / 2048 := by
  unfold lamSS lamRS gg; ring

/-- Lemma 1.5 dominance eq (1.6). -/
theorem dominance_q6 (q : ℝ) :
    lamRS q - q^6
      = (1 - q)^6 * (q + 1)^2 * (q^4 - 8*q^3 + 30*q^2 - 8*q + 1) / 1024 := by
  unfold lamRS; ring

/-- SOS cofactor for (1.6). (An LLM scout wrongly flagged this as off by 2q²; the kernel confirms
    the paper: (q²−4q+1)² = q⁴−8q³+18q²−8q+1, so +12q² gives 30q².) -/
theorem sos_cofactor (q : ℝ) :
    q^4 - 8*q^3 + 30*q^2 - 8*q + 1 = (q^2 - 4*q + 1)^2 + 12*q^2 := by ring

/-- Second SOS cofactor (sextic), positive for q ≥ 0. -/
theorem sos_sextic (q : ℝ) :
    3*q^6 - 30*q^5 + 93*q^4 + 124*q^3 + 93*q^2 - 30*q + 3
      = 3*q^4*((q - 5)^2 + 6) + 124*q^3 + 3*(31*q^2 - 10*q + 1) := by ring

/-- Positivity of the gap's final factor on [1/4, 1] ⊂ (q*, 1], q* = 0.212036… -/
theorem gg_pos (q : ℝ) (h1 : (1:ℝ)/4 ≤ q) (h2 : q ≤ 1) : 0 < gg q := by
  unfold gg
  nlinarith [h1, h2, sq_nonneg (q - 1), sq_nonneg q, sq_nonneg (2*q - 1),
    mul_nonneg (sub_nonneg.2 h1) (sub_nonneg.2 h2)]

/-- THE REFUTATION on the violation interval [1/4, 1): λ_SS > λ_RS, so ‖W_SS‖ ≥ λ_SS > λ_RS = ‖W_RS‖.
    Conjecture 1.1 (the SS-RS inequality) is FALSE. -/
theorem ss_exceeds_rs (q : ℝ) (h1 : (1:ℝ)/4 ≤ q) (h2 : q < 1) : lamRS q < lamSS q := by
  have hg : 0 < gg q := gg_pos q h1 (le_of_lt h2)
  have h1q : 0 < 1 - q := by linarith
  have hq1 : 0 < q + 1 := by linarith
  have hpos : 0 < (1 - q)^6 * (q + 1)^2 * gg q / 2048 :=
    div_pos (mul_pos (mul_pos (pow_pos h1q 6) (pow_pos hq1 2)) hg) (by norm_num)
  have := gap_identity q
  linarith

/-- A fully concrete refutation witness: at q = 1/2, single-shuffle strictly beats reshuffle. -/
theorem violation_at_half : lamRS (1/2) < lamSS (1/2) := by
  unfold lamRS lamSS; norm_num

/-- **Erratum, kernel-attested.** The paper's *printed* dominance identity (1.7) does NOT hold: at q = 1/2,
    λ_RS − μ_RS differs from the displayed right-hand side. (Degree mismatch: the printed RHS is degree 12 with
    leading 15q¹²/16384, but λ_RS − μ_RS has leading 16q¹²/16384.) -/
theorem paper_eq_1_7_false_at_half :
    lamRS (1/2) - muRS (1/2)
      ≠ (1 - (1:ℝ)/2)^4 * (5*(1/2)^2 + 2*(1/2) + 5)
        * (3*(1/2)^6 - 30*(1/2)^5 + 93*(1/2)^4 + 124*(1/2)^3 + 93*(1/2)^2 - 30*(1/2) + 3) / 16384 := by
  unfold lamRS muRS; norm_num

/-- The inequality (1.7) is *meant* to establish, λ_RS ≥ μ_RS, still holds at the witness point —
    so the erratum is in the displayed factorization only, not the underlying claim. -/
theorem lamRS_ge_muRS_at_half : muRS (1/2) ≤ lamRS (1/2) := by
  unfold lamRS muRS; norm_num

end SSRSGD

#print axioms SSRSGD.gap_identity
#print axioms SSRSGD.ss_exceeds_rs
#print axioms SSRSGD.violation_at_half
#print axioms SSRSGD.sos_cofactor
#print axioms SSRSGD.paper_eq_1_7_false_at_half
#print axioms SSRSGD.lamRS_ge_muRS_at_half

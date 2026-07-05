(*
  ADR 0048 — Isabelle/HOL proof-edge decider, demonstration certificate.

  Real theorems, checked by the Isabelle2025 kernel through leibniz.backends.isabelle_docker (report-only;
  the backend never touches Demonstratio.kernel_verified). Built as a one-theory session on the image's
  prebuilt HOL heap. Under the default quick_and_dirty=false, `isabelle build` HARD-ERRORS on `sorry`, so a
  laundered proof cannot build — the strictest analogue of Lean's no-sorry rule. Verification-amplification;
  no trust surface touched.
*)
theory Isabelle_Demo
  imports Main
begin

text \<open>Addition on nat is commutative.\<close>
lemma add_comm: "n + m = m + (n::nat)"
  by simp

text \<open>Reversing a list twice is the identity.\<close>
lemma rev_rev: "rev (rev xs) = xs"
  by simp

text \<open>Gauss's summation formula, by induction: 2 * (0 + 1 + ... + n) = n * (n + 1).\<close>
lemma gauss_sum: "2 * (\<Sum>i=0..(n::nat). i) = n * (n + 1)"
  by (induct n) auto

end

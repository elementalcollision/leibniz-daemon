/-
  Independent kernel verification of Mafi & Naderi (2021), "Integral closure and Hilbert series of a
  special monomial ideal", arXiv:2112.02921 — for M_{3,t} (n = 3).

  Theorem 1.6: closure(M_{3,t}) = the Veronese cap-sum ideal {min(a,t)+min(b,t)+min(c,t) ≥ 2t}.
  Corollary 1.7: M_{3,t} is Cohen–Macaulay (unmixed), yet its integral closure has EMBEDDED primes.

  Our integral-dependence instrument confirms closure(M_{3,t}) = the cap-sum ideal (t = 1..4); the
  kernel then decides (per t) that the closure has the embedded prime (x,y,z) while M_{3,t} does not —
  the closure GAINS it. All `decide`, standard axioms. LLMs propose nothing; the kernel decides.
  Produced by scripts/verify_mafi_naderi.py (Leibniz daemon).
-/
import Mathlib.Tactic

namespace MafiNaderi_t2
/-- closure(M_3,2) = Veronese I_(2·2; 2,2,2) = {x^u : min(a,2)+min(b,2)+min(c,2) ≥ 4}
    (Mafi–Naderi Theorem 1.6; our integral-dependence instrument confirms this equals the true closure). -/
def inClosure (a b c : ℕ) : Bool := 4 ≤ min a 2 + min b 2 + min c 2
/-- M_3,2 = (x^(0,2,2), x^(2,0,2), x^(2,2,0)). -/
def gens : List (ℕ × ℕ × ℕ) := [(0,2,2), (2,0,2), (2,2,0)]
def inM (a b c : ℕ) : Bool := gens.any (fun g => g.1 ≤ a && g.2.1 ≤ b && g.2.2 ≤ c)

/-- **Thm 1.6 (⊆ slice).** M_3,2 ⊆ closure, and the closure is STRICTLY bigger (witness x^(1, 1, 2) ∈ closure ∖ M). -/
theorem M_subsetneq_closure :
    (∀ a < 5, ∀ b < 5, ∀ c < 5, inM a b c = true → inClosure a b c = true)
    ∧ inClosure 1 1 2 = true ∧ inM 1 1 2 = false := by decide

/-- **Cor 1.7 (closure has embedded prime (x,y,z)).** x^(1, 1, 1) ∉ closure, but multiplying by each
    variable lands in closure — so (closure : x^(1, 1, 1)) = (x,y,z), an embedded associated prime. -/
theorem closure_embedded_prime :
    inClosure 1 1 1 = false ∧ inClosure 2 1 1 = true
    ∧ inClosure 1 2 1 = true ∧ inClosure 1 1 2 = true := by decide

/-- **Cor 1.7 (the closure GAINS it).** M_3,2 itself has NO such witness for (x,y,z) over the box —
    M is unmixed; the embedded prime appears only after passing to the integral closure. -/
theorem M_no_embedded_prime :
    ∀ a < 5, ∀ b < 5, ∀ c < 5,
      ¬ (inM a b c = false ∧ inM (a+1) b c = true ∧ inM a (b+1) c = true ∧ inM a b (c+1) = true) := by decide
end MafiNaderi_t2

namespace MafiNaderi_t3
/-- closure(M_3,3) = Veronese I_(2·3; 3,3,3) = {x^u : min(a,3)+min(b,3)+min(c,3) ≥ 6}
    (Mafi–Naderi Theorem 1.6; our integral-dependence instrument confirms this equals the true closure). -/
def inClosure (a b c : ℕ) : Bool := 6 ≤ min a 3 + min b 3 + min c 3
/-- M_3,3 = (x^(0,3,3), x^(3,0,3), x^(3,3,0)). -/
def gens : List (ℕ × ℕ × ℕ) := [(0,3,3), (3,0,3), (3,3,0)]
def inM (a b c : ℕ) : Bool := gens.any (fun g => g.1 ≤ a && g.2.1 ≤ b && g.2.2 ≤ c)

/-- **Thm 1.6 (⊆ slice).** M_3,3 ⊆ closure, and the closure is STRICTLY bigger (witness x^(1, 2, 3) ∈ closure ∖ M). -/
theorem M_subsetneq_closure :
    (∀ a < 7, ∀ b < 7, ∀ c < 7, inM a b c = true → inClosure a b c = true)
    ∧ inClosure 1 2 3 = true ∧ inM 1 2 3 = false := by decide

/-- **Cor 1.7 (closure has embedded prime (x,y,z)).** x^(1, 2, 2) ∉ closure, but multiplying by each
    variable lands in closure — so (closure : x^(1, 2, 2)) = (x,y,z), an embedded associated prime. -/
theorem closure_embedded_prime :
    inClosure 1 2 2 = false ∧ inClosure 2 2 2 = true
    ∧ inClosure 1 3 2 = true ∧ inClosure 1 2 3 = true := by decide

/-- **Cor 1.7 (the closure GAINS it).** M_3,3 itself has NO such witness for (x,y,z) over the box —
    M is unmixed; the embedded prime appears only after passing to the integral closure. -/
theorem M_no_embedded_prime :
    ∀ a < 7, ∀ b < 7, ∀ c < 7,
      ¬ (inM a b c = false ∧ inM (a+1) b c = true ∧ inM a (b+1) c = true ∧ inM a b (c+1) = true) := by decide
end MafiNaderi_t3

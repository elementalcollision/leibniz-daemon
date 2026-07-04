/-
  Independent kernel verification of Ataka–Matsuoka (2026), "Normality of monomial ideals in three
  variables", arXiv:2602.01782v1, Example 4.7(2) (§4.3).  LLMs propose nothing; the Lean kernel decides.

  Example 4.7(2) states: "Let I = (x³,y³,z³,x²y,xy²,x²z,yz). Then I is a normal ideal by Theorem 3.1."
  This is an ERRATUM — I is NOT integrally closed, so it cannot be normal (a normal ideal satisfies
  I = Ī) and Theorem 3.1 (which requires I = Ī and μ(I) ≤ 7) does not apply as printed. The kernel
  witness: the monomial xz² is NOT in I, yet its square (xz²)² = x²z⁴ = (x²z)·(z³) IS in I². Since a
  monomial whose square lies in I² is integral over I (it satisfies X² − c = 0 with c ∈ I²), xz² lies
  in closure(I) ∖ I. Its integral closure has 8 minimal generators (μ(Ī) = 8 > 7).

  This is a slip in an ILLUSTRATIVE example (§4.3, reduction numbers) and is INDEPENDENT of the paper's
  Main Theorem, whose sharpness (the μ(I) ≤ 7 bound, witness closure(x⁷,y³,z²)) we independently verified
  and confirmed correct in Example 4.5.  The companion positive example 4.7(1), I = (x³,y²,z²,xy,xz,yz),
  IS normal — confirmed by our general monomial-ideal normality instrument (integral-dependence + RRV).

  All theorems `decide`, no axioms.  Produced by scripts/verify_ataka_matsuoka_47.py (Leibniz daemon).
-/
import Mathlib.Tactic

namespace AtakaMatsuoka47

/-- x^g divides x^u (componentwise ≤) — monomial ideal membership test. -/
def dvd (g : ℕ × ℕ × ℕ) (a b c : ℕ) : Bool := g.1 ≤ a && g.2.1 ≤ b && g.2.2 ≤ c

/-- Example 4.7(2):  I = (x³, y³, z³, x²y, xy², x²z, yz). -/
def gens : List (ℕ × ℕ × ℕ) := [(3,0,0), (0,3,0), (0,0,3), (2,1,0), (1,2,0), (2,0,1), (0,1,1)]
def inI (a b c : ℕ) : Bool := gens.any (fun g => dvd g a b c)
/-- x^u ∈ I² ⟺ some pair of generators sums ≤ u. -/
def inI2 (a b c : ℕ) : Bool :=
  gens.any (fun g => gens.any (fun h => dvd (g.1 + h.1, g.2.1 + h.2.1, g.2.2 + h.2.2) a b c))

/-- xz² = (1,0,2) is not in I (no generator divides it). -/
theorem xz2_not_in_I : inI 1 0 2 = false := by decide
/-- (xz²)² = x²z⁴ = (2,0,4) is in I² (it equals (x²z)·(z³)). -/
theorem xz2_squared_in_I2 : inI2 2 0 4 = true := by decide

/-- **Erratum (Example 4.7(2)).** xz² ∉ I but (xz²)² ∈ I², so xz² is integral over I and lies in
    closure(I) ∖ I: the ideal is NOT integrally closed, contrary to "I is a normal ideal by Theorem 3.1"
    as printed. Independent of the Main Theorem (Example 4.5 sharpness, verified separately). -/
theorem I2_not_integrally_closed : inI 1 0 2 = false ∧ inI2 2 0 4 = true := by decide

end AtakaMatsuoka47

/-
  Problem 41 (Cahen–Fontana–Frisch–Glaz / Swanson) — the triple (4,5,7) is NOT normal.
  Kernel-decided (`decide`), NO axiom dependencies. I = closure(x⁴,y⁵,z⁷);
  witness x²y⁴z⁵ ∈ closure(I²) \ I². Both collapsed and direct forms; see scripts/prob41_normality_lean.py.
-/
import Mathlib.Tactic

namespace Prob41_457
def wt (a b c : ℕ) : ℕ := 35*a + 28*b + 20*c

/-- **Collapsed form.** x^(2,4,5) ∈ I² ⟺ ∃ v ≤ (2,4,5) with 140 ≤ wt v ≤ 282−140 = 142
    (I = {wt ≥ 140} is an up-set and wt is linear). No such v exists, and wt(2,4,5)=282 ≥ 280,
    so x^2y^4z^5 ∈ closure(I²) \ I² — hence I = closure(x⁴,y⁵,z⁷) is NOT normal. -/
def inI2_collapsed : Bool :=
  (List.range 3).any fun a => (List.range 5).any fun b => (List.range 6).any fun c =>
    140 ≤ wt a b c && wt a b c ≤ 142
theorem four_five_seven_not_normal_collapsed :
    280 ≤ wt 2 4 5 ∧ inI2_collapsed = false := by decide

/-- **Direct form** (no collapse — the product definition of I²): no two monomials v,w ∈ I with
    x^v·x^w ∣ x^(2,4,5). Equivalent, and manifestly the definition of I²-membership. -/
def inIb (a b c : ℕ) : Bool := 140 ≤ wt a b c
def box (u1 u2 u3 : ℕ) : List (ℕ × ℕ × ℕ) :=
  (List.range (u1+1)).flatMap fun a => (List.range (u2+1)).flatMap fun b =>
    (List.range (u3+1)).map fun c => (a, b, c)
def inI2_direct (u1 u2 u3 : ℕ) : Bool :=
  (box u1 u2 u3).any fun v => (box u1 u2 u3).any fun w =>
    inIb v.1 v.2.1 v.2.2 && inIb w.1 w.2.1 w.2.2
      && v.1 + w.1 ≤ u1 && v.2.1 + w.2.1 ≤ u2 && v.2.2 + w.2.2 ≤ u3
theorem four_five_seven_not_normal_direct :
    280 ≤ wt 2 4 5 ∧ inI2_direct 2 4 5 = false := by decide
end Prob41_457


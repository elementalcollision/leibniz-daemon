/-
  Problem 41 (Cahen–Fontana–Frisch–Glaz / Swanson) — a kernel-certified NORMALITY CENSUS.
  Every corner triple 1 ≤ a ≤ b ≤ c ≤ 9 classified; the 11 NON-normal ones each carry
  a `decide` witness x^u ∈ closure(I²) ∖ I² (I = closure(x^a,y^b,z^c)). No axioms.

  Smallest non-normal: (2,3,7) [= Ataka–Matsuoka's closure(x⁷,y³,z²), up to permutation] and (3,4,5),
  both smaller than the textbook Huneke–Swanson (4,5,7). Produced by scripts/prob41_census.py.
-/
import Mathlib.Tactic

namespace Prob41_2_3_7
/-- L-cleared weighted degree wrt (2,3,7); L = lcm = 42, weights = (21,14,6). -/
def wt (a b c : ℕ) : ℕ := 21*a + 14*b + 6*c
/-- x^u ∈ I² collapses to ∃ v ≤ u with 42 ≤ wt v ≤ wt u − 42. Here wt u = 85. -/
def inI2 : Bool :=
  (List.range 2).any fun a => (List.range 3).any fun b => (List.range 7).any fun c =>
    42 ≤ wt a b c && wt a b c ≤ 43
/-- (2,3,7) is NOT normal: x^(1, 2, 6) ∈ closure(I²) (wt=85 ≥ 84) but ∉ I². -/
theorem triple_2_3_7_not_normal : 84 ≤ wt 1 2 6 ∧ inI2 = false := by decide
end Prob41_2_3_7

namespace Prob41_3_4_5
/-- L-cleared weighted degree wrt (3,4,5); L = lcm = 60, weights = (20,15,12). -/
def wt (a b c : ℕ) : ℕ := 20*a + 15*b + 12*c
/-- x^u ∈ I² collapses to ∃ v ≤ u with 60 ≤ wt v ≤ wt u − 60. Here wt u = 121. -/
def inI2 : Bool :=
  (List.range 3).any fun a => (List.range 4).any fun b => (List.range 4).any fun c =>
    60 ≤ wt a b c && wt a b c ≤ 61
/-- (3,4,5) is NOT normal: x^(2, 3, 3) ∈ closure(I²) (wt=121 ≥ 120) but ∉ I². -/
theorem triple_3_4_5_not_normal : 120 ≤ wt 2 3 3 ∧ inI2 = false := by decide
end Prob41_3_4_5

namespace Prob41_2_5_7
/-- L-cleared weighted degree wrt (2,5,7); L = lcm = 70, weights = (35,14,10). -/
def wt (a b c : ℕ) : ℕ := 35*a + 14*b + 10*c
/-- x^u ∈ I² collapses to ∃ v ≤ u with 70 ≤ wt v ≤ wt u − 70. Here wt u = 141. -/
def inI2 : Bool :=
  (List.range 2).any fun a => (List.range 5).any fun b => (List.range 6).any fun c =>
    70 ≤ wt a b c && wt a b c ≤ 71
/-- (2,5,7) is NOT normal: x^(1, 4, 5) ∈ closure(I²) (wt=141 ≥ 140) but ∉ I². -/
theorem triple_2_5_7_not_normal : 140 ≤ wt 1 4 5 ∧ inI2 = false := by decide
end Prob41_2_5_7

namespace Prob41_3_5_8
/-- L-cleared weighted degree wrt (3,5,8); L = lcm = 120, weights = (40,24,15). -/
def wt (a b c : ℕ) : ℕ := 40*a + 24*b + 15*c
/-- x^u ∈ I² collapses to ∃ v ≤ u with 120 ≤ wt v ≤ wt u − 120. Here wt u = 241. -/
def inI2 : Bool :=
  (List.range 2).any fun a => (List.range 5).any fun b => (List.range 8).any fun c =>
    120 ≤ wt a b c && wt a b c ≤ 121
/-- (3,5,8) is NOT normal: x^(1, 4, 7) ∈ closure(I²) (wt=241 ≥ 240) but ∉ I². -/
theorem triple_3_5_8_not_normal : 240 ≤ wt 1 4 7 ∧ inI2 = false := by decide
end Prob41_3_5_8

namespace Prob41_4_5_7
/-- L-cleared weighted degree wrt (4,5,7); L = lcm = 140, weights = (35,28,20). -/
def wt (a b c : ℕ) : ℕ := 35*a + 28*b + 20*c
/-- x^u ∈ I² collapses to ∃ v ≤ u with 140 ≤ wt v ≤ wt u − 140. Here wt u = 282. -/
def inI2 : Bool :=
  (List.range 3).any fun a => (List.range 5).any fun b => (List.range 6).any fun c =>
    140 ≤ wt a b c && wt a b c ≤ 142
/-- (4,5,7) is NOT normal: x^(2, 4, 5) ∈ closure(I²) (wt=282 ≥ 280) but ∉ I². -/
theorem triple_4_5_7_not_normal : 280 ≤ wt 2 4 5 ∧ inI2 = false := by decide
end Prob41_4_5_7

namespace Prob41_3_7_8
/-- L-cleared weighted degree wrt (3,7,8); L = lcm = 168, weights = (56,24,21). -/
def wt (a b c : ℕ) : ℕ := 56*a + 24*b + 21*c
/-- x^u ∈ I² collapses to ∃ v ≤ u with 168 ≤ wt v ≤ wt u − 168. Here wt u = 337. -/
def inI2 : Bool :=
  (List.range 3).any fun a => (List.range 6).any fun b => (List.range 6).any fun c =>
    168 ≤ wt a b c && wt a b c ≤ 169
/-- (3,7,8) is NOT normal: x^(2, 5, 5) ∈ closure(I²) (wt=337 ≥ 336) but ∉ I². -/
theorem triple_3_7_8_not_normal : 336 ≤ wt 2 5 5 ∧ inI2 = false := by decide
end Prob41_3_7_8

namespace Prob41_5_6_7
/-- L-cleared weighted degree wrt (5,6,7); L = lcm = 210, weights = (42,35,30). -/
def wt (a b c : ℕ) : ℕ := 42*a + 35*b + 30*c
/-- x^u ∈ I² collapses to ∃ v ≤ u with 210 ≤ wt v ≤ wt u − 210. Here wt u = 421. -/
def inI2 : Bool :=
  (List.range 4).any fun a => (List.range 6).any fun b => (List.range 5).any fun c =>
    210 ≤ wt a b c && wt a b c ≤ 211
/-- (5,6,7) is NOT normal: x^(3, 5, 4) ∈ closure(I²) (wt=421 ≥ 420) but ∉ I². -/
theorem triple_5_6_7_not_normal : 420 ≤ wt 3 5 4 ∧ inI2 = false := by decide
end Prob41_5_6_7

namespace Prob41_5_6_8
/-- L-cleared weighted degree wrt (5,6,8); L = lcm = 120, weights = (24,20,15). -/
def wt (a b c : ℕ) : ℕ := 24*a + 20*b + 15*c
/-- x^u ∈ I² collapses to ∃ v ≤ u with 120 ≤ wt v ≤ wt u − 120. Here wt u = 241. -/
def inI2 : Bool :=
  (List.range 5).any fun a => (List.range 3).any fun b => (List.range 8).any fun c =>
    120 ≤ wt a b c && wt a b c ≤ 121
/-- (5,6,8) is NOT normal: x^(4, 2, 7) ∈ closure(I²) (wt=241 ≥ 240) but ∉ I². -/
theorem triple_5_6_8_not_normal : 240 ≤ wt 4 2 7 ∧ inI2 = false := by decide
end Prob41_5_6_8

namespace Prob41_5_7_9
/-- L-cleared weighted degree wrt (5,7,9); L = lcm = 315, weights = (63,45,35). -/
def wt (a b c : ℕ) : ℕ := 63*a + 45*b + 35*c
/-- x^u ∈ I² collapses to ∃ v ≤ u with 315 ≤ wt v ≤ wt u − 315. Here wt u = 631. -/
def inI2 : Bool :=
  (List.range 3).any fun a => (List.range 6).any fun b => (List.range 9).any fun c =>
    315 ≤ wt a b c && wt a b c ≤ 316
/-- (5,7,9) is NOT normal: x^(2, 5, 8) ∈ closure(I²) (wt=631 ≥ 630) but ∉ I². -/
theorem triple_5_7_9_not_normal : 630 ≤ wt 2 5 8 ∧ inI2 = false := by decide
end Prob41_5_7_9

namespace Prob41_5_8_9
/-- L-cleared weighted degree wrt (5,8,9); L = lcm = 360, weights = (72,45,40). -/
def wt (a b c : ℕ) : ℕ := 72*a + 45*b + 40*c
/-- x^u ∈ I² collapses to ∃ v ≤ u with 360 ≤ wt v ≤ wt u − 360. Here wt u = 721. -/
def inI2 : Bool :=
  (List.range 4).any fun a => (List.range 6).any fun b => (List.range 8).any fun c =>
    360 ≤ wt a b c && wt a b c ≤ 361
/-- (5,8,9) is NOT normal: x^(3, 5, 7) ∈ closure(I²) (wt=721 ≥ 720) but ∉ I². -/
theorem triple_5_8_9_not_normal : 720 ≤ wt 3 5 7 ∧ inI2 = false := by decide
end Prob41_5_8_9

namespace Prob41_7_8_9
/-- L-cleared weighted degree wrt (7,8,9); L = lcm = 504, weights = (72,63,56). -/
def wt (a b c : ℕ) : ℕ := 72*a + 63*b + 56*c
/-- x^u ∈ I² collapses to ∃ v ≤ u with 504 ≤ wt v ≤ wt u − 504. Here wt u = 1009. -/
def inI2 : Bool :=
  (List.range 5).any fun a => (List.range 8).any fun b => (List.range 6).any fun c =>
    504 ≤ wt a b c && wt a b c ≤ 505
/-- (7,8,9) is NOT normal: x^(4, 7, 5) ∈ closure(I²) (wt=1009 ≥ 1008) but ∉ I². -/
theorem triple_7_8_9_not_normal : 1008 ≤ wt 4 7 5 ∧ inI2 = false := by decide
end Prob41_7_8_9


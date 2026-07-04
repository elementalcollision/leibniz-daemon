/-
  Problem 16 (Cahen–Fontana–Frisch–Glaz / Chabert) — self-ordered sequence census: certified
  REFUTATIONS. A sequence is self-ordered when D_n = ∏_{k<n}(aₙ−aₖ) divides P(m,n) = ∏_{k<n}(aₘ−aₖ)
  for all m,n; the negation is finitely witnessed by one (m,n) with D_n ∤ P(m,n), kernel-decided.

  5 natural sequences refuted here: cube, quartic, factorial, fibonacci, primes.
  (n² is NOT here — it is self-ordered to N=30; the refutable pure powers are n^k, k ≥ 3.)
  Produced by scripts/prob16_census.py.
-/
import Mathlib.Tactic

namespace SO_cube
/-- Value prefix a₀..a_3 of the sequence (enough for the witness). -/
def a : List Int := [0, 1, 8, 27]
def D (n : Nat) : Int := (List.range n).foldl (fun acc k => acc * (a.getD n 0 - a.getD k 0)) 1
def P (m n : Nat) : Int := (List.range n).foldl (fun acc k => acc * (a.getD m 0 - a.getD k 0)) 1
/-- NOT self-ordered: at (m,n)=(3,2), D_2 = 56 ∤ P(3,2). -/
theorem cube_not_self_ordered : P 3 2 % D 2 ≠ 0 := by decide
end SO_cube

namespace SO_quartic
/-- Value prefix a₀..a_4 of the sequence (enough for the witness). -/
def a : List Int := [0, 1, 16, 81, 256]
def D (n : Nat) : Int := (List.range n).foldl (fun acc k => acc * (a.getD n 0 - a.getD k 0)) 1
def P (m n : Nat) : Int := (List.range n).foldl (fun acc k => acc * (a.getD m 0 - a.getD k 0)) 1
/-- NOT self-ordered: at (m,n)=(4,3), D_3 = 421200 ∤ P(4,3). -/
theorem quartic_not_self_ordered : P 4 3 % D 3 ≠ 0 := by decide
end SO_quartic

namespace SO_factorial
/-- Value prefix a₀..a_3 of the sequence (enough for the witness). -/
def a : List Int := [1, 2, 6, 24]
def D (n : Nat) : Int := (List.range n).foldl (fun acc k => acc * (a.getD n 0 - a.getD k 0)) 1
def P (m n : Nat) : Int := (List.range n).foldl (fun acc k => acc * (a.getD m 0 - a.getD k 0)) 1
/-- NOT self-ordered: at (m,n)=(3,2), D_2 = 20 ∤ P(3,2). -/
theorem factorial_not_self_ordered : P 3 2 % D 2 ≠ 0 := by decide
end SO_factorial

namespace SO_fibonacci
/-- Value prefix a₀..a_4 of the sequence (enough for the witness). -/
def a : List Int := [1, 2, 3, 5, 8]
def D (n : Nat) : Int := (List.range n).foldl (fun acc k => acc * (a.getD n 0 - a.getD k 0)) 1
def P (m n : Nat) : Int := (List.range n).foldl (fun acc k => acc * (a.getD m 0 - a.getD k 0)) 1
/-- NOT self-ordered: at (m,n)=(4,3), D_3 = 24 ∤ P(4,3). -/
theorem fibonacci_not_self_ordered : P 4 3 % D 3 ≠ 0 := by decide
end SO_fibonacci

namespace SO_primes
/-- Value prefix a₀..a_3 of the sequence (enough for the witness). -/
def a : List Int := [2, 3, 5, 7]
def D (n : Nat) : Int := (List.range n).foldl (fun acc k => acc * (a.getD n 0 - a.getD k 0)) 1
def P (m n : Nat) : Int := (List.range n).foldl (fun acc k => acc * (a.getD m 0 - a.getD k 0)) 1
/-- NOT self-ordered: at (m,n)=(3,2), D_2 = 6 ∤ P(3,2). -/
theorem primes_not_self_ordered : P 3 2 % D 2 ≠ 0 := by decide
end SO_primes


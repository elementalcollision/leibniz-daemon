/-
  Independent kernel verification of the finite core of Erdős Problem 707 (Sidon-Extension Conjecture).

  Erdős's $1000 conjecture — every finite Sidon set extends to a finite perfect difference set (PDS) —
  was disproved by Alexeev & Mixon (arXiv:2510.19804) via {1,2,4,8,13} (and Hall's {1,3,9,10,13}); Niu
  (arXiv:2604.25214) gave size-4 candidates {0,1,3,11}, {0,1,4,11}. A PDS of order n has n(n−1)=v−1, so
  B ⊂ ℤ_v is a PDS iff its pairwise diffs mod v are distinct; non-extension at order n ⟺ no size-n
  superset of S is Sidon mod v. We kernel-decide: each set is Sidon (over ℤ), and each is non-extending
  for the small orders below (a finite slice of the paper's unconditional exhaustion). All `decide`,
  no axioms. LLMs propose nothing; the kernel decides. Produced by scripts/verify_erdos_707.py.
-/
import Mathlib.Tactic
set_option maxHeartbeats 800000

namespace Erdos707

/-- pairwise differences (over ℤ) of a list — a set is a Sidon set iff these are all distinct. -/
def diffsZ (S : List Int) : List Int :=
  S.flatMap (fun a => S.filterMap (fun b => if a == b then none else some (b - a)))
/-- pairwise differences mod v (as ℕ). -/
def diffsMod (S : List Nat) (v : Nat) : List Nat :=
  S.flatMap (fun a => S.filterMap (fun b => if a == b then none else some ((v + b - a) % v)))
/-- B (⊂ ℤ_v) is a perfect difference set iff it is a distinct set whose pairwise diffs mod v are all
    distinct — equivalently Sidon mod v (valid since a PDS of order n has n(n−1) = v−1). -/
def isPDS (B : List Nat) (v : Nat) : Bool := (diffsMod B v).Nodup && B.Nodup

/-! ### A = {0, 1, 3, 11} — Niu size-4. -/
theorem A_sidon : (diffsZ [0, 1, 3, 11]).Nodup := by decide
/-- A does not extend to a perfect difference set of order 4 (v = 13). -/
theorem A_no_order4 : isPDS [0, 1, 3, 11] 13 = false := by decide
/-- A does not extend to a perfect difference set of order 5 (v = 21). -/
theorem A_no_order5 : ∀ x0 < 21, isPDS ([0, 1, 3, 11] ++ [x0]) 21 = false := by decide

/-! ### B = {0, 1, 4, 11} — Niu size-4. -/
theorem B_sidon : (diffsZ [0, 1, 4, 11]).Nodup := by decide
/-- B does not extend to a perfect difference set of order 4 (v = 13). -/
theorem B_no_order4 : isPDS [0, 1, 4, 11] 13 = false := by decide
/-- B does not extend to a perfect difference set of order 5 (v = 21). -/
theorem B_no_order5 : ∀ x0 < 21, isPDS ([0, 1, 4, 11] ++ [x0]) 21 = false := by decide

/-! ### AM5 = {1, 2, 4, 8, 13} — Alexeev–Mixon size-5 (disproves Erdős 707). -/
theorem AM5_sidon : (diffsZ [1, 2, 4, 8, 13]).Nodup := by decide
/-- AM5 does not extend to a perfect difference set of order 5 (v = 21). -/
theorem AM5_no_order5 : isPDS [1, 2, 4, 8, 13] 21 = false := by decide
/-- AM5 does not extend to a perfect difference set of order 6 (v = 31). -/
theorem AM5_no_order6 : ∀ x0 < 31, isPDS ([1, 2, 4, 8, 13] ++ [x0]) 31 = false := by decide

/-! ### Hall = {1, 3, 9, 10, 13} — Hall 1947 size-5. -/
theorem Hall_sidon : (diffsZ [1, 3, 9, 10, 13]).Nodup := by decide
/-- Hall does not extend to a perfect difference set of order 5 (v = 21). -/
theorem Hall_no_order5 : isPDS [1, 3, 9, 10, 13] 21 = false := by decide
/-- Hall does not extend to a perfect difference set of order 6 (v = 31). -/
theorem Hall_no_order6 : ∀ x0 < 31, isPDS ([1, 3, 9, 10, 13] ++ [x0]) 31 = false := by decide

end Erdos707

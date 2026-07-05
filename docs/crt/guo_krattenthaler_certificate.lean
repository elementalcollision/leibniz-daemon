/-
  Independent kernel verification of Guo & Krattenthaler (2014), "Some divisibility properties of
  binomial and q-binomial coefficients", J. Number Theory 135, 167–184 (arXiv:1301.7651) — Phase 1.

  (A) Their new all-n divisibilities, certified for a range of n:
        (6n−1) ∣ C(12n,3n),  (6n−1) ∣ C(12n,4n),  (66n−1) ∣ C(330n,88n).
  (B) Sun's conjecture (confirmed by GK): if a has a prime factor not dividing b, there are ∞ many n
      with (bn+1) ∤ C((a+b)n, an); certified here by explicit non-divisibility witnesses.

  All theorems are decided by `decide` over exact Nat.choose (no axioms). LLMs propose nothing;
  the kernel decides. Produced by scripts/guo_krattenthaler_divisibility.py (Leibniz daemon).
-/
import Mathlib.Tactic
set_option maxRecDepth 8000

namespace GuoKrattenthaler

/-! ### (A) Guo–Krattenthaler all-n divisibilities (certified instances). -/
/-- (6·1 − 1) = 5 divides C(12, 3). -/
theorem div_12_3_n1 : (5 : ℕ) ∣ Nat.choose 12 3 := by decide
/-- (6·2 − 1) = 11 divides C(24, 6). -/
theorem div_12_3_n2 : (11 : ℕ) ∣ Nat.choose 24 6 := by decide
/-- (6·3 − 1) = 17 divides C(36, 9). -/
theorem div_12_3_n3 : (17 : ℕ) ∣ Nat.choose 36 9 := by decide
/-- (6·4 − 1) = 23 divides C(48, 12). -/
theorem div_12_3_n4 : (23 : ℕ) ∣ Nat.choose 48 12 := by decide
/-- (6·5 − 1) = 29 divides C(60, 15). -/
theorem div_12_3_n5 : (29 : ℕ) ∣ Nat.choose 60 15 := by decide
/-- (6·6 − 1) = 35 divides C(72, 18). -/
theorem div_12_3_n6 : (35 : ℕ) ∣ Nat.choose 72 18 := by decide
/-- (6·7 − 1) = 41 divides C(84, 21). -/
theorem div_12_3_n7 : (41 : ℕ) ∣ Nat.choose 84 21 := by decide
/-- (6·8 − 1) = 47 divides C(96, 24). -/
theorem div_12_3_n8 : (47 : ℕ) ∣ Nat.choose 96 24 := by decide
/-- (6·1 − 1) = 5 divides C(12, 4). -/
theorem div_12_4_n1 : (5 : ℕ) ∣ Nat.choose 12 4 := by decide
/-- (6·2 − 1) = 11 divides C(24, 8). -/
theorem div_12_4_n2 : (11 : ℕ) ∣ Nat.choose 24 8 := by decide
/-- (6·3 − 1) = 17 divides C(36, 12). -/
theorem div_12_4_n3 : (17 : ℕ) ∣ Nat.choose 36 12 := by decide
/-- (6·4 − 1) = 23 divides C(48, 16). -/
theorem div_12_4_n4 : (23 : ℕ) ∣ Nat.choose 48 16 := by decide
/-- (6·5 − 1) = 29 divides C(60, 20). -/
theorem div_12_4_n5 : (29 : ℕ) ∣ Nat.choose 60 20 := by decide
/-- (6·6 − 1) = 35 divides C(72, 24). -/
theorem div_12_4_n6 : (35 : ℕ) ∣ Nat.choose 72 24 := by decide
/-- (6·7 − 1) = 41 divides C(84, 28). -/
theorem div_12_4_n7 : (41 : ℕ) ∣ Nat.choose 84 28 := by decide
/-- (6·8 − 1) = 47 divides C(96, 32). -/
theorem div_12_4_n8 : (47 : ℕ) ∣ Nat.choose 96 32 := by decide
/-- (66·1 − 1) = 65 divides C(330, 88). -/
theorem div_330_88_n1 : (65 : ℕ) ∣ Nat.choose 330 88 := by decide

/-! ### (B) Sun's conjecture — non-divisibility witnesses (GK-confirmed). -/
/-- (a,b)=(2,1): a has a prime factor ∤ b, so ∃∞ n with (bn+1) ∤ C((a+b)n,an); witness n=1: (2) ∤ C(3,2). -/
theorem sun_nondiv_a2_b1 : ¬ ((2 : ℕ) ∣ Nat.choose 3 2) := by decide
/-- (a,b)=(3,1): a has a prime factor ∤ b, so ∃∞ n with (bn+1) ∤ C((a+b)n,an); witness n=2: (3) ∤ C(8,6). -/
theorem sun_nondiv_a3_b1 : ¬ ((3 : ℕ) ∣ Nat.choose 8 6) := by decide
/-- (a,b)=(3,2): a has a prime factor ∤ b, so ∃∞ n with (bn+1) ∤ C((a+b)n,an); witness n=1: (3) ∤ C(5,3). -/
theorem sun_nondiv_a3_b2 : ¬ ((3 : ℕ) ∣ Nat.choose 5 3) := by decide
/-- (a,b)=(4,3): a has a prime factor ∤ b, so ∃∞ n with (bn+1) ∤ C((a+b)n,an); witness n=1: (4) ∤ C(7,4). -/
theorem sun_nondiv_a4_b3 : ¬ ((4 : ℕ) ∣ Nat.choose 7 4) := by decide
/-- (a,b)=(5,2): a has a prime factor ∤ b, so ∃∞ n with (bn+1) ∤ C((a+b)n,an); witness n=2: (5) ∤ C(14,10). -/
theorem sun_nondiv_a5_b2 : ¬ ((5 : ℕ) ∣ Nat.choose 14 10) := by decide
/-- (a,b)=(2,3): a has a prime factor ∤ b, so ∃∞ n with (bn+1) ∤ C((a+b)n,an); witness n=1: (4) ∤ C(5,2). -/
theorem sun_nondiv_a2_b3 : ¬ ((4 : ℕ) ∣ Nat.choose 5 2) := by decide

end GuoKrattenthaler

/-
  Problem 16 (Cahen–Fontana–Frisch–Glaz / Chabert) — the POSITIVE side, PROVED (not bounded evidence).

  A sequence a : ℕ → ℤ is *self-ordered* when its n-th factorial D_n = ∏_{k<n}(aₙ − aₖ) divides
  P(m,n) = ∏_{k<n}(aₘ − aₖ) for all m, n — i.e. the natural order is a simultaneous ordering. This is an
  INFINITE condition; the census (scripts/prob16_census.py) can only refute it or give bounded evidence.
  Here we PROVE it, in the kernel, for two entire classes:

    • `arith_selfOrdered`  — EVERY arithmetic sequence aₙ = α + βn is self-ordered. Each factor scales by β,
       so D_n and P(m,n) pick up the SAME βⁿ and it reduces to the identity case (aₙ = n), where D_n = n!
       divides the product of n consecutive integers (`Nat.factorial_dvd_descFactorial`).
    • `geom_selfOrdered`   — EVERY geometric sequence aₙ = qⁿ (q : ℤ) is self-ordered. Factoring
       qⁿ − qᵏ = qᵏ(q^{n−k} − 1) reduces D_n | P(m,n) to a q-factorial divisibility: the Gaussian binomial
       coefficient is an integer. Mathlib has no Gaussian binomials, so we build them (`gBinom`, q-Pascal
       recurrence) and prove the product identity `gBinom · qf = ffall` by induction, giving `qf_dvd_ffall`.

  Corollaries instantiate the census's self-ordered sequences (n, 2n, 3+5n, 2ⁿ) as theorems, upgrading them
  from "self-ordered up to N=30 (evidence)" to proofs. Every proof is complete and depends only on the
  standard axioms (propext / Classical.choice / Quot.sound); no compiler-trusted shortcuts. Hand-written
  (the Gaussian-binomial machinery built from scratch), Leibniz daemon.
-/
import Mathlib.Tactic
import Mathlib.RingTheory.Polynomial.Pochhammer

open Finset

/-- `SelfOrdered a` : for all m,n, the factorial `D_n = ∏_{k<n}(aₙ−aₖ)` divides `P(m,n) = ∏_{k<n}(aₘ−aₖ)`. -/
def SelfOrdered (a : ℕ → ℤ) : Prop :=
  ∀ m n : ℕ, (∏ k ∈ range n, (a n - a k)) ∣ (∏ k ∈ range n, (a m - a k))

/-! ### Arithmetic sequences -/

/-- The identity sequence aₙ = n is self-ordered: `D_n = ∏_{k<n}(n−k) = n!` divides the product of any
    `n` consecutive integers `∏_{k<n}(m−k)`. -/
theorem identity_selfOrdered : SelfOrdered (fun j => (j : ℤ)) := by
  intro m n
  have hD : (∏ k ∈ range n, ((n : ℤ) - k)) = (n.factorial : ℤ) := by
    have h1 : (∏ k ∈ range n, ((n : ℤ) - k)) = ((n.descFactorial n : ℕ) : ℤ) := by
      rw [Nat.descFactorial_eq_prod_range, Nat.cast_prod]
      exact Finset.prod_congr rfl (fun k hk => by rw [Finset.mem_range] at hk; omega)
    rw [h1, Nat.descFactorial_self]
  simp only []
  rw [hD]
  by_cases h : n ≤ m
  · have h2 : (∏ k ∈ range n, ((m : ℤ) - k)) = ((m.descFactorial n : ℕ) : ℤ) := by
      rw [Nat.descFactorial_eq_prod_range, Nat.cast_prod]
      exact Finset.prod_congr rfl (fun k hk => by rw [Finset.mem_range] at hk; omega)
    rw [h2]; exact_mod_cast Nat.factorial_dvd_descFactorial m n
  · replace h : m < n := Nat.not_le.mp h
    have h3 : (∏ k ∈ range n, ((m : ℤ) - k)) = 0 :=
      Finset.prod_eq_zero (Finset.mem_range.mpr h) (by simp)
    rw [h3]; exact dvd_zero _

/-- Every arithmetic sequence aₙ = α + βn is self-ordered. Each factor `(α+βx) − (α+βk) = β(x−k)`, so `D_n`
    and `P(m,n)` both factor as `βⁿ · (identity factorial)`, and it reduces to `identity_selfOrdered`. -/
theorem arith_selfOrdered (α β : ℤ) : SelfOrdered (fun j => α + β * (j : ℤ)) := by
  intro m n
  have e : ∀ x : ℕ, (∏ k ∈ range n, ((α + β * (x : ℤ)) - (α + β * (k : ℤ))))
         = β ^ n * (∏ k ∈ range n, ((x : ℤ) - k)) := by
    intro x
    rw [show (∏ k ∈ range n, ((α + β * (x : ℤ)) - (α + β * (k : ℤ))))
          = (∏ k ∈ range n, (β * ((x : ℤ) - k))) from Finset.prod_congr rfl (fun k _ => by ring)]
    rw [Finset.prod_mul_distrib, Finset.prod_const, Finset.card_range]
  simp only []
  rw [e m, e n]
  exact mul_dvd_mul_left (β ^ n) (identity_selfOrdered m n)

/-! ### Geometric sequences — via a from-scratch Gaussian-binomial construction.

The ratio `P(m,n) / D_n` for `aₙ = qⁿ` is a Gaussian binomial coefficient, an integer. Mathlib has no
q-binomials, so we build `gBinom` (the q-Pascal recurrence, hence ℤ-valued) and prove the product identity
`gBinom q a n * qf q n = ffall q a n`, whence `qf q n ∣ ffall q a n`. -/

/-- Gaussian binomial coefficient `[a choose n]_q`, ℤ-valued via the q-Pascal recurrence. -/
def gBinom (q : ℤ) : ℕ → ℕ → ℤ
  | _,     0     => 1
  | 0,     (_+1) => 0
  | (a+1), (n+1) => gBinom q a n + q ^ (n+1) * gBinom q a (n+1)

/-- The q-factorial-ish product `φ_n = ∏_{j=1}^{n}(qʲ − 1)`. -/
def qf (q : ℤ) (n : ℕ) : ℤ := ∏ j ∈ range n, (q ^ (j+1) - 1)

/-- The falling q-product `∏_{i<n}(q^{a−i} − 1)`. -/
def ffall (q : ℤ) (a n : ℕ) : ℤ := ∏ i ∈ range n, (q ^ (a - i) - 1)

theorem ffall_succ_right (q : ℤ) (a n : ℕ) : ffall q a (n+1) = ffall q a n * (q ^ (a - n) - 1) := by
  simp [ffall, Finset.prod_range_succ]

theorem ffall_succ_left (q : ℤ) (a n : ℕ) : ffall q (a+1) (n+1) = (q ^ (a+1) - 1) * ffall q a n := by
  rw [ffall, Finset.prod_range_succ']
  simp only [Nat.succ_sub_succ, Nat.sub_zero]
  rw [ffall, mul_comm]

theorem qf_succ (q : ℤ) (n : ℕ) : qf q (n+1) = qf q n * (q ^ (n+1) - 1) := by
  simp [qf, Finset.prod_range_succ]

/-- The product identity `[a choose n]_q · φ_n = ∏_{i<n}(q^{a−i}−1)`, by induction on `a` (so the IH covers
    both terms of the q-Pascal recurrence). -/
theorem gBinom_qf (q : ℤ) : ∀ a n, gBinom q a n * qf q n = ffall q a n := by
  intro a
  induction a with
  | zero =>
    intro n
    cases n with
    | zero => simp [gBinom, qf, ffall]
    | succ n =>
      have : ffall q 0 (n+1) = 0 :=
        Finset.prod_eq_zero (mem_range.mpr (Nat.succ_pos n)) (by simp)
      simp [gBinom, this]
  | succ a ih =>
    intro n
    cases n with
    | zero => simp [gBinom, qf, ffall]
    | succ n =>
      have hrec : gBinom q (a+1) (n+1) = gBinom q a n + q ^ (n+1) * gBinom q a (n+1) := rfl
      rw [hrec, add_mul, qf_succ]
      rw [show gBinom q a n * (qf q n * (q ^ (n+1) - 1))
            = (gBinom q a n * qf q n) * (q ^ (n+1) - 1) by ring, ih n]
      rw [show q ^ (n+1) * gBinom q a (n+1) * (qf q n * (q ^ (n+1) - 1))
            = q ^ (n+1) * (gBinom q a (n+1) * qf q (n+1)) by rw [qf_succ]; ring, ih (n+1)]
      rw [ffall_succ_left, ffall_succ_right]
      by_cases hab : n ≤ a
      · have e : q ^ (n+1) * q ^ (a - n) = q ^ (a+1) := by rw [← pow_add]; congr 1; omega
        linear_combination (ffall q a n) * e
      · have h0 : ffall q a n = 0 :=
          Finset.prod_eq_zero (mem_range.mpr (by omega : a < n)) (by simp)
        rw [h0]; ring

/-- **The q-factorial divides the shifted product** (the Gaussian binomial is an integer). -/
theorem qf_dvd_ffall (q : ℤ) (a n : ℕ) : qf q n ∣ ffall q a n :=
  ⟨gBinom q a n, by rw [← gBinom_qf q a n]; ring⟩

theorem factor_prod (q : ℤ) (a n : ℕ) (h : n ≤ a) :
    (∏ k ∈ range n, (q ^ a - q ^ k)) = q ^ (∑ k ∈ range n, k) * ffall q a n := by
  rw [ffall, ← Finset.prod_pow_eq_pow_sum, ← Finset.prod_mul_distrib]
  refine Finset.prod_congr rfl (fun k hk => ?_)
  rw [Finset.mem_range] at hk
  have hka : k ≤ a := le_of_lt (lt_of_lt_of_le hk h)
  rw [mul_sub, mul_one, ← pow_add, show k + (a - k) = a from by omega]

theorem ffall_n_n_eq_qf (q : ℤ) (n : ℕ) : ffall q n n = qf q n := by
  rw [ffall, qf, ← Finset.prod_range_reflect]
  refine Finset.prod_congr rfl (fun i hi => ?_)
  rw [Finset.mem_range] at hi
  congr 2
  omega

/-- Every geometric sequence aₙ = qⁿ (q : ℤ) is self-ordered: `D_n = q^{C(n,2)}·φ_n` and
    `P(m,n) = q^{C(n,2)}·∏(q^{m−i}−1)` (or `0` if `m < n`), and `φ_n` divides the shifted product. -/
theorem geom_selfOrdered (q : ℤ) : SelfOrdered (fun j => q ^ j) := by
  intro m n
  simp only []
  by_cases hmn : n ≤ m
  · rw [factor_prod q n n (le_refl n), factor_prod q m n hmn, ffall_n_n_eq_qf]
    exact mul_dvd_mul_left _ (qf_dvd_ffall q m n)
  · have h0 : (∏ k ∈ range n, (q ^ m - q ^ k)) = 0 :=
      Finset.prod_eq_zero (mem_range.mpr (Nat.not_le.mp hmn)) (by simp)
    rw [h0]; exact dvd_zero _

/-! ### Corollaries — the census's self-ordered sequences, now as theorems. -/

/-- aₙ = n (the identity) is self-ordered. -/
theorem identity_is_arith : SelfOrdered (fun j => (j : ℤ)) := by
  simpa using arith_selfOrdered 0 1

/-- aₙ = 2n (the even numbers) is self-ordered. -/
theorem even_selfOrdered : SelfOrdered (fun j => 2 * (j : ℤ)) := by
  simpa using arith_selfOrdered 0 2

/-- aₙ = 3 + 5n (the census exemplar) is self-ordered. -/
theorem arith_3_5_selfOrdered : SelfOrdered (fun j => 3 + 5 * (j : ℤ)) :=
  arith_selfOrdered 3 5

/-- aₙ = 2ⁿ (the census's geometric exemplar) is self-ordered. -/
theorem pow2_selfOrdered : SelfOrdered (fun j => (2 : ℤ) ^ j) :=
  geom_selfOrdered 2

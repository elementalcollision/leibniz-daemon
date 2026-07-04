/-
  Problem 16 (Cahen–Fontana–Frisch–Glaz / Chabert) — the POSITIVE side, PROVED (not bounded evidence).

  A sequence a : ℕ → ℤ is *self-ordered* when its n-th factorial D_n = ∏_{k<n}(aₙ − aₖ) divides
  P(m,n) = ∏_{k<n}(aₘ − aₖ) for all m, n — i.e. the natural order is a simultaneous ordering. This is an
  INFINITE condition; the census (scripts/prob16_census.py) can only refute it or give bounded evidence.
  Here we PROVE it, in the kernel, for an entire class:

    • `identity_selfOrdered`  — the identity sequence aₙ = n is self-ordered (D_n = n! divides the product
       of n consecutive integers — `Nat.factorial_dvd_descFactorial`).
    • `arith_selfOrdered`     — EVERY arithmetic sequence aₙ = α + βn is self-ordered. Each factor scales by
       β, so D_n and P(m,n) pick up the SAME βⁿ and it reduces to the identity case.

  Corollaries instantiate the census's self-ordered arithmetic sequences (n, 2n, 3+5n), upgrading them from
  "self-ordered up to N=30 (evidence)" to theorems. Every proof is complete and depends only on the standard
  axioms (propext / Classical.choice / Quot.sound); no compiler-trusted shortcuts. Hand-written, Leibniz daemon.

  (Geometric aₙ = qⁿ is self-ordered too — the ratio is a Gaussian binomial in ℤ[q] — but that needs the
  q-binomial integrality and is left as future work.)
-/
import Mathlib.Tactic
import Mathlib.RingTheory.Polynomial.Pochhammer

open Finset

/-- `SelfOrdered a` : for all m,n, the factorial `D_n = ∏_{k<n}(aₙ−aₖ)` divides `P(m,n) = ∏_{k<n}(aₘ−aₖ)`. -/
def SelfOrdered (a : ℕ → ℤ) : Prop :=
  ∀ m n : ℕ, (∏ k ∈ range n, (a n - a k)) ∣ (∏ k ∈ range n, (a m - a k))

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

/-- Every arithmetic sequence aₙ = α + βn is self-ordered. Each factor `(α+βx) − (α+βk) = β(x−k)`, so both
    `D_n` and `P(m,n)` factor as `βⁿ · (identity factorial)`, and it reduces to `identity_selfOrdered`. -/
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

/-! ### Corollaries — the census's self-ordered arithmetic sequences, now as theorems. -/

/-- aₙ = n (the identity) is self-ordered. -/
theorem identity_is_arith : SelfOrdered (fun j => (j : ℤ)) := by
  simpa using arith_selfOrdered 0 1

/-- aₙ = 2n (the even numbers) is self-ordered. -/
theorem even_selfOrdered : SelfOrdered (fun j => 2 * (j : ℤ)) := by
  simpa using arith_selfOrdered 0 2

/-- aₙ = 3 + 5n (the census exemplar) is self-ordered. -/
theorem arith_3_5_selfOrdered : SelfOrdered (fun j => 3 + 5 * (j : ℤ)) :=
  arith_selfOrdered 3 5

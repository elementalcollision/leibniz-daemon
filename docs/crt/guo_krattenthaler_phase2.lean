/-
  Guo–Krattenthaler (2014), arXiv:1301.7651 — Phase 2 (the all-n theorem), PRIME-MODULUS case, PROVED.

  Guo & Krattenthaler prove that (6n−1) ∣ C(12n,3n), (6n−1) ∣ C(12n,4n), and (66n−1) ∣ C(330n,88n) for all
  n ≥ 1, via positivity of quotients of q-binomial coefficients by q-integers. The full (all-n) result is
  research-level; here we prove the PRIME-MODULUS case as a genuine all-n theorem (covering infinitely many n)
  by an elementary Kummer argument.

  The mechanism: when the modulus p (= 6n−1 or 66n−1) is prime, the base-p UNITS digits already force a carry.
  E.g. for C(12n,3n): 12n ≡ 2 (mod p) while 3n and (12n−3n)=9n reduce to 3n and 3n+1 (mod p), whose sum
  6n+1 ≥ p = 6n−1. By Kummer's theorem (`Nat.factorization_choose`) one carry suffices: v_p(C(12n,3n)) ≥ 1,
  so p ∣ C(12n,3n). The same units-carry closes all three cases.

  Every proof is complete and depends only on the standard axioms (propext / Classical.choice / Quot.sound);
  no compiler-trusted shortcuts. Hand-written, Leibniz daemon. (The composite-modulus case needs the full
  prime-power carry analysis / the q-integer positivity — the documented open escalation.)
-/
import Mathlib.Tactic

open Finset

/-- **Units-carry ⇒ prime divides binomial** — a specialization of Kummer's theorem to the units digit: if
    `p` is prime and the base-`p` units digits of `k` and `m − k` already sum to at least `p`, then a carry
    occurs in the units place, so `p ∣ C(m, k)`. -/
theorem prime_dvd_choose_of_units_carry {p m k : ℕ} (hp : Nat.Prime p) (hkm : k ≤ m)
    (hc : p ≤ k % p + (m - k) % p) : p ∣ Nat.choose m k := by
  have h2 := hp.two_le
  have hm : 0 < m := by
    rcases Nat.eq_zero_or_pos m with h | h
    · subst h; simp only [Nat.le_zero] at hkm; subst hkm; simp at hc; omega
    · exact h
  have hne : Nat.choose m k ≠ 0 := (Nat.choose_pos hkm).ne'
  rw [hp.dvd_iff_one_le_factorization hne,
      Nat.factorization_choose hp hkm (lt_of_le_of_lt (Nat.log_le_self _ _) (Nat.lt_succ_self m))]
  refine Finset.card_pos.mpr ⟨1, ?_⟩
  rw [Finset.mem_filter, Finset.mem_Ico]
  refine ⟨⟨le_refl 1, by omega⟩, ?_⟩
  simpa [pow_one] using hc

/-- **Guo–Krattenthaler, prime modulus.** For every `n ≥ 1` with `6n − 1` prime, `(6n − 1) ∣ C(12n, 3n)`. -/
theorem gk_12_3_prime (n : ℕ) (hn : 1 ≤ n) (hp : Nat.Prime (6 * n - 1)) :
    (6 * n - 1) ∣ Nat.choose (12 * n) (3 * n) := by
  refine prime_dvd_choose_of_units_carry hp (by omega) ?_
  have h1 : 3 * n % (6 * n - 1) = 3 * n := Nat.mod_eq_of_lt (by omega)
  have h2 : (12 * n - 3 * n) % (6 * n - 1) = 3 * n + 1 := by
    rw [show 12 * n - 3 * n = (3 * n + 1) + (6 * n - 1) * 1 from by omega, Nat.add_mul_mod_self_left,
        Nat.mod_eq_of_lt (by omega)]
  rw [h1, h2]; omega

/-- For every `n ≥ 1` with `6n − 1` prime, `(6n − 1) ∣ C(12n, 4n)`. -/
theorem gk_12_4_prime (n : ℕ) (hn : 1 ≤ n) (hp : Nat.Prime (6 * n - 1)) :
    (6 * n - 1) ∣ Nat.choose (12 * n) (4 * n) := by
  refine prime_dvd_choose_of_units_carry hp (by omega) ?_
  have h1 : 4 * n % (6 * n - 1) = 4 * n := Nat.mod_eq_of_lt (by omega)
  have h2 : (12 * n - 4 * n) % (6 * n - 1) = 2 * n + 1 := by
    rw [show 12 * n - 4 * n = (2 * n + 1) + (6 * n - 1) * 1 from by omega, Nat.add_mul_mod_self_left,
        Nat.mod_eq_of_lt (by omega)]
  rw [h1, h2]; omega

/-- For every `n ≥ 1` with `66n − 1` prime, `(66n − 1) ∣ C(330n, 88n)`. -/
theorem gk_330_88_prime (n : ℕ) (hn : 1 ≤ n) (hp : Nat.Prime (66 * n - 1)) :
    (66 * n - 1) ∣ Nat.choose (330 * n) (88 * n) := by
  refine prime_dvd_choose_of_units_carry hp (by omega) ?_
  have h1 : 88 * n % (66 * n - 1) = 22 * n + 1 := by
    rw [show 88 * n = (22 * n + 1) + (66 * n - 1) * 1 from by omega, Nat.add_mul_mod_self_left,
        Nat.mod_eq_of_lt (by omega)]
  have h2 : (330 * n - 88 * n) % (66 * n - 1) = 44 * n + 3 := by
    rw [show 330 * n - 88 * n = (44 * n + 3) + (66 * n - 1) * 3 from by omega, Nat.add_mul_mod_self_left,
        Nat.mod_eq_of_lt (by omega)]
  rw [h1, h2]; omega

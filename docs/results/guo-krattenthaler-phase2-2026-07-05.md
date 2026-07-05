# Independent kernel verification — Guo–Krattenthaler (2014), Phase 2: the all-`n` theorem (prime-modulus case)

**Date:** 2026-07-05 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (4/4 theorems kernel-verified, standard axioms)

## Target

Guo, V. J. W., & Krattenthaler, C. (2014). *Some divisibility properties of binomial and q-binomial
coefficients.* Journal of Number Theory, 135, 167–184 ([arXiv:1301.7651](https://arxiv.org/abs/1301.7651);
doi:10.1016/j.jnt.2013.08.012). The three headline **all-`n`** binomial divisibilities:

> `(6n−1) ∣ C(12n,3n)`, `(6n−1) ∣ C(12n,4n)`, `(66n−1) ∣ C(330n,88n)` for **all** `n ≥ 1`.

Phase 1 ([`guo-krattenthaler-divisibility-2026-07-05.md`](guo-krattenthaler-divisibility-2026-07-05.md))
certified these as a finite census of instances. Phase 2 lifts them to a genuine **all-`n` theorem** — over
an infinite family of `n` — and kernel-verifies it.

## The result Phase 2 proves

For each of the three divisibilities, **whenever the modulus is prime**, the divisibility holds for *every*
such `n`:

| Theorem | Statement (Lean) |
|---|---|
| `gk_12_3_prime` | `∀ n ≥ 1, (6n−1) prime → (6n−1) ∣ C(12n, 3n)` |
| `gk_12_4_prime` | `∀ n ≥ 1, (6n−1) prime → (6n−1) ∣ C(12n, 4n)` |
| `gk_330_88_prime` | `∀ n ≥ 1, (66n−1) prime → (66n−1) ∣ C(330n, 88n)` |

The prime-modulus `n` are infinite (Dirichlet: `6n−1` and `66n−1` each run through infinitely many primes) —
100 of the first 200 `n` give a prime `6n−1`, 75 give a prime `66n−1`. So this is a real all-`n` theorem over
an infinite subfamily, not a finite census.

## The mechanism: one carry, by Kummer

The proof is elementary and lives in `prime_dvd_choose_of_units_carry` (a specialization of Kummer's theorem
to the **units digit**). Kummer: `v_p(C(m,k))` equals the number of carries when adding `k` and `m−k` in
base `p`. Mathlib packages the units-place instance as `Nat.factorization_choose`, whose carry-set includes
`i = 1` exactly when `p ≤ k mod p + (m−k) mod p`. So:

> **if `p` is prime and the base-`p` units digits of `k` and `m−k` already sum to `≥ p`, then `p ∣ C(m,k)`.**

For each GK case the units digits are forced, and their sum overshoots the modulus by a fixed amount:

- `C(12n,3n)` with `p = 6n−1`: `3n mod p = 3n`, `(12n−3n) mod p = 3n+1`, sum `6n+1 ≥ p`. ✓
- `C(12n,4n)` with `p = 6n−1`: `4n mod p = 4n`, `(12n−4n) mod p = 2n+1`, sum `6n+1 ≥ p`. ✓
- `C(330n,88n)` with `p = 66n−1`: `88n mod p = 22n+1`, `(330n−88n) mod p = 44n+3`, sum `66n+4 ≥ p`. ✓

One carry suffices for `v_p ≥ 1`, hence `p ∣ C`. The residues are pinned in Lean with `Nat.mod_eq_of_lt`
and `Nat.add_mul_mod_self_left` (writing each numerator as `remainder + modulus·quotient`), then `omega`
discharges the `≥ p` inequality.

## What Leibniz verified

LLMs propose nothing — the theorem statements are the paper's, and the Lean 4.31 kernel **decides** the proofs
(hand-written; the ensemble prover Goedel@Featherless was attempted first and 503'd, so the Kummer route was
taken directly). The verifier (`scripts/verify_gk_phase2.py`) elaborates the four theorems, confirms
`#print axioms` returns only the standard set `{propext, Classical.choice, Quot.sound}` on each (no `sorryAx`),
and independently cross-checks the arithmetic: over `n ≤ 200`, every prime-modulus `n` in all three cases
actually satisfies the divisibility (a caught error would be any that didn't — none found).

## Honest scope — what remains open

The **composite-modulus** case is *not* covered here and is genuinely research-level. When `6n−1` is composite
the units-digit carry argument no longer decides divisibility on its own — one needs the prime-power carry
analysis for each prime factor, which is exactly what Guo–Krattenthaler obtain from the **positivity of the
quotient of q-binomial coefficients by the q-integer `[6n−1]_q`** (the q-machinery Phase 1 flagged, and the
from-scratch Gaussian-binomial toolkit built for CFFG Problem 16). We also confirmed (by computation) that
**no fixed integer-combination-of-binomials closed form** reproduces the quotient across all `n`. So:

- **Prime modulus:** proved for all such `n` (this document). ✓
- **Composite modulus / full all-`n`:** documented open escalation — needs the q-integer positivity route.

No trust surface touched — read-only kernel elaborations, `tests/test_invariants.py` byte-identical.

## Artifacts

- Certificate (downloadable): `docs/crt/guo_krattenthaler_phase2.lean` — 4 theorems (1 helper + 3 GK cases)
- Producer / verifier: `scripts/verify_gk_phase2.py` · Tests: `tests/test_gk_phase2.py`
- Result record: `docs/results/gk_phase2_verification.json`

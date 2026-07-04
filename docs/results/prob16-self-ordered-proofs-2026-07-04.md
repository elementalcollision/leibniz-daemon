# Problem 16 — the positive side, PROVED (arithmetic sequences are self-ordered)

**Date:** 2026-07-04 · **Track:** T9 (external open-problem corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (4/4 theorems kernel-elaborated, standard axioms, 0 sorry)

## Context

CFFG **Problem 16** (Chabert) asks for the "natural" self-ordered integer sequences. A sequence `a : ℕ → ℤ`
is **self-ordered** when its factorial `D_n = ∏_{k<n}(aₙ − aₖ)` divides `P(m,n) = ∏_{k<n}(aₘ − aₖ)` for all
`m, n`. This is an **infinite** condition — the census
([`prob16-self-ordered-census`](prob16-self-ordered-census-2026-07-04.md)) can only *refute* it (a finite
witness) or give bounded evidence for the positive cases. Here we cross that line and **prove** the positive
side for an entire class, in the kernel.

## What was proved

Hand-written Lean 4 proofs (`docs/crt/prob16_self_ordered_proofs.lean`), all depending only on the standard
axioms (`propext / Classical.choice / Quot.sound`), no `sorry`, no compiler-trusted shortcuts:

- **`identity_selfOrdered`** — the identity sequence `aₙ = n` is self-ordered. `D_n = ∏_{k<n}(n−k) = n!`
  (via `Nat.descFactorial_self`), and `n!` divides the product of any `n` consecutive integers
  `∏_{k<n}(m−k)` (via `Nat.factorial_dvd_descFactorial`; when `m < n` the product has a zero factor). The
  ℤ-product equals the ℕ descending factorial exactly because the only sign issues arise alongside a zero
  factor.
- **`arith_selfOrdered`** — **every** arithmetic sequence `aₙ = α + βn` is self-ordered. Each factor
  `(α+βx) − (α+βk) = β(x−k)`, so `D_n` and `P(m,n)` both factor as `βⁿ · (identity factorial)`; the shared
  `βⁿ` cancels and it reduces to `identity_selfOrdered` (`mul_dvd_mul_left`).
- Corollaries instantiate the census's self-ordered arithmetic sequences — `n`, `2n`, `3 + 5n` — as
  theorems, **upgrading them from "self-ordered up to N=30 (evidence)" to proofs**.

Together with the census refutations (n³, n⁴, factorial, Fibonacci, primes), Problem 16 now has both a
certified negative side and a proved positive class.

## How it was done — "in any way we can"

- **Handwritten** ✅ — identity + arithmetic, above (the shipped result).
- **Mechanical** — the harder **geometric** case `aₙ = qⁿ` (the ratio `P/D` is a Gaussian binomial in
  `ℤ[q]`, hence an integer) was routed to the wired Goedel-Prover-V2 (Featherless); it did not converge within
  the time budget (the q-binomial integrality is genuinely research-level for Lean). Left as future work — a
  hand proof would go through the q-factorial / `Nat.qBinomial` machinery.
- **Calculated** — the census supplies the empirical map that told us which sequences to prove vs. refute.

## Honest scope

`arith_selfOrdered` is fully general (all `α, β ∈ ℤ`). The geometric and other non-arithmetic self-ordered
classes are not yet proved. The classification of all "natural" self-ordered sequences is the open
mathematics and is not claimed. No trust surface is touched — `LeanVerifier.discharge` is untouched, these
are read-only kernel elaborations, and `tests/test_invariants.py` is byte-identical.

## Artifacts

- Certificate (downloadable): `docs/crt/prob16_self_ordered_proofs.lean` — 4 theorems, standard axioms
- Producer / verifier: `scripts/prob16_self_ordered_proofs.py` · Tests: `tests/test_prob16_self_ordered_proofs.py`
- Result record: `docs/results/prob16_self_ordered_proofs.json`

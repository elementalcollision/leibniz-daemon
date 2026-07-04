# Problem 16 — the positive side, PROVED (arithmetic AND geometric sequences are self-ordered)

**Date:** 2026-07-04 · **Track:** T9 (external open-problem corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (7/7 theorems kernel-elaborated, standard axioms, 0 sorry)

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
  `∏_{k<n}(m−k)` (via `Nat.factorial_dvd_descFactorial`; when `m < n` the product has a zero factor).
- **`arith_selfOrdered`** — **every** arithmetic sequence `aₙ = α + βn` is self-ordered. Each factor
  `(α+βx) − (α+βk) = β(x−k)`, so `D_n` and `P(m,n)` both factor as `βⁿ · (identity factorial)`; the shared
  `βⁿ` cancels and it reduces to `identity_selfOrdered`.
- **`geom_selfOrdered`** — **every** geometric sequence `aₙ = qⁿ` (`q : ℤ`) is self-ordered. Factoring
  `qⁿ − qᵏ = qᵏ(q^{n−k} − 1)` gives `D_n = q^{C(n,2)}·φ_n` and `P(m,n) = q^{C(n,2)}·∏(q^{m−i}−1)` (or `0` if
  `m < n`), reducing the claim to the **q-factorial divisibility** `φ_n ∣ ∏(q^{m−i}−1)` — the fact that the
  Gaussian binomial coefficient is an integer. **Mathlib has no Gaussian binomials**, so they are built from
  scratch: `gBinom` (the q-Pascal recurrence, hence ℤ-valued), the product identity
  `gBinom · φ_n = ∏(q^{a−i}−1)` proved by induction on `a` (the IH covers both q-Pascal terms), and
  `qf_dvd_ffall`.
- Corollaries instantiate the census's self-ordered sequences — `n`, `2n`, `3 + 5n`, **`2ⁿ`** — as theorems,
  **upgrading them from "self-ordered up to N=30 (evidence)" to proofs**.

Together with the census refutations (n³, n⁴, factorial, Fibonacci, primes), Problem 16 now has a certified
negative side and **two proved positive classes (arithmetic and geometric)**.

## How it was done — "in any way we can"

- **Handwritten** ✅ — identity, arithmetic, **and the geometric case** (the Gaussian-binomial machinery
  built from scratch), all shipped and kernel-verified.
- **Mechanical** — the geometric goal was first routed to the wired Goedel-Prover-V2 (Featherless); it did
  **not** converge in the time budget (504 gateway timeouts). We then closed it by hand with the q-factorial
  machinery below — the prover attempt is recorded honestly, not hidden.
- **Calculated** — the census supplied the empirical map (which sequences to prove vs. refute), and a
  numerical check confirmed the q-Pascal product identity before it was formalized.

## Honest scope

`arith_selfOrdered` (all `α, β ∈ ℤ`) and `geom_selfOrdered` (all `q : ℤ`) are fully general. Other
non-arithmetic/non-geometric self-ordered classes are not yet proved, and the classification of all "natural"
self-ordered sequences is the open mathematics — not claimed. No trust surface is touched:
`LeanVerifier.discharge` is untouched, these are read-only kernel elaborations, and `tests/test_invariants.py`
is byte-identical.

## Artifacts

- Certificate (downloadable): `docs/crt/prob16_self_ordered_proofs.lean` — 7 theorems (incl. the from-scratch Gaussian-binomial core), standard axioms
- Producer / verifier: `scripts/prob16_self_ordered_proofs.py` · Tests: `tests/test_prob16_self_ordered_proofs.py`
- Result record: `docs/results/prob16_self_ordered_proofs.json`

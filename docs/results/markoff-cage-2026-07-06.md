# Kernel-attested 2-adic divisibility placing the Markoff point (1,1,1) in the connected cage (Bellah–Dunn–Naidu–Wells 2025)

**Date:** 2026-07-06 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (exact integer arithmetic; Lean 4.31 `decide`)

## What this is

An independent, exact-arithmetic confirmation of the arithmetic core of a 2025 result in a domain new to the
ledger (**Diophantine / arithmetic geometry — Markoff triples**). The Markoff surface is
`X₁² + X₂² + X₃² = 3X₁X₂X₃`; the *Markoff mod p graph* `𝒢_p` has the nonzero mod `p` solutions as vertices and
the Vieta "rotations" as edges. Strong Approximation for Markoff triples (Bourgain–Gamburd–Sarnak) hinges on
connecting the reduction-fixed special point `(1,1,1)` to the provably connected **cage**. Bellah, Dunn, Naidu &
Wells ([arXiv:2511.23401](https://arxiv.org/abs/2511.23401), 2025) reduce this to a **2-adic property of a
rotation order**:

- the rotation order `ord_p(1,1,1)` equals the multiplicative order of `A = [[0,1],[-1,3]]` in `GL₂(F_p)` (the
  companion matrix of `f(T)=T²−3T+1`, discriminant `Δ = 9−4 = 5`);
- **Theorem 2.10** (at `(1,1,1)`): if `x=1` is elliptic (`Δ=5` a non-residue) and `((3·1+2)/p)=(5/p)=−1` — both
  hold exactly when `p ≡ ±2 (mod 5)` — then `2^{ν₂(p+1)} ∣ ord_p(1,1,1)`;
- **Proposition 3.3**: `ord_p(1,1,1) = π(p)/2`, half the Fibonacci **Pisano period** — a second, independent
  route.

## What Leibniz verified — two independent routes

By exact integer arithmetic over the primes `p ≡ ±2 (mod 5)` (15 primes from 7 to 113, plus the Mersenne primes
`7, 127, 524287, 2147483647`):

1. **Matrix order (self-contained).** `A^{p+1} ≡ I` forces `ord ∣ p+1` (the elliptic torus), and then
   `A^{(p+1)/2} ≢ I` forces `2^{ν₂(p+1)} ∣ ord`. Together these two facts **rigorously imply** the divisibility —
   no exact-order computation, and no external lemma, required. Verified for every prime.
2. **Pisano period.** Independently, `π(p)` computed from the Fibonacci recurrence mod `p` satisfies
   `ord(A) = π(p)/2` (Prop 3.3). The two routes **agree** on every prime up to `524287`.

For the **Mersenne primes** `p = 2ⁿ − 1` (all `≡ 2 mod 5` here: `n = 3,7,19,31`), `p+1 = 2ⁿ`, so `ν₂(p+1) = n`
and `ord(A) = p + 1` **exactly** — e.g. for `p = 2147483647 = 2³¹−1`, `ord = 2³¹ = 2147483648`.

**Negative control.** A prime `p ≡ ±1 (mod 5)` makes `x=1` *hyperbolic*; there `A^{p+1} ≢ I` (the order does
**not** divide `p+1`) for all eight control primes — so the ellipticity hypothesis of Theorem 2.10 is genuinely
load-bearing.

## The Lean kernel re-decides it

The **Lean 4.31 kernel** independently re-decides (plain `decide`, report-only) in
[`docs/crt/markoff_cage.lean`](../crt/markoff_cage.lean), with all arithmetic done by self-contained
fast-exponentiation / iteration on `Nat` 4-tuples — no baked data:

- `markoff_div_small` — the divisibility certificate `A^{p+1}=I ∧ A^{(p+1)/2}≠I` (with `p≡±2 mod 5`) for a
  spread of primes;
- `markoff_div_mersenne` — the same for the Mersenne primes `127, 524287, 2147483647` (`= 2³¹−1`);
- `markoff_pisano` — the second route: `ord(A) = π(p)/2` for `p ∈ {7,127}`, matrix order and Pisano period each
  computed by direct iteration;
- `markoff_control` — a prime `p ≡ ±1 (mod 5)` has `A^{p+1} ≠ I` (the negative control).

All four are `#print axioms`-clean — each **depends on no axioms at all** (pure `Nat`/`Bool`; no `native_decide`,
no `sorry`).

## Honest scope

This certifies the **arithmetic core** — the 2-adic divisibility and the Pisano identity for `(1,1,1)`, over a
finite (but open-ended) family of primes — that Theorem 2.10 uses to place `(1,1,1)` in the cage. It is **not** a
proof of Theorem 2.10 for all primes, nor of the graph-connectedness statement (Theorem 2.9 / Prop 2.8) itself;
those are general theorems, not finite objects. The Pisano cross-check is capped at `p ≤ 524287` (the direct
period iteration); the largest Mersenne prime `2³¹−1` is certified by the matrix route only. The backend is
**report-only**: nothing sets `kernel_verified` or touches `trust.py`; `tests/test_invariants.py` is
byte-identical.

## Artifacts

- Certificate (downloadable): [`docs/crt/markoff_cage.lean`](../crt/markoff_cage.lean) — Lean 4.31, four
  `decide` theorems.
- Producer / verifier: [`scripts/verify_markoff_cage.py`](../../scripts/verify_markoff_cage.py) ·
  Tests: [`tests/test_markoff_cage.py`](../../tests/test_markoff_cage.py)
- Result record: `docs/results/markoff_cage_verification.json`

## References

- Bellah, E., Dunn, C., Naidu, V., & Wells, A. (2025). *Connectedness of Special Points in the Markoff mod p
  Graphs* ([arXiv:2511.23401](https://arxiv.org/abs/2511.23401)).
- Bourgain, J., Gamburd, A., & Sarnak, P. (2016). *Markoff triples and strong approximation*. Comptes Rendus
  Mathématique, 354(2), 131–135.

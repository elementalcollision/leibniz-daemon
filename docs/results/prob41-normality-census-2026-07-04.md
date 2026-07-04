# Problem 41 — a kernel-certified corner-ideal normality census

**Date:** 2026-07-04 · **Track:** T9 (external open-problem corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (11/11 non-normal certificates kernel-clean, axiom-free)

## What this is

Cahen–Fontana–Frisch–Glaz **Problem 41** (Swanson) asks to classify the triples `(a,b,c)` for which
`I = closure(x^a, y^b, z^c)` in `k[x,y,z]` is **normal** (every power integrally closed). The full
classification is **open**. This is *not* a classification — it is a **certified census**: the exact
normal / not-normal verdict for **every** corner triple in a bounded box, each non-normal one carrying an
axiom-free kernel `decide` witness `x^u ∈ closure(I²) ∖ I²`.

The reusable checker `prob41_normality_lean.certify` (Newton polyhedron + Reid–Roberts–Vitulli `d = 3`
reduction) is exact-integer; the census is taken up to coordinate-permutation symmetry, i.e. over
`1 ≤ a ≤ b ≤ c ≤ 9`.

## Result (N = 9)

- **165** corner triples classified; **11** are not normal (~6%). Every non-normal one is kernel-decided,
  `#print axioms` → "does not depend on any axioms" (11/11).
- The 11 non-normal triples: `(2,3,7) (3,4,5) (2,5,7) (3,5,8) (4,5,7) (3,7,8) (5,6,7) (5,6,8) (5,7,9)
  (5,8,9) (7,8,9)`.

### The headline observation

The **two smallest** non-normal corner ideals (by `a+b+c = 12`) are **`(2,3,7)`** and **`(3,4,5)`** — both
strictly smaller than the textbook Huneke–Swanson `(4,5,7)` (`a+b+c = 16`). And **`(2,3,7)` is exactly the
Ataka–Matsuoka (2026) sharpness witness `closure(x⁷,y³,z²)` up to permutation** — so the sharpest
generator-count counterexample in their paper is, at the same time, the *minimal* non-normal corner ideal in
the `(a,b,c)` family. Two independent extremal characterizations meeting at one ideal.

### Empirical patterns (certified data, not proofs)

Across the census range, every non-normal corner triple:

- has **distinct coordinates** (no non-normal triple with a repeated exponent appears);
- has **`a ≥ 2`** (any `a = 1` triple — `x` itself a generator — is normal here);
- and **10 of 11 are pairwise-coprime** (the sole exception is `(5,6,8)`, `gcd(6,8) = 2`).

These are honest observations about the open classification, offered as certified instances — not a competing
classification.

## Artifacts

- Producer: `scripts/prob41_census.py` (reuses the `certify` / `lean_cert` instrument)
- Bundled certificate (downloadable): `docs/crt/prob41_census_certificate.lean` — 11 non-normality theorems,
  all `decide`, all axiom-free
- Result record: `docs/results/prob41_census.json` · Tests: `tests/test_prob41_census.py`
- The two minimal triples `(2,3,7)` (as `{7,3,2}`) and `(3,4,5)` are registered in the
  counterexample-certificate domain (`monomial_normal`, Tier 1).

## Honest scope

Certifying a *specific* triple is decidable; **classifying all triples is the open mathematics** and is not
claimed. The census is bounded (`N = 9`); the patterns above are observations within that box, not theorems.
No trust surface is touched — every verdict is read-only and kernel-decided.

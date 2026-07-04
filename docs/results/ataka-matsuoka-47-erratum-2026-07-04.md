# Ataka–Matsuoka (2026) Example 4.7 — a kernel-checkable erratum

**Date:** 2026-07-04 · **Track:** T5 (external audit instrument) / T9 (external corpus) ·
**Tier:** audit · **EV:** verification-amplification · **Gate:** GREEN (kernel-clean, axiom-free)

## Target

Ataka, M., & Matsuoka, N. (2026). *Normality of monomial ideals in three variables* (arXiv:2602.01782v1),
§4.3, **Example 4.7** — two illustrative ideals used to discuss reduction numbers of normal ideals:

- **4.7(1)** `I = (x³, y², z², xy, xz, yz)` — stated integrally closed and normal (μ = 6).
- **4.7(2)** `I = (x³, y³, z³, x²y, xy², x²z, yz)` — stated "a normal ideal by Theorem 3.1."

## Findings

We built a **general monomial-ideal normality instrument** (`scripts/monomial_ideal_normality.py`) that
decides everything by the *integral-dependence* definition — stdlib-only, no floating point, no convex-hull
library:

- `x^u ∈ I^p` ⟺ some multiset of `p` generators sums ≤ `u`;
- `x^u ∈ closure(I^p)` ⟺ `∃ k ≥ 1 : x^{ku} ∈ I^{pk}` (integral dependence, exact);
- `I` normal ⟺ `I` and `I²` integrally closed (Reid–Roberts–Vitulli, `d = 3`).

It is cross-validated three ways: it agrees with the corner-ideal instrument (`prob41`) on `(4,5,7)`,
`(3,3,3)`, `(7,3,2)`; it reproduces the Example 4.5 sharpness result (`closure(x⁷,y³,z²)` not normal, witness
`x⁶y²z`); and against exact LP membership on the 4.7 ideals.

**4.7(1) — CONFIRMED normal.** `I` and `I²` are integrally closed, so `I` is normal. ✅

**4.7(2) — ERRATUM: the ideal is NOT integrally closed.** The monomial **`xz²` is not in `I`**, yet
**`(xz²)² = x²z⁴ = (x²z)·(z³) ∈ I²`**. A monomial whose square lies in `I²` is integral over `I` (it satisfies
`X² − c = 0` with `c ∈ I²`), so **`xz² ∈ closure(I) ∖ I`** — `I` is not integrally closed. Consequently:

- `I` is not normal in the standard sense (a normal ideal is in particular integrally closed, `I = Ī`);
- Theorem 3.1, cited in the example, requires `I = Ī` **and** `μ(I) ≤ 7`; the actual integral closure `Ī`
  has **8** minimal generators (`μ(Ī) = 8 > 7`), so the theorem does not apply as printed either way.

This is kernel-decided, axiom-free:

```
theorem xz2_not_in_I          : inI 1 0 2 = false := by decide
theorem xz2_squared_in_I2     : inI2 2 0 4 = true  := by decide
theorem I2_not_integrally_closed : inI 1 0 2 = false ∧ inI2 2 0 4 = true := by decide
```

`#print axioms` → "does not depend on any axioms" on all three.

## Scope and honesty

This is a slip in an **illustrative example** (§4.3, reduction numbers) and is **independent of the paper's
Main Theorem** — the `μ(I) ≤ 7 ⇒ normal` bound in `k[x,y,z]` — whose sharpness (witness `closure(x⁷,y³,z²)`,
8 generators, not normal) we independently verified and confirmed **correct** in Example 4.5 (see
`ataka-matsuoka-732-verification-2026-07-04.md`). It does not undermine the paper's contribution; it is a
transcription/normalization slip in a downstream example. The likely intended object is the integral closure
`Ī` (8 generators), for which the reduction-number discussion would need a separate justification since
`μ(Ī) = 8 > 7` puts it outside Theorem 3.1.

We did **not** kernel-certify 4.7(1)'s *normality* in Lean: doing so for a general (non-corner) monomial ideal
needs the true multi-facet Newton polyhedron of `I²` — the naive single-facet shortcut is unsound (the kernel
rejected it during development: `closure(4.7(1))` coincides with `{x+2y+2z ≥ 3}` on the lattice but the real
polyhedron is strictly smaller, so doubling the offset wrongly admits `y³, y²z, yz², z³`). A sound in-kernel
general-normality certificate is future work; 4.7(1)-normal here rests on the instrument (exact
integral-dependence), which is the same tier at which the corner instrument reports its *normal* cases.

## Artifacts

- Instrument: `scripts/monomial_ideal_normality.py` (general, stdlib, exact)
- Producer + erratum guard: `scripts/verify_ataka_matsuoka_47.py`
- Certificate (downloadable): `docs/crt/ataka_matsuoka_47_certificate.lean`
- Result record: `docs/results/ataka_matsuoka_47_verification.json` · Tests: `tests/test_ataka_matsuoka_47.py`

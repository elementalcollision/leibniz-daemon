# Independent kernel verification — Ataka–Matsuoka (2026), Example 4.5

**Date:** 2026-07-04 · **Track:** T9 (external open-problem corpus) / T5 (external audit instrument) ·
**Tier:** audit · **EV:** verification-amplification · **Gate:** GREEN (kernel-clean, axiom-free)

## Target

Ataka, M., & Matsuoka, N. (2026). *Normality of monomial ideals in three variables* (arXiv:2602.01782v1,
Feb 2026, math.AC). Their **Main Theorem**: an integrally closed monomial ideal `I` in `k[x,y,z]` with
`ht I = 3` and `μ(I) ≤ 7` is normal (`Iⁿ` integrally closed for all `n`); the bound **7 is sharp**. The
sharpness witness (**Remark 1.3 / Example 4.5**) is

```
I = closure(x⁷, y³, z²) = (x⁷, y³, z², x⁵y, x³y², x⁴z, y²z, x²yz),   μ(I) = 8,
```

which is **not normal**: `x⁶y²z ∉ I²`, yet `(x⁶y²z)² = (x⁵y)·x⁷y³z² ∈ I⁴ = (I²)²`, so `x⁶y²z ∈ closure(I²)`,
whence `I² ⊊ closure(I²)`. By Reid–Roberts–Vitulli (in `d = 3`, normality ⟺ `I` and `I²` integrally closed;
their **Theorem 2.3**), `I` is not normal.

## What Leibniz verified

LLMs propose nothing here — the paper's claim *is* the object; our Lean 4.31 kernel **decides**. On the
flagship Problem-41 instrument (`scripts/prob41_normality_lean.py`), extended with a minimal-generator
computation, we reproduce **both** load-bearing facts directly from the Newton polyhedron (weights
`(6,14,21)`, `L = lcm(7,3,2) = 42`) and cross-check them **verbatim** against Example 4.5:

| Fact | Paper (Ex. 4.5) | Leibniz (independent) | Kernel theorem |
|---|---|---|---|
| minimal generators | 8, listed | 8, **set-equal** | `eight_minimal_generators`, `generators_are_paper_list` |
| non-normality witness | `x⁶y²z ∈ closure(I²) ∖ I²` | `x⁶y²z` (wt 85 ≥ 2L = 84; ∉ I²) | `not_normal_witness_x6y2z` |

All three theorems are kernel-decided by `decide` and **depend on no axioms at all** (`#print axioms` →
"does not depend on any axioms" ×3). A built-in erratum guard (`build_certificate`) refuses to emit the
certificate unless the generator count, the generator set, the non-normality verdict, the witness monomial,
and the weight vector *all* match the transcribed paper data — the same discipline that caught a real erratum
in the SS-RS-GD COLT refutation.

- Certificate (downloadable): `docs/crt/ataka_matsuoka_732_certificate.lean`
- Producer: `scripts/verify_ataka_matsuoka.py` · Instrument: `scripts/prob41_normality_lean.py::min_generators`
- Result record: `docs/results/ataka_matsuoka_732_verification.json` · Tests: `tests/test_ataka_matsuoka.py`
- Registered in the counterexample-certificate domain as `monomial_normal {a:7,b:3,c:2}` (Tier 1).

## Honest scope

This is **verification-amplification**, not a solve: we do not prove the Main Theorem (the `μ(I) ≤ 7 ⇒
normal` direction is an abstract case analysis over all such ideals, outside the finite-`decide` lane). We
independently kernel-attest the **sharpness witness** — the finite, decidable half — reproducing the paper's
Example 4.5 exactly. No trust surface is touched; every artifact is read-only and kernel-decided.

## Companion finding — the resolved n-absorbing CRT problems are not counterexample-shaped

A paper-grounded research + adversarial-faithfulness pass over the three *resolved* Tier-A CRT candidates
(before selecting this target) found none of them is a finite-`decide` counterexample:

| CFFG problem | Resolution | Formalizability |
|---|---|---|
| **30a** — every n-absorbing ideal strongly n-absorbing? | **Positive** (Secord 2023, arXiv:2305.03878) — always true | no counterexample exists |
| **30b** — `rad(I)ⁿ ⊆ I` for n-absorbing `I`? | **Positive** (Choi–Walker 2016, arXiv:1610.10077) — always holds | no counterexample exists |
| **9** — integrally closed reduced non-McCoy, locally McCoy | Counterexample **exists** (Haotian Ma 2026, arXiv:2604.07465) | **intrinsically infinite** (Akiba/Nagata construction; not a bounded `decide`) |

Each paper was independently re-fetched and its claim confirmed faithful; the verdict is `FAITHFUL_BUT_NOT_
DECIDABLE` in all three. The honest consequence: the counterexample-certificate domain's growth on new CRT
problems runs through **open, monomial** questions (Problem 41 / Ataka–Matsuoka), not the resolved
n-absorbing ones — which were settled in the *positive* direction or with infinite objects.

# Problem 16 — a self-ordered sequence census (certified refutations + a correction)

**Date:** 2026-07-04 · **Track:** T9 (external open-problem corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (5/5 refutation certificates kernel-clean, standard axioms)

## What this is

Cahen–Fontana–Frisch–Glaz **Problem 16** (Chabert) asks for the "natural" **self-ordered** integer sequences.
A sequence `a = (aₙ)` is self-ordered (Adam–Cahen–Fares *simultaneously ordered*) when its factorial
`D_n = ∏_{k<n}(aₙ − aₖ)` divides `P(m,n) = ∏_{k<n}(aₘ − aₖ)` for **all** `m, n` — i.e. the natural order is
itself a simultaneous ordering.

"Self-ordered" is an *infinite* condition, so it cannot be *certified* by a bounded computation. Its
**negation**, however, is finitely witnessed — one pair `(m,n)` with `D_n ∤ P(m,n)` refutes it — and that is a
kernel-`decide`-able fact. This census screens a curated set of natural sequences and emits a bundled Lean
certificate **refuting** the non-self-ordered ones, each cert hardcoding only the short value prefix its
witness needs (so factorial, Fibonacci, primes are all handled uniformly).

## Result

| Sequence | Verdict | Certificate |
|---|---|---|
| `n` (identity, arithmetic) | self-ordered to N=30 | — (evidence, not a proof) |
| `3 + 5n` (arithmetic) | self-ordered to N=30 | — |
| **`n²`** | **self-ordered to N=30** | — (see correction below) |
| `n(n+1)/2` (triangular) | self-ordered to N=30 | — |
| `2ⁿ` (geometric) | self-ordered to N=30 | — |
| `n³` | **NOT self-ordered** | witness (m,n) = (3,2), `D₂=56 ∤ P=702` ✅ |
| `n⁴` | **NOT self-ordered** | witness (4,3) ✅ |
| `(n+1)!` (factorial) | **NOT self-ordered** | witness (3,2), `D₂=20 ∤ P=506` ✅ |
| distinct Fibonacci `1,2,3,5,8,…` | **NOT self-ordered** | witness (4,3), `D₃=24 ∤ P=210` ✅ |
| `(n+1)`-th prime | **NOT self-ordered** | witness (3,2), `D₂=6 ∤ P=20` ✅ |

All 5 refutation theorems are kernel-decided; `#print axioms` returns only the standard set (`propext`), like
the sibling `self_ordered` family in the counterexample-certificate domain.

### The correction

The corpus doc (`docs/crt-open-problems-corpus.md`) loosely listed the additive-value angle for Problem 16 as
"refute {n²}, {nᵏ}". **That is wrong for `n²`:** `{n²}` is self-ordered up to `N = 30` — there is no refuting
witness. The refutable *pure powers* are `n^k` with **`k ≥ 3`** (`n³`, `n⁴` refute here). The corpus doc has
been corrected accordingly.

### Notable: natural sequences that are NOT self-ordered

Problem 16 asks for *natural* self-ordered sequences; three of the most natural non-polynomial sequences —
**factorial, Fibonacci, and the primes** — are certified **not** self-ordered, each by a small explicit
witness. That is honest evidence about where self-ordering does *not* come from.

## Honest scope

The census **certifies refutations** (complete, kernel-decided). The self-ordered verdicts are *bounded
evidence* (`N = 30`), not proofs — certifying that a sequence *is* self-ordered requires proving the infinite
divisibility condition (a theorem, e.g. for arithmetic/geometric sequences), which is future work. The
classification of all "natural" self-ordered sequences is the open mathematics and is not claimed. No trust
surface is touched; every verdict is read-only and, where certified, kernel-decided.

## Artifacts

- Producer: `scripts/prob16_census.py`
- Bundled certificate (downloadable): `docs/crt/prob16_census_certificate.lean` — 5 refutation theorems
- Result record: `docs/results/prob16_census.json` · Tests: `tests/test_prob16_census.py`

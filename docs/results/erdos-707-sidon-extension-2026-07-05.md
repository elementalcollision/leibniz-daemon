# Independent kernel verification — Erdős Problem 707 (the Sidon-Extension Conjecture), finite core

**Date:** 2026-07-05 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (12/12 theorems kernel-decided, no axioms)

## Target

**Erdős Problem 707** (a "favourite" $1000 conjecture, posed repeatedly from 1976): *every finite Sidon set
extends to a finite perfect difference set (PDS).* A Sidon set has all pairwise differences distinct; a PDS of
order `n` is `B ⊂ ℤ_v` with `|B| = n`, `v = n² − n + 1`, and every nonzero residue a difference exactly once.

- **Disproved** by Alexeev & Mixon, *"Forbidden Sidon subsets of perfect difference sets"*
  ([arXiv:2510.19804](https://arxiv.org/abs/2510.19804), Oct 2025) — the size-5 Sidon set `{1,2,4,8,13}` does
  not extend to any PDS (and Hall's 1947 `{1,3,9,10,13}` predates the conjecture).
- **Smallest size** studied by Niu, *"Size-4 Counterexamples to the Sidon-Extension Conjecture"*
  ([arXiv:2604.25214](https://arxiv.org/abs/2604.25214)) — `A = {0,1,3,11}`, `B = {0,1,4,11}` are Sidon and
  fail to extend for every modulus `v ≤ 133` (unconditional brute-force), evidence the smallest non-extending
  Sidon set has size 4.

## The kernel-decidable reduction

A PDS of order `n` has `n(n−1) = v−1`, so a size-`n` set `B ⊂ ℤ_v` is a PDS **iff its pairwise differences mod
`v` are all distinct** (Sidon mod `v`). Hence:

> `S` extends to a PDS of order `n` ⟺ some size-`n` superset of `S` is Sidon mod `v`;
> `S` is non-extending at order `n` ⟺ **no** size-`n` superset of `S` is Sidon mod `v` — a bounded, decidable fact.

## What Leibniz verified

LLMs propose nothing here — the papers' objects are the claims; our Lean 4.31 kernel **decides**. For each of
the four counterexample sets (`A`, `B`, `{1,2,4,8,13}`, `{1,3,9,10,13}`), all `decide`, **no axioms**:

- **Sidon** (over ℤ) — `{name}_sidon`.
- **Non-extension at order `|S|`** — the set, reduced mod `v = |S|²−|S|+1`, is not a PDS (`isPDS S v = false`).
- **Non-extension at order `|S|+1`** — no single element extends it to a PDS (`∀ x < v, isPDS (S++[x]) v = false`).

The instrument (`verify_erdos_707.py`, Python) additionally reproduces the non-extension for **all orders with
`v ≤ 43`** (up to order 7) — a faithful slice of the papers' unconditional exhaustion (their full run reaches
`v ≤ 133`). Every set is Sidon and none extends.

## Honest scope

"Non-extending to *any* finite PDS" is an **infinite** claim, proven non-finitely (Alexeev–Mixon's polarity
argument for the size-5 disproof; the size-4 case is still conjectural). We certify the **finite exhaustion**
at small orders — an independent kernel verification of the finitely-checkable core of a freshly-resolved
$1000 problem. No trust surface touched — read-only kernel elaborations, `tests/test_invariants.py`
byte-identical.

## Artifacts

- Certificate (downloadable): `docs/crt/erdos_707_certificate.lean` — 12 theorems
- Producer / verifier: `scripts/verify_erdos_707.py` · Tests: `tests/test_erdos_707.py`
- Result record: `docs/results/erdos_707_verification.json`

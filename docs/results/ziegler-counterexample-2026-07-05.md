# Kernel-attested confirmation of Kaibel–Pokutta's counterexample to Ziegler's cross-polytope conjecture

**Date:** 2026-07-05 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (exact-ℚ verification; Lean 4.31 kernel re-decides the core)

## What this is

An **independent, first-principles** confirmation of a fresh 2026 result in a domain new to the ledger
(**polytope theory / discrete geometry**). Ziegler proved every simplicial `d`-dimensional 0/1-polytope has at
most `2d` vertices, and **asked** (Question 1.1) whether equality forces central symmetry — equivalently, a
0/1-realization of the `d`-dimensional cross polytope. **Kaibel & Pokutta**
([arXiv:2606.31640](https://arxiv.org/abs/2606.31640), 2026) answer **no**: an explicit `14 = 2·7` vertices in
`{0,1}⁷` whose convex hull is a **simplicial 7-polytope that is not centrally symmetric** (`d=7` is the first
dimension where this can happen).

## What Leibniz verified — exactly over ℚ

Leibniz re-decides the counterexample from the 14 vertices (read directly from the paper's Theorem 3.1) using
**exact rational linear algebra** — the paper's own method ("the facet enumeration and rank computations were
carried out exactly over ℚ"):

1. **dim P = 7** — `rank[1|V] = 8`.
2. **Simplicial** — exact facet enumeration finds **exactly 136 supporting facets**, each touching exactly 7 of
   the 14 vertices, and each set of 7 is **affinely independent** (a nonzero 6×6 minor) — so every facet is a
   6-simplex.
3. **Completeness** — the 136 facets form a **closed pseudomanifold**: every one of the **476 ridges** (a
   6-subset of a facet) lies in **exactly 2 facets**. Since ∂P is a connected pseudomanifold, a closed
   collection of genuine facets must be *all* of them — so the enumeration is complete and `P` is simplicial.
   (The ridge count 476 matches the paper's f-vector entry `f₅`.)
4. **Not centrally symmetric** — `V` is *balanced* (each coordinate sums to `d=7`), so the barycenter is
   `(½,…,½)`, the only possible centre; yet four vertices (`v₁,v₅,v₆,v₁₀`) lack their cube antipode `1−v`, so
   `V` is not closed under `v↦1−v`. Hence `P` is not centrally symmetric.

Every one of (1)–(4) is settled by exact rational arithmetic — no floating point.

## The Lean kernel re-decides the core

The **Lean 4.31 kernel** then independently re-decides (plain `decide`, report-only) the parts that fit its
reduction budget, as three theorems in [`docs/crt/ziegler_counterexample.lean`](../crt/ziegler_counterexample.lean):

- **`ziegler_dim_notsym`** — `rank[1|V]=8` (via a nonzero 8×8 minor), `V` balanced, and the four cube-antipodes
  absent ⇒ not centrally symmetric.
- **`ziegler_supporting`** — each of the 136 facets is cut out by a supporting hyperplane vanishing on its 7
  vertices and strictly negative on the other 7 (so each facet has exactly 7 vertices).
- **`ziegler_closed`** — the closed-pseudomanifold certificate: for every facet and each of its 7 ridges, an
  explicit partner facet shares that ridge (completeness).

Affine-independence of the 136 facets (that each is a genuine 6-simplex — 136 nonzero determinants) is carried
by the **exact-rational leg**; it exceeds the kernel's `decide` reduction budget, so it is certified by exact
arithmetic rather than in-kernel. The kernel legs use plain `decide` — no `native_decide`, no `sorry`.

## Honest scope

The exact-rational leg is the **complete** decider (it is the paper's own verification method, cross-checked
there against `polymake`); the Lean kernel re-decides the dimension, the supporting-hyperplane structure, the
pseudomanifold completeness, and the non-central-symmetry. This is the *single* Theorem 3.1 example — the
paper's full `d=7` classification (five examples, two combinatorial types) is not reproduced here. The backend
is **report-only**: the kernel *observes*; nothing sets `kernel_verified`, mints a proof edge, or imports
`trust.py`. `tests/test_invariants.py` is byte-identical.

## Artifacts

- Certificate (downloadable): [`docs/crt/ziegler_counterexample.lean`](../crt/ziegler_counterexample.lean) —
  Lean 4.31, three `decide` theorems.
- Producer / verifier: [`scripts/verify_ziegler_counterexample.py`](../../scripts/verify_ziegler_counterexample.py)
  · Tests: [`tests/test_ziegler_counterexample.py`](../../tests/test_ziegler_counterexample.py)
- Result record: `docs/results/ziegler_counterexample_verification.json`

## References

- Kaibel, V., & Pokutta, S. (2026). *A counterexample to Ziegler's cross-polytope conjecture for simplicial
  0/1-polytopes* (arXiv:2606.31640). arXiv.
- Ziegler, G. M. (2000). Lectures on 0/1-polytopes. In *Polytopes — Combinatorics and Computation* (DMV Seminar
  29, pp. 1–41). Birkhäuser.

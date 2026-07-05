# Kernel-attested confirmation of Aliabadi's counterexample to the Brualdi–Friedland–Pothen conjecture

**Date:** 2026-07-05 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (symbolic over ℚ(a,…,l) + integer instance + Lean 4.31 `decide`)

## What this is

An **independent, first-principles** confirmation — and a **Lean-kernel-decided** witness — of a fresh 2026
counterexample in a domain new to the ledger (**combinatorial matrix theory / elementary vectors**). Brualdi,
Friedland & Pothen conjectured a clean combinatorial test for when the elementary vectors of a sparse-generic
matrix form a basis of its row space; **Aliabadi** ([arXiv:2605.30401](https://arxiv.org/abs/2605.30401), 2026)
refutes the **sufficiency** direction with an explicit 4×8 matrix.

## The conjecture and the refutation

**Conjecture 2.1 (BFP).** Let `A` be an `m×n` matrix of rank `m` whose displayed nonzero entries are
algebraically independent over ℚ. Let `x₁,…,xₘ` be elementary vectors in the row space, with zero-sets
`Jₛ = Z(xₛ)`. Then `x₁,…,xₘ` form a basis of the row space **iff** for every nonempty `P ⊆ [m]`,
`rank A[:, ⋂_{s∈P} Jₛ] ≤ m − |P|`.

**Counterexample.** The 4×8 sparse-generic matrix
```
      c1 c2 c3 c4 c5 c6 c7 c8
r1  [  a  c  d  0  0  0  0  k ]
r2  [  0  0  0  e  0  h  0  l ]
r3  [  b  0  0  0  0  i  j  0 ]
r4  [  0  0  0  f  g  0  0  0 ]
```
with elementary vectors having zero-sets `J₁={5,7,8}, J₂={1,5,6}, J₃={1,4,6}, J₄={4,7,8}`. Every
rank-intersection inequality holds, yet the four elementary vectors are **linearly dependent** — so they are
**not** a basis. Sufficiency fails.

The mechanism is transparent once seen: the inequalities only ever inspect `⋂_{s∈P} Jₛ`, and here those
intersections are tiny (all `|⋂| ≤ 4−|P|`), so the condition is satisfied *for free* — while the genuine
dependence among the `xₛ` lives outside what those intersections can detect.

## What Leibniz verified — reconstructing the vectors itself

Leibniz does **not** trust the paper's elementary vectors or its dependence relation; it rebuilds them.

1. **Symbolic, exact, general (over ℚ(a,…,l) — the algebraically-independent case BFP requires).** For each
   `s`, it constructs `xₛ` as the unique-up-to-scale row-space vector vanishing on `Jₛ`, and checks: `Z(xₛ)=Jₛ`;
   each `xₛ` is a **genuine elementary vector** (its support is a *cocircuit* — the complement `Jₛ` is a
   hyperplane: `rank A[:,Jₛ]=3` and adjoining any outside column raises the rank to 4 — confirmed two ways,
   including direct minimal-support); all **15** rank-intersection inequalities hold; and `rank[x₁;…;x₄]=3<4`
   (dependent ⇒ not a basis). *(Row-space elementary vectors have cocircuit, not circuit, supports — the load-
   bearing subtlety this verification gets right.)*

2. **Integer instance + Lean 4.31 kernel.** A **matroid-faithful** integer specialization — its nonzero
   4×4-minor *set* equals the generic one exactly (39 bases; checked as full set-equality against the
   perfect-matching pattern, not merely a count) — carries an explicit witness bundle the kernel **decides**
   (plain `decide`, no `native_decide`; `#print axioms` reports only `propext`): membership `xₛ = combosₛ·A`;
   `Z(xₛ)=Jₛ`; elementary-ness via nonzero 3×3 and 4×4 minors computed *from A in-kernel* by a recursive
   determinant; the BFP inequalities via the cardinality bound `|⋂Jₛ| ≤ 4−|P|`, which yields the conjecture's
   `rank A[:,⋂Jₛ] ≤ 4−|P|` because `rank ≤ #columns` (and for the tight singleton cases `⋂ = Jₛ` the exact
   rank-3 is certified in-kernel by the elementary leg; the exact ranks for every `P` are also certified in the
   symbolic/integer legs); and a nonzero integer vector `d = [598, 403, −31, 46]` with `d·[x₁;…;x₄] = 0`. A
   deliberately corrupted `d` is **rejected** by the same `decide` (negative control), confirming the check is
   discriminating.

## Honest scope

The refutation is of **sufficiency** (the "if" direction); the necessity direction is not at issue. The kernel
leg certifies a matroid-faithful integer representative — the fully general algebraically-independent statement
is carried by the exact symbolic leg over ℚ(a,…,l). `propext` is one of Lean's three canonical trusted axioms
(not `sorryAx`, not compiler trust). The verification is **report-only**: the kernel *observes*; nothing sets
`kernel_verified`, mints a proof edge, or imports `trust.py`. `tests/test_invariants.py` is byte-identical.

## Artifacts

- Certificate (downloadable): [`docs/crt/bfp_counterexample.lean`](../crt/bfp_counterexample.lean) — Lean 4.31,
  plain `decide`, `#print axioms` = `[propext]`.
- Producer / verifier: [`scripts/verify_bfp_counterexample.py`](../../scripts/verify_bfp_counterexample.py) ·
  Tests: [`tests/test_bfp_counterexample.py`](../../tests/test_bfp_counterexample.py)
- Result record: `docs/results/bfp_counterexample_verification.json`

## References

- Aliabadi, M. (2026). *A counterexample to a basis conjecture of Brualdi, Friedland, and Pothen*
  (arXiv:2605.30401). arXiv.
- Brualdi, R. A., Friedland, S., & Pothen, A. (1995). The sparse basis problem and multilinear algebra.
  *SIAM Journal on Matrix Analysis and Applications, 16*(1), 1–20.

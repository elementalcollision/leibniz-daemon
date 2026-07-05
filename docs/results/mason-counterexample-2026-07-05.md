# Kernel-attested confirmation of the counterexample to Mason's matroid log-concavity conjecture

**Date:** 2026-07-05 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (exact ℤ counting, validated vs brute force; Lean 4.31 `decide`)

## What this is

An **independent, first-principles** confirmation of a fresh 2026 result in a domain new to the ledger
(**matroid theory / log-concavity**). Mason conjectured that the **Whitney numbers of the second kind** of any
matroid — `W_k` = the number of flats of rank `k` — form a **log-concave** sequence,
`W_k² ≥ W_{k-1}·W_{k+1}`. The paper *Counterexamples to two conjectures about matroids*
([arXiv:2607.02208](https://arxiv.org/abs/2607.02208), 2026) disproves it with an explicit graphic matroid.

## The counterexample

The generalized **theta graph** `Θ(1,26,26,26)`: two hubs joined by four internally-disjoint paths of
edge-lengths `1, 26, 26, 26` (**77 vertices, 79 edges, rank 76**). Its graphic matroid's Whitney numbers
violate log-concavity at `k = 74`.

## What Leibniz verified — recomputing the Whitney numbers itself

Leibniz uses **none of the paper's three integers**. It exploits the exact bijection **flats of a graphic
matroid ↔ partitions of the vertices into connected blocks** (a flat of rank `k` ↔ a partition into `77−k`
connected blocks), so `W_k` is a *connected-partition count*:

1. **Exact counting.** A per-path transfer generating function counts connected partitions of the theta graph:
   each hub-to-hub path contributes floating blocks and hub-attached segments, subject to the flat condition
   that every intra-block edge is kept (so two hub-blocks may never be adjacent). The three identical length-26
   paths are combined by exact polynomial arithmetic.
2. **Self-validation.** That counter is checked against **brute-force connected-partition enumeration** on
   small theta graphs — exact ground truth — matching on every case, including the `Θ(1,L,L,L)` shape of the
   counterexample.
3. **Result.** For `Θ(1,26,26,26)`:
   `W₇₅ = 18551`, `W₇₄ = 983775`, `W₇₃ = 52954525` — matching the paper — and log-concavity **fails** at `k=74`:
   `W₇₄² = 967 813 250 625 < 982 359 393 275 = W₇₃·W₇₅` (a deficit of **14 546 142 650**).

## The Lean kernel re-decides it

The **Lean 4.31 kernel** independently re-decides the result (plain `decide`, report-only) in
[`docs/crt/mason_counterexample.lean`](../crt/mason_counterexample.lean): from the two per-path generating
functions it **assembles the three Whitney numbers by exact polynomial arithmetic** (cubing the three long
paths and combining), and proves two theorems — `mason_whitney_values` (`W₇₅,W₇₄,W₇₃ = 18551,983775,52954525`)
and `mason_log_concavity_fails` (`W₇₄² < W₇₃·W₇₅`). Both are `#print axioms`-clean (`[propext]` only — no
`native_decide`, no `sorry`). So the kernel doesn't merely stamp three integers: it *recomputes* them from the
per-path combinatorics and decides the strict inequality.

## Honest scope

The bijection flats ↔ connected partitions and the per-path transfer generating function are exact
combinatorics, **validated against brute force**; the kernel does the multi-path assembly and the arithmetic.
This certifies the single Example 2.2 counterexample (the log-concavity failure at one `k`), not the paper's
second result (White's toric-ideal conjecture). The backend is **report-only**: the kernel *observes*; nothing
sets `kernel_verified`, mints a proof edge, or imports `trust.py`. `tests/test_invariants.py` is byte-identical.

## Artifacts

- Certificate (downloadable): [`docs/crt/mason_counterexample.lean`](../crt/mason_counterexample.lean) —
  Lean 4.31, two `decide` theorems.
- Producer / verifier: [`scripts/verify_mason_counterexample.py`](../../scripts/verify_mason_counterexample.py)
  · Tests: [`tests/test_mason_counterexample.py`](../../tests/test_mason_counterexample.py)
- Result record: `docs/results/mason_counterexample_verification.json`

## References

- Larson, M. (2026). *Counterexamples to two conjectures about matroids* (arXiv:2607.02208). arXiv.
- Mason, J. H. (1972). Matroids: unimodal conjectures and Motzkin's theorem. In *Combinatorics* (pp. 207–220).
  Institute of Mathematics and Its Applications.

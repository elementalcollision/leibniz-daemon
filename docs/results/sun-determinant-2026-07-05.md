# Kernel-attested confirmation of Sun's determinant congruence (Zhang–Yang 2026)

**Date:** 2026-07-05 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (exact integer linear algebra; Lean 4.31 `decide`)

## What this is

An independent, exact-arithmetic confirmation of a fresh 2026 result in a domain new to the ledger
(**determinantal number theory / binary quadratic forms**). For `c,d ∈ ℤ` and `n ≥ 2`, let

`Dₙ(c,d) = det[ (i² + c·i·j + d·j²)^{n−2} ]₀≤i,j≤n−1`  (an `n×n` integer determinant).

**Zhang & Yang** ([arXiv:2605.19486](https://arxiv.org/abs/2605.19486), accepted *Bull. Aust. Math. Soc.*)
prove, in strengthened form, a conjecture of **Zhi-Wei Sun**:

- for **composite `n`**: `n² | Dₙ(c,d)` for **all** `c,d ∈ ℤ`;
- for **prime `n = p`**: `p² | Dₚ(c,d)` whenever the **Legendre symbol** `(d/p) = −1`.

## What Leibniz verified — exact integer determinants

The matrix is reconstructed directly from the formula (no external data). Leibniz forms the exact integer
determinant (fraction-free **Bareiss**) and checks the divisibility:

1. **Composite case.** `n² | Dₙ(c,d)` holds for every composite `n ∈ {4,6,8,9,10,12}` and all `c ∈ {−2..2}`,
   `d ∈ {1..6}`.
2. **Prime sufficiency.** For each prime `p ∈ {5,7,11,13}`, `p² | Dₚ(c,d)` holds at **every** quadratic
   non-residue `d` (all `c`).
3. **Sharpness.** For each tested prime there is a quadratic **residue** `d` with `p² ∤ Dₚ` (e.g. `p=5,d=1`
   gives `vₚ=1`) — so the Legendre condition is **not vacuous**; the divisibility genuinely can fail off the
   non-residues.

## The Lean kernel re-decides small instances

The **Lean 4.31 kernel** independently re-decides several small instances (plain `decide`, report-only) in
[`docs/crt/sun_determinant.lean`](../crt/sun_determinant.lean): from the explicit integer matrix it computes
the determinant by cofactor expansion and checks divisibility by `n²` — `sun_comp_n4_c1_d2` (`16 | D₄(1,2)`),
`sun_comp_n6_c1_d2` (`36 | D₆(1,2)`), `sun_prime_p5_c1_d2` (`(2/5)=−1`, `25 | D₅(1,2)`), and `sun_prime_p7_c1_d3`
(`(3/7)=−1`, `49 | D₇(1,3)`). All are `#print axioms`-clean (`[propext]` only — no `native_decide`, no `sorry`).

## Honest scope

This is **instance verification** of a proved theorem: Leibniz re-decides the congruence on a census of `(n,c,d)`
by exact arithmetic (and the kernel on small cases), rather than reproving the general theorem. That is
legitimate amplification — confirming the theorem's predictions, including the sharp prime behaviour (`vₚ=2` at
non-residues; failure at some residues). The backend is **report-only**: nothing sets `kernel_verified` or
touches `trust.py`; `tests/test_invariants.py` is byte-identical.

## Artifacts

- Certificate (downloadable): [`docs/crt/sun_determinant.lean`](../crt/sun_determinant.lean) — Lean 4.31, four
  `decide` theorems.
- Producer / verifier: [`scripts/verify_sun_determinant.py`](../../scripts/verify_sun_determinant.py) ·
  Tests: [`tests/test_sun_determinant.py`](../../tests/test_sun_determinant.py)
- Result record: `docs/results/sun_determinant_verification.json`

## References

- Zhang, Y., & Yang, Y. (2026). *A determinant congruence conjectured by Sun* (arXiv:2605.19486). arXiv /
  Bulletin of the Australian Mathematical Society.

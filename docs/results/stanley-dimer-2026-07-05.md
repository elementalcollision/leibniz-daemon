# Kernel-attested disproof of Stanley's 1985 dimer conjecture at k=13 (Guo–Tao 2026)

**Date:** 2026-07-05 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (exact sweep k=2..13; Lean 4.31 kernel `decide`, axiom-free)

## What this is

An **independent, first-principles** confirmation — and a **Lean-kernel-decided** disproof — of a 41-year-old
conjecture. Richard Stanley (1985) studied the domino-tiling counts `A_{k,n}` of the `k×n` rectangle, showed
their generating function is rational with denominator degree `2^⌊(k+1)/2⌋`, and **conjectured** that the
minimal linear-recurrence order of `{A_{k,n}}` equals that bound for every `k` (equivalently: numerator and
denominator are coprime; the denominator has only simple roots). This is **Problem 33** in Lai's 2024 AMS
open-problems volume. **Guo & Tao** ([arXiv:2605.28195](https://arxiv.org/abs/2605.28195), 2026) disproved it,
identifying **k=13 as the smallest counterexample**.

Leibniz reproduces the disproof using **none of the paper's polynomials**.

## What Leibniz computed

1. **Exact tiling counts + exact Berlekamp–Massey.** A broken-profile transfer DP computes `A_{k,n}` as exact
   big integers (validated: `A_{2,n}` is Fibonacci, `A_{2,13}=F₁₄=377`; `A_{4,n}` is OEIS A005178). Exact-
   rational Berlekamp–Massey reads the **true** minimal recurrence order:

   | k | Stanley's `2^⌊(k+1)/2⌋` | actual minimal order | |
   |---|---|---|---|
   | 2..12 | 2, 4, 4, 8, 8, 16, 16, 32, 32, 64, 64 | **identical** | conjecture holds |
   | **13** | **128** | **112** | **FALSE ★** |

   The conjecture holds *exactly* for every `k ≤ 12` and first fails at `k=13`, where the order is **112 < 128**.
   The deficiency `128 − 112 = 16 = deg(f₁₆)` matches Guo–Tao's squared degree-16 factor `f₁₆²` of `Q₁₃` — a
   repeated root collapses 16 double roots to 16 simple ones in the minimal polynomial.

2. **The Lean 4.31 kernel decides it.** Working on the even subsequence `B_m = A_{13,2m}` (order halves to 56;
   Stanley's bound halves to 64), the kernel decides — by **plain `decide`, no `native_decide`, and
   `#print axioms` reports none** — that the monic integer recurrence of order 56 annihilates `B` on **64
   consecutive equations**. Since `B` satisfies a recurrence of order `≤ 64` (Stanley's *proven* upper bound),
   a residual that is order-`≤64` and vanishes at 64 consecutive indices is identically zero; hence the
   annihilator holds for all `m` and the **minimal order is ≤ 56 < 64**. The strict drop is the disproof, and
   exact Berlekamp–Massey pins the matching lower bound (the order is *exactly* 56).

A deliberately corrupted coefficient is **rejected** by the same kernel `decide` (negative control), confirming
the check is discriminating rather than vacuous.

## Why the kernel can carry this

The natural formalization — check the order-112 recurrence over a 128-wide window of ~10¹³⁰-digit integers —
is a flat conjunction of ~14 000 big-integer products and walls the `decide` big-literal limit measured in the
large-block-PSD probes (ADR 0047). Two moves bring it inside the kernel: (i) the **even subsequence** halves
order and window (56 / 64), and (ii) a **compact `List.zipWith`/`foldl` encoding** (structured reduction, not a
flattened product-sum) reduces in the kernel's whnf. The 64-equation certificate decides in **~1.3 s**.

## Honest scope

k=13 is the *smallest* counterexample; the Guo–Tao families `k = 14h−1` and `k = 30h−1` (next: k=27, k=29) are
not recomputed here — their `2^13`/`2^14`-state DPs and wider windows are out of cheap-CPU range, and the
paper's infinite family is a closed-form argument this finite audit does not replay. The Lean backend run is
**report-only**: the kernel *observes*; nothing sets `kernel_verified`, mints a proof edge, or imports
`trust.py`. `tests/test_invariants.py` is byte-identical.

## Artifacts

- Certificate (downloadable): [`docs/crt/stanley_dimer_13.lean`](../crt/stanley_dimer_13.lean) — Lean 4.31,
  plain `decide`, `#print axioms` clean.
- Producer / verifier: [`scripts/verify_stanley_dimer.py`](../../scripts/verify_stanley_dimer.py) ·
  Tests: [`tests/test_stanley_dimer.py`](../../tests/test_stanley_dimer.py)
- Result record: `docs/results/stanley_dimer_verification.json`

## References

- Guo, Q.-H., & Tao, T. (2026). *Repeated roots of Stanley's dimer-covering denominators, disproving a 1985
  conjecture* (arXiv:2605.28195). arXiv.
- Stanley, R. P. (1985). On dimer coverings of rectangles of fixed width. *Discrete Applied Mathematics, 12*(1),
  81–87.
- Lai, C.-Y. (Ed.). (2024). *Open Problems in Algebraic Combinatorics* (Problem 33). AMS PSPM 110.

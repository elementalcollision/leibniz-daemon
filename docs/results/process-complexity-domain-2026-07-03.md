# Process-complexity certificate domain — GREEN (2026-07-03)

**Result: GREEN.** The beyond-Markov machinery is now a **first-class certificate domain** — a reusable
`certify(process)` interface, a sibling of the code-bound (Delsarte/Terwilliger) and covering-design domains.
`scripts/process_complexity_domain.py`, `tests/test_process_complexity_domain.py`,
`docs/results/process_complexity_domain.json`. No trust surface touched.

## The interface

`certify(process)` takes a process as an HMM/OOM (`{name, pi, T, [order]}`) and produces the exact-rational
certificate bundle, each part naming the **kernel-verified Lean lemma** that attests it:

- **Validity** — a valid rational HMM (`π≥0, Σπ=1, T_a≥0, Σ_a T_a` row-stochastic): a genuine stochastic
  process, not a signed formal series (the external panel's #1 mandate).
- **Hankel rank** — the exact rank of the word-Hankel block (the prediction-state dimension) + a nonsingular
  r-minor (kernel-checkable `rank ≥ r`; lemma `hankel_block_rank_le`).
- **Markov order** — conditional-separation certs (`order > K`), and for synchronizing processes the
  infinite-order recurrence (lemma `even_infinite_order` via `two_step_recurrence_nonzero`).
- **Positive realization** — where a fooling set exists, the minimal-positive-HMM-states lower bound (lemmas
  `fooling_le_of_nonneg_factor` + `hankel_nonneg_factor` + `necklace_positive_realization_needs_4`).

## Measured — the initial corpus

| process | dim | Hankel rank | Markov order | positive realization | certified |
|---|---|---|---|---|---|
| BM-1 symmetric 2-mode HMM | 2 | 2 (minor −192≠0) | > 8 | — | ✓ |
| even process ε-machine | 2 | 2 (minor −2≠0) | > 8 (infinite, kernel-derived) | — | ✓ |
| necklace 4-cycle chain | 4 | 3 | — | **4 > 3 = rank** | ✓ |

## Honest disposition

Audit tier, **verification-AMPLIFICATION** — and the module says so in its own docstring, enforced by a test.
The mathematics is textbook and the genuine-discovery case (the deep finite-OOM-but-no-finite-HMM phenomenon)
is provably out of reach of the exact-rational machinery (per the 8-reviewer panel). The domain's value is a
reusable, kernel-attestable certificate family — a legible instrument, not new theorems. Behind the unbroken
trust boundary; `tests/test_invariants.py` byte-identical.

## Sequential build (all four complete)

This closes the operator's "build 1–4 sequentially" directive: **#1** H0 trust-integrity hardening (#268);
**#2** beyond-Markov Calculemus cycle (#269); **#3** the audit-runner instrument (#270); **#4** this domain.
Two cheap boundary/legibility wins, one product-value instrument, one reusable amplification domain — all
audit/read-only, no trust surface touched.

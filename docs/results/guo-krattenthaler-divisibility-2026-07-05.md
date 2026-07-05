# Independent kernel verification — Guo–Krattenthaler (2014) binomial divisibility (Phase 1)

**Date:** 2026-07-05 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (23/23 theorems kernel-decided, standard axioms)

## Target

Guo, V. J. W., & Krattenthaler, C. (2014). *Some divisibility properties of binomial and q-binomial
coefficients.* Journal of Number Theory, 135, 167–184 ([arXiv:1301.7651](https://arxiv.org/abs/1301.7651);
doi:10.1016/j.jnt.2013.08.012). Two headline results:

- **(A) New all-`n` binomial divisibilities:** `(6n−1) ∣ C(12n,3n)`, `(6n−1) ∣ C(12n,4n)`, and
  `(66n−1) ∣ C(330n,88n)` for all `n ≥ 1`. In the paper these are consequences of **divisibility + positivity
  of quotients of q-binomial coefficients by q-integers**, generalizing the positivity of the q-Catalan
  numbers.
- **(B) A conjecture of Z.-W. Sun, confirmed:** if `a` has a prime factor not dividing `b`, then there are
  **infinitely many** `n` with `(bn+1) ∤ C((a+b)n, an)`. (The Catalan case `a=b=1` always divides — the
  boundary of the phenomenon.)

## What Leibniz verified (Phase 1)

LLMs propose nothing here — the paper's claims are the objects; our Lean 4.31 kernel **decides**. This Phase 1
is a certified census, all axiom-`decide` over exact `Nat.choose` (the ~90-digit `C(330,88)` needs
`set_option maxRecDepth`; the kernel evaluates `Nat.choose` with sub-term sharing, so the work is `O(n·k)`):

| Result | Certified | Theorems |
|---|---|---|
| `(6n−1) ∣ C(12n,3n)` | `n = 1..8` | `div_12_3_n1 … n8` |
| `(6n−1) ∣ C(12n,4n)` | `n = 1..8` | `div_12_4_n1 … n8` |
| `(66n−1) ∣ C(330n,88n)` | `n = 1` (≈90-digit binomial) | `div_330_88_n1` |
| Sun non-divisibility `(bn+1) ∤ C((a+b)n,an)` | 6 pairs `(a,b)` with witnesses | `sun_nondiv_a{a}_b{b}` |

The Sun witnesses: `(2,1)→n=1`, `(3,1)→n=2`, `(3,2)→n=1`, `(4,3)→n=1`, `(5,2)→n=2`, `(2,3)→n=1` — each a genuine
`(bn+1) ∤ C((a+b)n,an)`. 23 theorems total; `#print axioms` → only `[propext]` (standard set) on each.

## Why this target

It uniquely reuses the **from-scratch Gaussian-binomial machinery** we built for CFFG Problem 16
(`gBinom` q-Pascal recurrence, `qf`, `qf_dvd_ffall`) — because the paper's mechanism *is* q-binomial-by-q-integer
positivity. Phase 1 (this cert) is the finite, ship-alone half; **Phase 2** is the all-`n` theorem: extend the
q-Pascal/induction pattern to the positivity of the quotient by `[bn−1]_q`, giving `(6n−1) ∣ C(12n,3n)` etc.
for *all* `n` (not just certified instances). If Phase 2 stalls on a q-Chu–Vandermonde step, Phase 1 stands.

## Honest scope

Phase 1 certifies **instances** (a range of `n`) plus explicit witnesses — an independent verification, not a
re-proof of the general-`n` theorems. Live erratum potential: any `n` where the divisibility failed would be a
caught error (none found). No trust surface touched — read-only kernel elaborations, `tests/test_invariants.py`
byte-identical.

## Artifacts

- Certificate (downloadable): `docs/crt/guo_krattenthaler_certificate.lean` — 23 theorems
- Producer / verifier: `scripts/guo_krattenthaler_divisibility.py` · Tests: `tests/test_guo_krattenthaler.py`
- Result record: `docs/results/guo_krattenthaler_divisibility.json`

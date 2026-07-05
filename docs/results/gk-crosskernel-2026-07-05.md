# Cross-kernel amplification — Guo–Krattenthaler divisibilities in a second kernel (Lean ↔ Coq)

**Date:** 2026-07-05 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (17/17 instances agree; Rocq-sound, rocqchk axioms `<none>`)

## What this is

The first use of the ADR 0048 **sound Coq backend** for genuine cross-kernel amplification: the
Guo–Krattenthaler binomial divisibilities that Leibniz's **Lean 4.31** kernel decided in
[#293](https://github.com/elementalcollision/leibniz-daemon/pull/293) are here **independently re-decided by
the Rocq 9.0 (Coq) kernel**. Two independent trusted cores agreeing on the same arithmetic is strictly
stronger evidence than either alone — an independent kernel catches translation and kernel-specific errors a
single-checker pipeline cannot.

## Target

Guo, V. J. W., & Krattenthaler, C. (2014). *Some divisibility properties of binomial and q-binomial
coefficients.* Journal of Number Theory, 135, 167–184 ([arXiv:1301.7651](https://arxiv.org/abs/1301.7651)).
The three all-`n` divisibilities, as the exact finite instances the Lean census certified:

| Divisibility | Instances |
|---|---|
| `(6n−1) ∣ C(12n, 3n)` | `n = 1..8` |
| `(6n−1) ∣ C(12n, 4n)` | `n = 1..8` |
| `(66n−1) ∣ C(330n, 88n)` | `n = 1` (≈90-digit binomial) |

## The Coq certificate

Coq's Peano `nat` cannot hold `C(330,88) ≈ 2.65×10⁸⁷`, so the certificate works over **binary `N`** with an
exact incremental binomial (`C(n,i) = C(n,i−1)·(n−i+1)/i`, each partial an integer). Each of the 17 instances
is an `Example … : (binom … ) mod (6n−1) = 0` closed by `vm_compute; reflexivity` — the Rocq kernel evaluates
the binomial and the modulus and checks equality. `docs/crt/gk_coq_crosscheck.v`.

## What Leibniz verified — soundly

The certificate is checked through the ADR 0048 **sound** Coq backend: `rocq compile` **and** Rocq's own
library checker **`rocqchk`**, whose whole-development CONTEXT SUMMARY reports **`* Axioms: <none>`** and
`<none>` for every unsafe-construct class (type-in-type / unsafe (co)fixpoints / assumed-positivity),
name-agnostically and authenticated against source output-injection by an unforgeable nonce. So the
divisibilities are confirmed **axiom-free** in Coq, matching Lean's `#print axioms`-clean `decide`. The
instrument additionally re-derives all 17 divisibilities in exact Python (`math.comb`), a third
cross-check. All three agree.

## Honest scope

This confirms the same **finite instances** in a second kernel — an independent cross-check, not a re-proof
of the general-`n` theorem (that is GK Phase 2, [#296](https://github.com/elementalcollision/leibniz-daemon/pull/296),
which proves the prime-modulus case in Lean via Kummer). The Coq backend is **report-only** and **dormant for
promulgation** (its producer is not admitted to `trust.KERNEL_PRODUCERS`); no trust surface is touched, and
`tests/test_invariants.py` stays byte-identical. Coq's axiom audit is kernel-driven and sound; a false result
in either kernel would be a caught disagreement (none found).

## Artifacts

- Certificate (downloadable): `docs/crt/gk_coq_crosscheck.v` — 17 Coq `Example`s (binary-`N` binomial)
- Producer / verifier: `scripts/verify_gk_crosskernel.py` · Tests: `tests/test_gk_crosskernel.py`
- Result record: `docs/results/gk_crosskernel_verification.json`

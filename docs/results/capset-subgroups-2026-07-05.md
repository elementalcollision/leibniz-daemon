# Kernel-attested confirmation: subgroups of finite fields as cap sets (Kable–Mills–Wright 2026)

**Date:** 2026-07-05 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (exact GF(pᵏ) arithmetic; Lean 4.31 `decide`)

## What this is

An independent, exact-arithmetic confirmation of a fresh 2026 result in a domain new to the ledger (**additive
combinatorics over finite fields / cap sets**). A **cap set** is a subset of an affine geometry containing no
full "line": in `AG(k,3)` — the geometry of the card game **SET** — a line is three distinct points `a,b,c` with
`a+b+c = 0`; in `AG(k,2)` — the game **EvenQuads** — the analogue is a "quad", four distinct points `a,b,c,d`
with `a+b+c+d = 0`. **Kable, Mills & Wright** ([arXiv:2604.26989](https://arxiv.org/abs/2604.26989), 2026) show
that certain **multiplicative** subgroups of a finite field, viewed inside the field's **additive** geometry,
are cap sets.

## What Leibniz verified — from the field axioms, model-independently

Leibniz uses **none** of the paper's tables. It builds `GF(pᵏ) = F_p[t]/(irreducible)`, confirms the
construction is a genuine field (its multiplicative group is cyclic of order `pᵏ−1`), forms the power-subgroup,
and checks the cap property by **exact finite-field arithmetic** over every triple (char 3) or quad (char 2):

| Result | Field | Subgroup | Cap condition | Size | ✓ |
|---|---|---|---|---|---|
| **SET** | GF(81) ≅ AG(4,3) | 20 nonzero **fourth** powers | no 3 distinct sum to 0 | **20** | ✓ |
| **EvenQuads** | GF(64) ≅ AG(6,2) | 9 nonzero **seventh** powers | no 4 distinct sum to 0 | **9** | ✓ |
| **General** | GF(2^{2n}), n=2..5 | `(2ⁿ−1)`-th powers | no 4 distinct sum to 0 | `2ⁿ+1` (5,9,17,33) | ✓ |

Both marquee subgroups are **maximal caps** of their respective decks (the maximal cap sizes for SET and
EvenQuads are 20 and 9), giving an external cross-check. The cap property is **independent of the field model**:
Leibniz re-verifies the GF(81) case with a **second** irreducible polynomial (`t⁴+t³+t²+1`) and obtains the same
20-cap — as it must, since the additive geometry is determined up to isomorphism.

## The Lean kernel re-decides the two marquee caps

The **Lean 4.31 kernel** independently re-decides (plain `decide`, report-only) in
[`docs/crt/capset_subgroups.lean`](../crt/capset_subgroups.lean): `capset_set81` (no three distinct of the 20
GF(81) fourth-power vectors sum to 0 mod 3) and `capset_eq64` (no four distinct of the 9 GF(64) seventh-power
vectors sum to 0 mod 2). Both are `#print axioms`-clean (`[propext]` only — no `native_decide`, no `sorry`). The
element vectors are emitted from the field construction, so the kernel checks the cap directly over `(F₃)⁴` /
`(F₂)⁶` arithmetic.

## Honest scope

This confirms two explicit maximal caps and the general `GF(2^{2n})` family (n=2..5); the paper's additional
`GF(243)`/`GF(729)` cases are not reproduced here (their exact subgroups are not restated in the abstract).
Verifying a *cap set exists* is a positive result — a mechanical audit of an exactly-reconstructible object,
decided by exact finite-field arithmetic (the same tier as earlier finite-field / exact-rational cycles). The
backend is **report-only**: nothing sets `kernel_verified` or touches `trust.py`; `tests/test_invariants.py` is
byte-identical.

## Artifacts

- Certificate (downloadable): [`docs/crt/capset_subgroups.lean`](../crt/capset_subgroups.lean) — Lean 4.31, two
  `decide` theorems.
- Producer / verifier: [`scripts/verify_capset_subgroups.py`](../../scripts/verify_capset_subgroups.py) ·
  Tests: [`tests/test_capset_subgroups.py`](../../tests/test_capset_subgroups.py)
- Result record: `docs/results/capset_subgroups_verification.json`

## References

- Kable, A., Mills, M., & Wright, D. J. (2026). *Subgroups of finite fields as cap sets* (arXiv:2604.26989).
  arXiv.

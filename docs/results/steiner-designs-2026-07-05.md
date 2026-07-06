# Kernel-attested existence of Steiner systems S(2,8,225) and S(2,9,289) (Hetman 2026)

**Date:** 2026-07-05 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (exact finite-group arithmetic; Lean 4.31 `decide`)

## What this is

An independent, exact-arithmetic confirmation of a fresh 2026 result in a domain new to the ledger (**design
theory / explicit incidence structures**). A **Steiner system S(2,k,v)** is a set of `v` points with a family
of `k`-blocks such that **every pair of points lies in exactly one block**. The *Handbook of Combinatorial
Designs* lists 129 undecided existence cases for block lengths 8 and 9. **Hetman**
([arXiv:2509.10673](https://arxiv.org/abs/2509.10673), accepted *J. Combinatorial Designs* 2026) **resolves
two** of them: `S(2,8,225)` and `S(2,9,289)` exist, via explicit **difference families**:

- **six** `S(2,8,225)` — two in `ℤ₃×ℤ₃×ℤ₅×ℤ₅` and four in `ℤ₅×ℤ₅×ℤ₉` (order 225), each 4 base blocks of size 8;
- **four** `S(2,9,289)` — in `ℤ₁₇×ℤ₁₇` (order 289), each 4 base blocks of size 9.

## What Leibniz verified — two independent, complete checks

From the base blocks (read directly from the paper), by exact finite-group arithmetic:

1. **Difference family (all ten systems).** The multiset of nonzero differences `b−b′` within the base blocks
   hits **every nonzero group element exactly once** — a `(v,k,1)`-difference family (`4·8·7 = 224 = 225−1`
   differences for the S(2,8,225) systems; `4·9·8 = 288 = 289−1` for S(2,9,289)). This is the standard
   sufficient condition for the development to be a Steiner 2-design, and it is **self-validating** against
   transcription: a single wrong point breaks the exact cover. All ten pass.
2. **Direct development (a representative of each parameter set).** Translating each base block by every group
   element yields `v·4` blocks (900 for order 225, 1156 for order 289); Leibniz checks **directly** that every
   one of the `C(225,2)=25200` / `C(289,2)=41616` pairs lies in **exactly one** block — the definition of a
   Steiner 2-design, with no theorem cited. All three representatives pass.

## The Lean kernel re-decides it

The **Lean 4.31 kernel** independently re-decides (plain `decide`, report-only) the difference-family property
for one marquee system of each parameter set, in
[`docs/crt/steiner_designs.lean`](../crt/steiner_designs.lean): `steiner_S8_225` (the 224 differences of the
`ℤ₃×ℤ₃×ℤ₅×ℤ₅` system are pairwise distinct, all nonzero, and number 224 — hence exactly the 224 nonzero
elements) and `steiner_S9_289` (the 288 differences of the `ℤ₁₇×ℤ₁₇` system, likewise). Both are `#print
axioms`-clean (`[propext]` only — no `native_decide`, no `sorry`).

## Honest scope

This confirms **existence** — a positive result resolving two open cases — by verifying explicit, exactly-
transcribed difference families with two independent exact checks (a mechanical audit of a printed object). The
paper's non-isomorphism "fingerprints" are not recomputed here. The backend is **report-only**: nothing sets
`kernel_verified` or touches `trust.py`; `tests/test_invariants.py` is byte-identical.

## Artifacts

- Certificate (downloadable): [`docs/crt/steiner_designs.lean`](../crt/steiner_designs.lean) — Lean 4.31, two
  `decide` theorems.
- Producer / verifier: [`scripts/verify_steiner_designs.py`](../../scripts/verify_steiner_designs.py) ·
  Tests: [`tests/test_steiner_designs.py`](../../tests/test_steiner_designs.py)
- Result record: `docs/results/steiner_designs_verification.json`

## References

- Hetman, I. (2026). *There exist Steiner systems S(2,8,225) and S(2,9,289)* (arXiv:2509.10673). arXiv /
  Journal of Combinatorial Designs.
- Colbourn, C. J., & Dinitz, J. H. (Eds.). (2007). *Handbook of Combinatorial Designs* (2nd ed.). CRC Press.

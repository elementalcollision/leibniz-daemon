# Kernel-attested "Simplest Kochen–Specker Set" — a 14-basis KS set refuting a 2025 PRL conjecture (Cabello 2025)

**Date:** 2026-07-06 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (exact Eisenstein-integer arithmetic; Lean 4.31 `decide`)

## What this is

An independent, exact-arithmetic confirmation of a 2025 **disproof of a published conjecture** in a domain new to
the ledger (**quantum contextuality / Kochen–Specker sets**). A **Kochen–Specker (KS) set** is a finite set of
vectors admitting **no** `{0,1}`-assignment `f` with `f(u)+f(v) ≤ 1` for orthogonal `u,v` and `Σ = 1` over each
orthonormal basis. Cabello ([Phys. Rev. Lett. **135**, 190203, 2025](https://arxiv.org/abs/2508.07335)) exhibits a
KS set of **33 qutrit vectors** using only **14 orthogonal bases** — a new **record** for the minimum number of
bases (previous record 16, Peres) — **refuting Conjecture 2** of Phys. Rev. Lett. **134**, 010201 (2025) on the
minimum number of inputs.

The vectors have **Eisenstein-integer** components (`ω = e^{2πi/3}`, `ω² = −1−ω`); the 14 bases are Eqs
(1a)–(1e) and (2a)–(2i).

## What Leibniz verified

By exact arithmetic over the Eisenstein integers `ℤ[ω]` (stored as pairs `(a,b) = a+bω`; `conj(a+bω) = (a−b)−bω`):

- **Geometry**: each of the 14 printed bases is mutually orthogonal (Hermitian inner product 0), and the vectors
  span **exactly 33 distinct projective rays** (as the paper states); the orthogonality graph has 78 edges.
- **Uncolorability**: **no KS `{0,1}`-assignment exists** — a finite Boolean UNSAT (exactly-one per basis +
  at-most-one per orthogonal edge), verified by a bounded backtracking search visiting ≈1.2k nodes (and
  independently confirmed `unsat` by Z3).

### A faithfulness finding

Reproducing the internal orthogonality of every basis **caught one text-extraction artifact**: the third vector
of the `x=3` basis (Eq. 1d) is `(ω², −ω, 1)` — a PDF text-layer extraction had dropped the minus sign, giving
`(ω², ω, 1)` and only 32 rays. The exact orthogonality of each basis is authoritative and fixes the reading
(recovering all 33 rays).

## The Lean kernel re-decides it

The **Lean 4.31 kernel** independently re-decides (plain `decide`, exact `ℤ[ω]` arithmetic computed in-kernel) in
[`docs/crt/cabello_ks.lean`](../crt/cabello_ks.lean):

- `cabello_bases_orth` — each of the 14 bases is mutually orthogonal;
- `cabello_uncolorable` — the bounded backtracking solver returns **no** KS assignment (the set is uncolorable) —
  the small (~1.2k-node) search means the UNSAT is decided **directly in the kernel**, with no external SAT/DRAT
  certificate;
- `cabello_control` — removing one basis makes the reduced (13-basis) set **colorable** — a discriminating
  negative control.

`#print axioms` shows at most `[propext]` for each — no `native_decide`, no `sorry`.

## Honest scope

This certifies the two finite facts that carry the result — that the 33 Eisenstein-integer vectors form 14
orthogonal bases, and that the resulting orthogonality/basis structure is KS-uncolorable — establishing a
14-basis KS set (below the previous record 16) and thus refuting the minimum-inputs conjecture. The paper's
quantum-strategy / pseudo-telepathy game-value analysis (a separate `W_C`/`W_Q` census) is **not** attempted; it
is not needed for the uncolorability disproof. A priority note by Pavičić (arXiv:2512.10483) about the same set's
earlier appearance is orthogonal to correctness — the uncolorability re-decided here is uncontested. The backend
is **report-only**: nothing sets `kernel_verified` or touches `trust.py`; `tests/test_invariants.py` is
byte-identical.

## Artifacts

- Certificate (downloadable): [`docs/crt/cabello_ks.lean`](../crt/cabello_ks.lean) — Lean 4.31, three `decide`
  theorems.
- Producer / verifier: [`scripts/verify_cabello_ks.py`](../../scripts/verify_cabello_ks.py) ·
  Tests: [`tests/test_cabello_ks.py`](../../tests/test_cabello_ks.py)
- Result record: `docs/results/cabello_ks_verification.json`

## References

- Cabello, A. (2025). *Simplest Kochen–Specker set*. Physical Review Letters, 135, 190203
  ([arXiv:2508.07335](https://arxiv.org/abs/2508.07335)).
- Kochen, S., & Specker, E. P. (1967). *The problem of hidden variables in quantum mechanics*. Journal of
  Mathematics and Mechanics, 17, 59–87.
- Yu, S., & Oh, C. H. (2012). *State-independent proof of Kochen–Specker theorem with 13 rays*. Physical Review
  Letters, 108, 030402.

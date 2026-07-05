# Independent kernel verification — Mafi–Naderi (2021), integral closure of a special monomial ideal

**Date:** 2026-07-05 · **Track:** T5 (external audit) / T9 (external corpus) · **Tier:** audit ·
**EV:** verification-amplification · **Gate:** GREEN (6/6 theorems kernel-decided, standard axioms)

## Target

Mafi, A., & Naderi, D. (2021). *Integral closure and Hilbert series of a special monomial ideal*
([arXiv:2112.02921](https://arxiv.org/abs/2112.02921)). For `M_{n,t} = (x^{e_1},…,x^{e_n})` with
`x^{e_i} = ∏_{j≠i} x_j^t` (each generator is the product of all variables *except one*, to the `t`):

- **Theorem 1.6** — the integral closure `M̄_{n,t}` equals the Veronese-type ideal `I_{(t(n−1); t,…,t)}`. For
  `n = 3`: `closure(M_{3,t}) = {x^u : min(a,t) + min(b,t) + min(c,t) ≥ 2t}`.
- **Corollary 1.7** — `M_{n,t}` is Cohen–Macaulay (unmixed), yet its integral closure `M̄_{n,t}` has
  **embedded primes**.

## What Leibniz verified (`n = 3`)

LLMs propose nothing here — the paper's claims are the objects; our Lean 4.31 kernel **decides**. Using the
general monomial-ideal instrument (`monomial_ideal_normality.py`, exact integral-dependence membership):

- **Theorem 1.6, confirmed** — `closure(M_{3,t})` (computed by integral dependence) equals the Veronese
  cap-sum ideal, cross-checked for `t = 1, 2, 3, 4` (the cap-sum predicate `min(a,t)+min(b,t)+min(c,t) ≥ 2t`
  is validated to equal the true closure over the whole box).
- **Corollary 1.7, confirmed** — the closure has the embedded prime `(x,y,z)` for `t ≥ 2`, witnessed by a
  monomial `u` with `u ∉ closure` but `x·u, y·u, z·u ∈ closure` (so `(closure : x^u) = (x,y,z)`) — for `t = 2`
  the witness is `xyz`. Meanwhile `M_{3,t}` itself has **no** such witness over the box: it is unmixed. The
  integral closure **gains** an embedded prime the original ideal lacks.

An honest detail our verification surfaces: at `t = 1`, `M_{3,1} = (xy,xz,yz)` is the squarefree Veronese —
already integrally closed and with *no* embedded prime; the phenomenon of Corollary 1.7 begins at `t = 2`.

The kernel certs (`t = 2, 3`) are `decide` over the cap-sum closure predicate (instrument-verified to equal
the true integral closure): `M_subsetneq_closure` (M ⊊ closure), `closure_embedded_prime`, and
`M_no_embedded_prime`. 6 theorems; `#print axioms` → standard set on each.

## Verdict

**Agreement** — no erratum. This is a clean independent kernel verification of a published integral-closure
result, showcasing the general monomial-ideal instrument on a second paper (after Ataka–Matsuoka), and
capturing the interesting phenomenon (closure gains an embedded prime) as a kernel-decided fact.

## Honest scope

Verified for `n = 3` (our instrument is `k[x,y,z]`); the paper's general-`n` statements are not re-proved. The
closure-equality is confirmed as instances (`t = 1..4`); the embedded-prime facts are complete decidable
witnesses. No trust surface touched — read-only kernel elaborations, `tests/test_invariants.py` byte-identical.

## Artifacts

- Certificate (downloadable): `docs/crt/mafi_naderi_certificate.lean` — 6 theorems
- Producer / verifier: `scripts/verify_mafi_naderi.py` · Tests: `tests/test_mafi_naderi.py`
- Result record: `docs/results/mafi_naderi_verification.json`

<!--
The F2b external formalization brief (scope doc §F2, "Draft external brief"), finalized per the operator's
2026-07-02 decision to send it. Self-contained: paste into an email / Mathlib Zulip thread / an Aristotle
project description as-is. Transmission is the operator's action (external channels + credentials).
-->

# Formalization brief — Schrijver's block-diagonalization of the Terwilliger algebra (Lean 4 + Mathlib)

**From**: the Leibniz theorem-daemon project (machine-checked upper bounds for binary codes; LLMs propose,
only the Lean kernel decides). **What we ask for**: (i) a Lean 4 + Mathlib formalization plan with lemma
decomposition, (ii) a gap analysis of which Mathlib pieces already exist, (iii) an estimate and staging.

## Target statement (the hard core — "Theorem 1", Schrijver 2005, eq. (7)/(8))

For the Terwilliger algebra of the binary Hamming scheme H(n,2): a matrix in the algebra, presented by the
triple-distribution variables `x^t_{i,j}`, is PSD **iff** each of the blocks `M_k` (k = 0..⌊n/2⌋) built from
the coefficients

```
β^t_{i,j,k} = Σ_u (−1)^{u−t} C(u,t) C(n−2k, u−k) C(n−k−u, i−u) C(n−k−u, j−u)
```

is PSD. Our validated convention is exactly this formula (binomials zero outside `0 ≤ b ≤ a`; the sign via
parity of `u−t`; `C(u,t)` — NOT `C(t,u)`). Sketch of the lemma we want admitted first, so our kernel data
plugs in directly:

```lean
lemma schrijver_block_diag (n : ℕ) (x : Triple n → ℚ) (hx : IsTripleDistribution x) :
    PosSemidef (Rmatrix n x) ↔ ∀ k, PosSemidef (Mblock n k x)
```

with `Mblock` defined via the eq. (7) β above. Natural staging: **admit this as one named,
citation-backed lemma first** (it shrinks our informal trusted base to a single statement), then discharge.

## Why the elementary proof path is preferred

Schrijver's own §II proof is elementary — an explicit orthogonal-ish basis change `U`, Propositions 2–5,
finite combinatorics — and minimizes Mathlib dependencies. We explicitly prefer it over abstract
C*-algebra/representation-theoretic machinery (S_n wreath actions, Specht modules), unless the gap analysis
shows the abstract route is genuinely shorter in current Mathlib.

## Ground truth and machine-checked context you can build against

- **β oracle**: `docs/results/terwilliger_beta_oracle.tsv` (TSV `n\tk\tt\ti\tj\tbeta`, nonzero entries) —
  validated against real-code PSD differential tests with corrupt controls (Phase 0).
- **Kernel-side β**: our F1 checker already *recomputes eq. (7) inside the Lean kernel* (core Lean,
  Pascal-table verified) and validates 12,155 entries at n=19 in seconds
  (`scripts/terwilliger_kernel_full.py`).
- **Weak duality is already formalized** (F2a, Lean+Mathlib, no sorries): `gram_pairing_nonneg` +
  `tw_weak_duality` in `scripts/terwilliger_f2a.py` — dual PSD-ness stated in the LDLT/Gram witness form
  our certificates emit. What remains for a full bridge is exactly: codes ⇒ primal-feasible, whose core is
  Theorem 1 above (plus R/R′ PSD via averaged outer products, Proposition 1, PSD congruence invariance,
  and eq. (21) `|C| = Σ C(n,i) x⁰_{i,0}`).
- **Payoff**: three kernel-attested certificates await the bridge — A(19,6) ≤ 1280, A(23,6) ≤ 13766,
  A(25,10) ≤ 503 — turning audit-tier bounds into kernel-checked statements about codes.

## The three asks, concretely

1. **Plan**: lemma-level decomposition of Theorem 1 (elementary §II route), with the admit-then-discharge
   staging above; identify the 2–3 riskiest lemmas.
2. **Gap analysis**: which pieces exist in Mathlib today (block matrices / PSD congruence / Krawtchouk-style
   sums / the U change-of-basis), and which must be built from scratch.
3. **Estimate**: expert-weeks, staged; what a first milestone (admitted-lemma wiring compiling end-to-end
   against our F2a statement) would take.

Reference: A. Schrijver, *New code upper bounds from the Terwilliger algebra and semidefinite programming*,
IEEE Trans. Inf. Theory 51 (2005) 2859–2866.

<!--
The F2b external formalization brief. REVISED 2026-07-03 (review response) after an 8-reviewer witness panel
(docs/results/terwilliger-f2b-witness-review-2026-07-03.md): trust framing corrected to match ADR 0046
(admitted lemma is NON-PROMOTING scaffold); target theorem restated algebraically (no 2^n matrix, no
IsTripleDistribution, bounded k, self-adjoint) with a forward-direction-first option; beta guarded-binomial +
beta=cert mandate; PSD pinned over R; un-normalized rational basis; scope table; self-contained for a cold
Mathlib recipient. Transmission is the operator's action (external channels + credentials).
-->

# Formalization brief — Schrijver's block-diagonalization of the Terwilliger algebra (Lean 4 + Mathlib)

## Project context (for a cold recipient)

**Leibniz** is a theorem daemon that produces **machine-verified upper bounds on binary code sizes** A(n,d):
LLMs and SDP solvers only *propose*; only the **Lean 4.31 kernel** and an exact-rational decision procedure
*decide*. We have three code-size bounds proved as **exact-rational dual certificates and kernel-attested at the
arithmetic level** (the "audit tier"): A(19,6) ≤ 1280, A(23,6) ≤ 13766, A(25,10) ≤ 503. What is *not* yet
machine-checked is the **mathematical bridge** from those certificates to statements about actual codes — the
subject of this brief. *(Glossary: **F1** = our in-kernel certificate checker; **F2a** = our Lean/Mathlib weak-
duality proof, done, no `sorry`; **F2b** = this bridge; "audit tier" = arithmetic kernel-checked but the
code-bridge not yet formalized.)*

**What we ask** (deliverable form in the last section): (i) a Lean 4 + Mathlib formalization **plan** with a
lemma dependency graph; (ii) a **gap analysis** answering the specific Mathlib questions below; (iii) an
**estimate** with confidence bands.

## Trust constraint (please read first — it shapes the whole ask)

An admitted lemma / `axiom` / `sorry` in Lean is a **formal trusted assumption**: any theorem depending on it
is kernel-checked *relative to* it, **not** a full proof. In our trust model this means:

- The block-diagonalization lemma may be introduced as a **named axiom for scaffolding only** (to wire
  interfaces and test the architecture). Any theorem depending on it is **audit-tier / CONDITIONAL and
  non-promoting** — it is never treated as a finished ("Q.E.D.") result.
- **Definition of finished**: an `#print axioms` closure on each final bound theorem that contains **no**
  project axiom (`schrijver_block_diag`, `sorryAx`, …) — only Lean/Mathlib's standard axioms.
- Corollary: admitting the lemma does **not** shrink our trusted base; it names the obligation. The real
  deliverable is the eventual `sorry`-free discharge. Please plan accordingly.

## Target theorem — state it ALGEBRAICALLY (not over the 2ⁿ space)

**Do not** state this over the ambient 2ⁿ×2ⁿ matrix: for n=19 that is 524288×524288 and does not type-check in
Lean. State it over the **Terwilliger algebra's intrinsic basis** (dimension `binom(n+3,3)`), i.e. as a
predicate on the coefficient family, or via a quadratic-form PSD predicate — never a literal 2ⁿ matrix.

Keep the algebraic block-diagonalization **separate** from code-derived constraints (do *not* bake
`IsTripleDistribution` into it — Schrijver's theorem is a fact about *any* self-adjoint element of the algebra):

```lean
-- (A) the pure algebraic theorem — self-adjoint Terwilliger coefficients, bounded k
theorem schrijver_block_psd_iff (n : ℕ) (a : TerwCoeff n ℚ) (ha : SelfAdjoint a) :
    PSD (terwMatrix n a) ↔ ∀ k, k ≤ n / 2 → PSD (schrijverBlock n k a)

-- (B) the code-side, later, using the algebraic theorem twice (for R and R′):
theorem code_triples_primal_feasible (C : Finset (Word n)) (h : MinDistAtLeast C d) :
    SchrijverPrimalFeasible n d (tripleDist C)
```

where `schrijverBlock n k a` has dimension `(n−2k+1)` and its entries are the eq.(7) β-combinations below.
`PSD` is **`Matrix.PosSemidef` over ℝ** (rational coefficients coerced to ℝ; our certificates are exact integer
Gram/LDLᵀ witnesses that imply real PSD). Mathlib's `Matrix.PosSemidef.conjTranspose_mul_mul_same` gives the
congruence step.

**Forward-direction-first (recommended scoping).** For the *bound* we need only the forward implication —
`PSD (terwMatrix n a) → ∀ k, PSD (schrijverBlock n k a)` — plus Proposition 1 (`R`, `R′` are Gram, hence PSD).
The reverse implication (blocks PSD ⇒ full PSD) is the harder algebraic half and is **not** needed for the
code bounds. A viable first milestone is forward-only.

## The β coefficients — and the Lean binomial hazard

```
β^t_{i,j,k} = Σ_u (−1)^{u−t} C(u,t) C(n−2k, u−k) C(n−k−u, i−u) C(n−k−u, j−u)
```

Convention (validated in our code): binomials are **zero outside `0 ≤ b ≤ a`**; sign via parity of `u−t`;
`C(u,t)` — **NOT** `C(t,u)`. **Lean hazard (please state to the formalizer):** raw `Nat` subtraction truncates,
so `Nat.choose (n−k−u) (i−u)` can become `Nat.choose 0 0 = 1` where it must be 0 — corrupting β. The formal β
**must** use a guarded / integer zero-outside binomial (e.g. `zchoose (a b : ℤ) := if 0 ≤ b ∧ b ≤ a then
Nat.choose a.toNat b.toNat else 0`); raw `Nat` subtraction is not acceptable in the spec. **Source-of-truth:**
the formal β definition must be provably equal to our certificate generator's β (our `C(a,b)` returns 0 outside
`0≤b≤a`, so it is already guarded) — otherwise a `sorry` on the theorem still leaks through a β mismatch.

## Normalization — stay in ℚ, avoid `Real.sqrt`

Schrijver's eq.(8) normalizes blocks by `binom(...)^{−1/2}` (irrational). **Do not** carry `Real.sqrt` /
algebraic numbers. Use the **un-normalized** orthogonal basis (scale by the binomials to clear denominators):
the resulting integer/rational blocks are congruent to Schrijver's up to a **positive rational diagonal**, which
preserves PSD. Please state this as a **named subgoal** (`posSemidef_congr_pos_diag`) and give the exact diagonal
scaling. Note the multiplicities `q_k = C(n,k) − C(n,k−1)`: PSD-iff is unaffected, but the SDP *objective/trace*
depends on them — please flag where they are handled downstream.

## Scope of the full bridge (Theorem 1 is the largest piece, not the only one)

| component | status |
|---|---|
| weak duality (dual feasible ⇒ obj ≤ Σγ−ν) | **done** — F2a, Lean+Mathlib, no `sorry` |
| in-kernel β recomputation vs eq.(7) | **done** — F1, validates 12,155 entries at n=19 |
| **block-diagonalization (Theorem 1, forward)** | **the ask** — this brief |
| R, R′ are Gram ⇒ PSD (Proposition 1) | in scope (medium; independent of Theorem 1) |
| objective identity `|C| = Σ C(n,i) x⁰_{i,0}` (eq. 21) | in scope (combinatorial, small) |
| PSD congruence invariance | Mathlib provides `conjTranspose_mul_mul_same` |
| code def / min-distance / triple distribution / integer rounding | in scope (plumbing) |

Concrete end-to-end target (so a plan can be checked against the pipeline):

```lean
theorem code_bound_19_6 : ∀ C : Finset (Word 19), MinDistAtLeast C 6 → C.card ≤ 1280
```

## Recommended $0 pre-check (before any Lean work)

Validate the *statement* (not just β values) computationally: a small Python/Sage script that, for n = 6, 8, 10,
builds the un-normalized `U`, checks `Uᵀ U` diagonal-positive and `Uᵀ M^t_{i,j} U` block-diagonal with entries
matching our β oracle (exact rational). GREEN → the axiom you admit is the *right* statement; RED → a
sign/index mismatch to fix before formalizing. (Our F1/D1 validate β *values*; the U/block-diag *statement* is
not yet independently checked.)

## The three asks — deliverable form

1. **Plan** — a lemma dependency graph (Layer 0 finite/cube basics → … → block-diagonalization → normalization
   congruence → code⇒feasible → bound), each node with: statement sketch, Mathlib deps, difficulty, risk,
   "admittable temporarily? y/n". Name the 2–3 riskiest lemmas. *Deliverable: a ≤4-page markdown doc.*
2. **Gap analysis** — answer specifically: (a) does Mathlib have PSD congruence for the (possibly
   rank-collapsing) change of basis, beyond `conjTranspose_mul_mul_same`? (b) Krawtchouk / signed-Krawtchouk
   `U` — is the existing `Krawtchouk` def usable, or is Schrijver's `U` a variant to build? (c) Hahn
   polynomials / their orthogonality — present or absent? (d) `blockDiagonal'` for dependent block sizes and an
   n-block PSD-iff lemma — present or to-build? (e) the signed-binomial triple sums in `U`-orthogonality —
   any existing identities? *Deliverable: a gap table.*
3. **Estimate** — expert-weeks with confidence bands, staged: (i) admitted-wiring milestone (a `sorry`-free
   algebraic signature + the `sorry`-free corollary linking to our F2a `tw_weak_duality`); (ii) Proposition 1;
   (iii) full discharge. Please calibrate against our internal read (**~1–2 weeks** wiring; **~3–6 months** full
   discharge, less if forward-only) and flag 2×/5× scenarios.

## Route

We *suspect* Schrijver's elementary §II route (explicit `U`, Propositions 2–5, finite combinatorics) is the only
viable path given Mathlib's current gaps (no hyperoctahedral representation theory / association-scheme
machinery), but we do **not** want to over-prescribe: please **confirm or compare** against any
abstract/representation-theoretic route that is shorter in current Mathlib, and recommend the path with the
fewest new hard lemmas.

## Ground truth you can build against

β oracle: `docs/results/terwilliger_beta_oracle.tsv` (`n	k	t	i	j	beta`, nonzero entries). Machine-checked
context: our F2a Lean file (`scripts/terwilliger_f2a.py` — `gram_pairing_nonneg`, `tw_weak_duality`); F1
in-kernel β checker (`scripts/terwilliger_kernel_full.py`). Target Mathlib: the revision pinned in our
`lean-toolchain` (Lean 4.31 + Mathlib v4.31.0) — we will share the exact commit and a compiling skeleton
(F2a signatures + stubs) on request.

Reference: A. Schrijver, *New code upper bounds from the Terwilliger algebra and semidefinite programming*,
IEEE Trans. Inf. Theory 51 (2005) 2859–2866 (§I–II; Theorem 1, eq. (7)/(8)).

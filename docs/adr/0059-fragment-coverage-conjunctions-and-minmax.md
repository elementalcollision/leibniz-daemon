# ADR 0059 — Fragment coverage: modular conjunctions + min/max algebraic identities

**Status:** **PROPOSED — blocked on adversarial review.** Widens the *covered fragment* of the
ceiling-raiser (ADR 0056 faithfulness + ADR 0058 prover) from a single modular atom / residue-set to
the two clean shapes the conjecturer (ADR 0053) actually produces beyond it: **conjunctions of modular
atoms**, and **min/max symmetric-function identities**. Each is a coordinated extension of *both* the
faithfulness backend (a claim must be certified before it is proven) *and* the decision-procedure
prover. Per the ADR 0051/0054/0055/0056/0057/0058 precedent, **no code ships until this design clears
its own ≥3-lens adversarial review.** The **trust boundary is untouched**: the Lean kernel decides every
proof and certifies every faithfulness pair; `TrustPolicy.validate_path` and `tests/test_invariants.py`
stay byte-identical; both new procedures are exact-or-DEFER and fail-closed behind the same
`LEIBNIZ_LEAN_DECIDED` activation.

## Context — the conjecturer out-reaches the fragment

Activating the ceiling-raiser let two-variable *single-atom / residue-set* modular laws promulgate
end-to-end (proved). But a live cycle showed the conjecturer's raised ambition now produces **compound**
claims the fragment does not cover — e.g. `(a²+b²)%4≠3 ∧ ((a²+b²)%4=2 ↔ a,b both odd)`,
`max(a,b)²+min(a,b)² = a²+b²`. The binding constraint moved to **fragment coverage**. A kernel prototype
(`scratchpad/proto_compound.py`) established which shapes are cleanly reachable by the existing
backbones:

- **Conjunctions of modular atoms — PASS.** `refine ⟨?_, ?_⟩`, then the existing per-atom ZMod bridge on
  each conjunct.
- **min/max symmetric identities — PASS.** `rcases le_total a b <;> simp [max_eq_*, min_eq_*] <;> ring`.
- **Biconditionals / mixed-modulus — deferred** (feasible via an LCM reduction, but needs more proof
  automation; a later increment, out of scope here).

## Decision (proposed, pending review)

Two independent decision procedures, each extending faithfulness + prover in lockstep. Both keep the ADR
0058 shape: a deterministic generator emits a kernel-checked proof; the kernel re-verifies (a generator
bug ⇒ DEFER, never an unsound law); promotion is on the single kernel verification via the residue
DEMONSTRATE fast-path; faithfulness is certified by a sound backend gated by the same trust discipline.

### 1. Modular conjunctions (extends the ZMod backbone)

- **Classifier.** `classify_property` gains a `conjunction` skeleton: a top-level `And` whose every
  conjunct is a currently-admitted atom (`poly % m ⋈ c`, eq/neq) **sharing one modulus `m`** and drawing
  variables from the common set. Mixed moduli ⇒ **reject** (DEFER) in this increment — a conjunct with a
  different modulus is not admitted (avoids the LCM machinery). Each atom keeps the static residue-range
  guard (`0 ≤ c < m`) and the pure-poly / var-count / residue-budget guards.
- **Faithfulness (`lean_decided`).** The pair's property leg becomes
  `∀ vars, box → established → claim_domain → (P₁ ∧ … ∧ Pₖ)`; proved by the ZMod key
  `∀ vars : ZMod m, (P₁ᶻ ∧ … ∧ Pₖᶻ)` (still one `decide`, finite), then the ℤ bridge splits the
  conjunction and lifts each atom exactly as today. Coverage / ∃-witness / discrimination controls are
  unchanged (they are about the domain, not the property's boolean shape). A **false** conjunct makes the
  `decide` refuse ⇒ DEFER.
- **Prover (`residue_law` / fast-path).** The canonical LAW is `∀ vars, box → claim_domain → (P₁∧…∧Pₖ)`;
  the proof is `refine ⟨…⟩` over the conjuncts, each discharged by the existing per-atom ZMod bridge. The
  fast-path, `theorem_src` binding (A2), axiom footprint (A4), and lean_decided-edge requirement are all
  inherited unchanged.

### 2. min/max symmetric-function identities (a new order-split decision procedure)

This is **not** modular — it is an algebraic identity over `min`/`max`, so it is a **separate** technique
and a **separate faithfulness path + prover**, not a change to the ZMod code.

- **Shape.** `∀ vars, <LHS> = <RHS>` (a conjunction of equalities allowed) where LHS/RHS are polynomials
  in the variables and `min(·,·)`/`max(·,·)` of variables — an identity that becomes a polynomial
  identity once each `min`/`max` is resolved by the variable ordering. Restricted to `min`/`max` of two
  variables (nesting/≥3-ary deferred).
- **Faithfulness + Prover (one order-split decision procedure).** Both the faithfulness property leg and
  the promulgated law are the identity itself; the decision procedure proves it by
  `rcases le_total a b with h | h <;> simp only [max_eq_left, max_eq_right, min_eq_left, min_eq_right, h] <;> ring`
  (generalised to the claim's variables' pairwise orderings). **A non-identity makes `ring` fail on some
  branch ⇒ the kernel rejects ⇒ DEFER** — the kernel gates truth, exactly as for the modular procedures.
  This backend stamps a distinct producer (`minmax_identity/kernel`) to be admitted to
  `FAITHFULNESS_PRODUCERS` by the operator (ADR 0041), like `lean_decided/kernel`.

### 3. Both stay kernel-gated, exact-or-DEFER, fail-closed

- The kernel decides every proof (`discharge`) and certifies every faithfulness pair; a generator/classifier
  bug can only DEFER (kernel rejection) — never promulgate an unproven or false law.
- `validate_path` / `is_promotable` / `test_invariants` are **byte-identical**; the two new faithfulness
  producers are admitted to `FAITHFULNESS_PRODUCERS` by the operator, the ADR 0041 seam.
- Fail-closed behind `LEIBNIZ_LEAN_DECIDED`; the residue fast-path already falls through for anything its
  generators abstain on.

## Red-team targets for the adversarial review

- **Conjunction soundness.** Can a conjunction with a *false* conjunct promote? (The ZMod key's `decide`
  must refuse; the per-atom bridge must fail on the false atom.) Can the classifier admit a conjunction
  with **mixed moduli** and then build a wrong single-`m` key (must reject mixed moduli)? Nested `And`,
  `And` of non-atoms, empty/degenerate conjunction.
- **min/max prover soundness.** Can it "prove" a **non-identity** (must fail on some `le_total` branch ⇒
  DEFER)? Does the order-split enumerate *all* pairwise orderings for ≥2 min/max variables, or can a
  missing branch leave a false identity provable? Does `ring` over ℤ close only genuine identities? Is
  the min/max faithfulness genuinely a *decision procedure* (deterministic, kernel-gated), warranting the
  ADR 0041 producer admission?
- **Faithfulness–proof statement binding (A2) for both families.** The promulgated LAW must be the DSL
  contract the faithfulness backend byte-bound; confirm the conjunction / identity renderings are
  character-identical between the faithfulness `canonical_statement` and the prover's `law_statement`.
- **Vacuity / discrimination.** The ∃-witness vacuity control must still gate the conjunction path; a
  min/max identity over an empty domain must DEFER. Trivial identities (`a = a`) are the non-triviality
  gate's job (runs first) — confirm the ordering.
- **Fragment guards.** Every new admitted shape must be exact-or-DEFER; a shape outside both procedures
  (biconditional, mixed-modulus, ≥3-ary min/max) must DEFER, not mis-classify.

## Consequences

- The ceiling-raiser covers the compound-conjunction and min/max families the conjecturer already
  produces — more of its output promulgates end-to-end.
- Two new decision procedures enter the trust model under the established "judgment quorum-gated /
  decision kernel-gated" distinction (ADR 0058), each admitted by the operator after its own review.
- Biconditional / mixed-modulus modular claims remain DEFERred (a well-scoped later increment with the
  LCM reduction), and the fast-path falls through for them — no regression.
- Not implemented until this design clears its ≥3-lens adversarial review, and each built procedure clears
  a code-level review before its producer is admitted / activated — the same gate every prior step passed.

# ADR 0059 — Fragment coverage: modular conjunctions + min/max algebraic identities

**Status:** **REVIEWED — SPLIT; both families BUILT.** Modular conjunctions: **ACCEPTED (amendments
A.1–A.4)**, shipped in PR #350. min/max identities: **BUILT (amendments B.1–B.4)** as a separate
decision procedure (`leibniz/gates/minmax_decided.py` + `leibniz/providers/minmax_prover.py`),
kernel-confirmed end-to-end, behind its own code-level review before the `minmax_identity/kernel`
producer is activated. Widens the *covered
fragment* of the ceiling-raiser (ADR 0056 faithfulness + ADR 0058 prover) from a single modular atom /
residue-set to the two clean shapes the conjecturer (ADR 0053) actually produces beyond it:
**conjunctions of modular atoms**, and **min/max symmetric-function identities**. Each is a coordinated
extension of *both* the faithfulness backend (a claim must be certified before it is proven) *and* the
decision-procedure prover. Per the ADR 0051/0054/0055/0056/0057/0058 precedent, **no code ships until
this design clears its own ≥3-lens adversarial review.** The **trust boundary is untouched**: the Lean
kernel decides every proof and certifies every faithfulness pair; `TrustPolicy.validate_path` and
`tests/test_invariants.py` stay byte-identical; both new procedures are exact-or-DEFER and fail-closed
behind the same `LEIBNIZ_LEAN_DECIDED` activation.

## Adversarial review outcome (4 lenses) — the families split

The ≥3-lens review adjudicated the two families **separately**, and a controlled kernel run confirmed
every soundness claim:

- **Modular conjunctions — ACCEPTED, safe to build with amendments.** The family *inherits* the
  already-wired end-to-end path: `classify_property` → `property_proof` (faithfulness) and
  `residue_law` → `_law_proof` (prover) all render from the one shared `render_pred`, and `templates[KIND]`
  is already registered — so the **A2 statement-binding is inherited byte-for-byte**. Every failure mode is
  fail-closed: a false conjunct, mixed moduli, or a plumbing error makes `decide` refuse or the ℤ-bridge
  type-mismatch → the kernel rejects → **DEFER**. Kernel-confirmed: `(a*a)%4≠3 ∧ (a*a)%4=2` (false
  conjunct) **DEFERs**; the three true single-modulus conjunctions (eq+eq, eq+neq same poly, neq+neq diff
  poly) **prove**. The only real work is the multi-atom `Skeleton` and the explicit single-modulus guard.
- **min/max identities — HELD (not safe as written).** The order-split **tactic is sound** — kernel-confirmed
  that a false identity (`max a b + min a b = a`), a missing-branch case (`min a b + max b c = a + c` under a
  single split), and an inequality-shaped goal all fail closed → DEFER (a true identity like
  `max a b ^2 + min a b ^2 = a^2 + b^2` proves). But the ADR as written claims a promotion path that
  **does not exist**: the residue fast-path `_promote` structurally rejects min/max (`residue_law`→
  `classify_property` abstains, and `_promote` requires a `lean_decided/kernel` edge), and the prose invites
  a naive new fast-path that would skip the `templates[KIND]` statement-pin and re-open the ADR 0058
  mis-stated-law hole. The fix is pure wiring+binding (B.1–B.4), deferred to its own increment.

### Required amendments — modular conjunctions (folded into this increment)

- **A.1** Extend `Skeleton` to carry per-atom `(op, poly, c)` with one shared modulus `m`; the proof is
  `refine ⟨…⟩` over the conjuncts, each discharged by a per-atom ZMod key (`∀ vars:ZMod m, Pᵢᶻ := by decide`)
  and the existing eq/neq bridge. **Net-new code, not a residue-set copy.** (Per-atom keys, each independently
  `decide`-closed, are equivalent in soundness to one big conjunction key and simpler to bridge.)
- **A.2** The new `And` branch of `classify_property` enforces **one shared modulus** (`len(moduli)==1`)
  explicitly; rejects nested `And`, non-atom conjuncts, and empty/degenerate conjunctions; each conjunct
  keeps the static residue-range guard (`0 ≤ c < m`) and pure-poly guard via the reused `_atom`.
- **A.3** The residue budget and `MIN/MAX_VARS` are computed on the **union** `free_vars(cd, cp, ed)` across
  all conjuncts (`decide_certificate`/`applies`/`residue_law` already pass the union — the classifier feeds it).
  A conjunct cap (`MAX_CONJUNCTS`) bounds the total decide work.
- **A.4 (load-bearing invariant).** The promulgated law is rendered from the DSL (`law_statement`→`render_pred`),
  independent of the per-atom proof skeleton. This is the **Net-2** that makes a mis-encoded atom **DEFER
  rather than mis-state**: the statement the kernel proves is the DSL contract, so a classifier that built the
  wrong single-`m` skeleton yields a proof that fails to elaborate against the true statement → DEFER.

### Required amendments — min/max identities (HELD for the follow-up increment)

- **B.1** Specify a **separate min/max fast-path** (gated on a `minmax_identity/kernel` edge) that **re-renders
  the law from the DSL** (`replace(theorem_src=…)`), never the autoformalizer's free text — mirror
  `residue_prover._promote`. (Or state explicitly that min/max never promotes-on-one and rides the ensemble.)
- **B.2** Its `register()` must install **both** `recheckers[KIND]` **and** `templates[KIND]` (a
  `prop_statement_template` from the identity's fields); without the template, `faithfulness.py` leaves
  `bound=True` and the statement is unbound.
- **B.3** Own the fragment restriction **at the classifier**: top-level `Eq` (or conjunction of `Eq`), every
  `min`/`max` a bare 2-arg call over variables; reject ≥3-ary, nested, non-Eq, compound-arg (the renderer
  already admits these, so the classifier must be the gate). Record the branch bound `2^C(nvars,2)` (≤8 at
  `MAX_VARS=3`).
- **B.4** The min/max faithfulness leg is domain-free, so the ∃-witness vacuity control does no work here;
  the ADR must say so rather than imply it "still gates."
- **Terminology.** The order-split is a **sound proof-search heuristic** for the restricted class, not a
  complete decision procedure (compound/nested args DEFER). Describe it as such in the producer admission.

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
  `∀ vars, box → established → claim_domain → (P₁ ∧ … ∧ Pₖ)`; proved by `refine ⟨…⟩` over the conjuncts,
  each conjunct discharged by its **own** per-atom ZMod key (`∀ vars : ZMod m, Pᵢᶻ := by decide`, finite)
  and the existing eq/neq ℤ-bridge. (Per-atom keys — each independently `decide`-closed over `ZMod m` — are
  soundness-equivalent to one big conjunction key and simpler to bridge; validated against the kernel.)
  Coverage / ∃-witness / discrimination controls are unchanged (they are about the domain, not the
  property's boolean shape). A **false** conjunct makes *its* `decide` refuse ⇒ DEFER.
- **Prover (`residue_law` / fast-path).** The canonical LAW is `∀ vars, box → claim_domain → (P₁∧…∧Pₖ)`;
  the proof is `refine ⟨…⟩` over the conjuncts, each discharged by the existing per-atom ZMod bridge. The
  fast-path, `theorem_src` binding (A2), axiom footprint (A4), and lean_decided-edge requirement are all
  inherited unchanged.

### 2. min/max symmetric-function identities — BUILT (a new order-split decision procedure)

> **Built per B.1–B.4** in `leibniz/gates/minmax_decided.py` (the order-split faithfulness backend) and
> `leibniz/providers/minmax_prover.py` (`MinMaxDemonstrate`, the separate fast-path), wired opt-in via
> `assembly.maybe_register_minmax_decided` / `maybe_wrap_minmax` behind the same `LEIBNIZ_LEAN_DECIDED`
> activation, producer `minmax_identity/kernel` admitted to `FAITHFULNESS_PRODUCERS`. How the amendments
> landed:
> - **B.1** `MinMaxDemonstrate` mirrors `ResidueDemonstrate`: gates on a `minmax_identity/kernel`
>   faithfulness edge and **re-renders the LAW from the DSL** (`minmax_law` → `law_statement`/`render_pred`),
>   never the autoformalizer's free text; kernel-gated, promote-on-one, axiom-closed.
> - **B.2** `register()` installs **both** `recheckers[KIND]` and `templates[KIND]` (`prop_statement_template`).
> - **B.3** The fragment is owned at the classifier (`classify_identity` / `_mmpoly`): top-level `Eq`, every
>   `min`/`max` a bare 2-arg call over two distinct variables, ≥1 min/max present, branch budget
>   `2^#pairs ≤ 8`. ≥3-ary / nested / compound-arg / non-Eq / pure-poly all DEFER (kernel-confirmed).
> - **B.4** The identity is domain-free, so the ∃-witness legs add no power to its truth; they remain a
>   deliberate **non-vacuity gate over the non-negative witness box** (identical to the modular path — an
>   empty/out-of-box `claim_domain` DEFERs). A faithful identity over a negative-only or large domain is a
>   conservative out-of-scope yield choice this increment, never an unsound outcome.
>
> **Scope:** this increment admits a **single top-level `Eq`** (the review's "conjunction of `Eq`" is a
> natural, deferrable extension — it would `refine ⟨…⟩` the equalities and order-split each). The
> order-split is a **sound proof-search heuristic** (complete for the restricted fragment; compound/nested
> args DEFER), not a complete decision procedure. Kernel-confirmed: `max²+min² = a²+b²` and a 3-var
> two-pair sum promulgate end-to-end; `max+min = a` (false), the absolute-value trap `max−min = a−b`, and
> nested min/max (out of fragment) all DEFER.
>
> **Code-level review outcome (5 adversarial lenses + completeness critic):** no soundness, correctness,
> or trust-boundary findings survived verification. Three LOW items were folded in: a collision-proof
> hypothesis base (`_hyp_base`) so a claim variable literally named `h0` yields a valid proof rather than a
> spurious DEFER; the B.4 witness-leg wording above; and a **pre-activation operator note** below.
>
> **⚠ Pre-activation operator note (novelty coverage).** The fragment admits an infinite family of *true
> but textbook-trivial* symmetric identities (`max(a,b)+min(a,b)=a+b`, `max·min=a·b`, commutativity). These
> are sound laws, but they are non-results; the only thing between them and the ledger is the
> non-triviality + retrieval-novelty gates (which run in FORMALIZE, before any proof). **Before activating
> `minmax_identity/kernel`, confirm the novelty corpus / non-triviality gate quarantines the canonical
> trivial min/max identities as KNOWN** (or seed the corpus with them), so activation raises real yield,
> not textbook noise. This is a quality gate, not a soundness one — the trust boundary is unaffected.

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

## Follow-on increments (the two remaining frontiers, now built)

Both frontiers this ADR originally deferred are now built as separate, reviewed increments:

### Path A — conjunction of `Eq` min/max identities (extends `minmax_decided`)

`classify_identity` also accepts a top-level conjunction of ≤ `MAX_MINMAX_EQS` `Eq` min/max identities;
the proof splits with `refine ⟨…⟩` and order-splits each equality (over the union of pairs). Rides the
existing `minmax_identity/kernel` producer + fast-path — no new trust surface. Kernel-confirmed.

### Path B — biconditional / same-modulus boolean combinations (`boolean_decided` + `boolean_prover`)

A **third** decision procedure generalising `lean_decided` from a single atom / residue-set / conjunction
to an **arbitrary boolean combination** — `∧`, `∨`, `¬`, and **biconditionals `↔`** — of eq/neq modular
atoms **sharing one modulus**, over nonlinear polynomials (e.g. `(a·b)%3=0 ↔ (a%3=0 ∨ b%3=0)`).

- **Renderer.** A small, conformance-covered extension to the audited `dsl_to_lean._prop`: `(P) == (Q)`
  between *boolean* operands renders to `P ↔ Q` (and `!=` to `¬(P ↔ Q)`) — Python has no `↔`. Arithmetic
  equalities are unchanged; the differential conformance suite now evaluates `↔` over the negative grid.
- **Proof (ZMod-decide, kernel-validated).** `have key : ∀ vars:ZMod m, Q_zmod := by decide` decides the
  whole boolean formula; one uniform per-atom bridge `(Int.emod poly m = c) ↔ ((↑poly:ZMod m)=↑c)` (proved
  `rw [ZMod.intCast_eq_intCast_iff']; show …%… ; omega` — the `show` converts the `Int.emod` goal to `%`
  so `omega`, which groks `%` not raw `Int.emod`, can finish); `rw` the atoms, `push_cast`, discharge with
  the key. A **false** formula makes the `decide` refuse ⇒ DEFER.
- **Fragment (owned at the classifier).** Single shared modulus (mixed moduli DEFER); eq/neq atoms over
  pure polys with `0 ≤ c < m`; `and`/`or`/`not`/`↔` structure only. Disjoint-in-practice from `lean_decided`
  by cost order (cost 93). Producer `boolean_modular/kernel`, admitted to `FAITHFULNESS_PRODUCERS`.
- **Kernel-confirmed:** `(a·b)%3=0 ↔ (a%3=0 ∨ b%3=0)` promulgates end-to-end (Q.E.D., is_promotable); a
  false biconditional and a mixed-modulus claim DEFER.

**Still deferred:** **nonlinear mixed-modulus** claims (`(a+b)²%4` vs `(a+b)%2`) — the emod-push across
differing moduli / castHom reduction is not yet a robust gate-owned tactic. `omega` cleanly decides the
*linear* mixed-modulus fragment, but that overlaps the existing Z3 probe, so it is not separately wired.

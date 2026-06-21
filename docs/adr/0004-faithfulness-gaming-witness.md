# ADR 0004 — The Gaming-Witness Encoding (R2)

- Status: Accepted
- Date: 2026-06-21
- Related: ADR 0002 (faithfulness gate — the strategy), ADR 0001 (trust tiers);
  resolves operator decision D3 (`_negate` encoding: "Z3-predicate path primary").

## Context

ADR 0002 made the gaming-witness the spine of the faithfulness gate but left
`_negate` — turning a `falsifiable_claim` into a *searchable* predicate — a
placeholder (`f"NOT({claim})"`), so the adversarial spine passed vacuously. ADR 0002
named this "the primary R2 research task." This ADR fixes the encoding for the
measurable claim types we support first.

## The gaming pattern we catch first: domain narrowing / vacuous specialization

The most common, most dangerous faithfulness gap is a formal statement that is
kernel-true but **weaker than the human claim** — typically by *narrowing the
domain*. The Enuntiatio asserts a property over a claim domain; the formal theorem,
while provable, only establishes it over a sub-domain (e.g. an extra `n ≥ c`
hypothesis, or a single instance). The ledger then reads as if the full claim were
proven.

We model a measurable claim as three arithmetic predicates over an input `n`:

- `claim_domain(n)` — the inputs the Enuntiatio quantifies over;
- `claim_property(n)` — what it asserts holds on that domain;
- `established_domain(n)` — the domain the **formal statement** actually covers
  (extracted from the theorem's hypotheses).

A **gaming witness** is an `n` such that:

```
claim_domain(n) ∧ ¬established_domain(n) ∧ ¬claim_property(n)
```

— an input the claim covers, the proof leaves unconstrained, and on which the
claimed property can fail. If such an `n` exists, the statement underspecifies the
claim → `FAIL`, `FinishReason.GAMED`.

## Decision

**1. `_negate` and the search target.** The faithfulness gate calls
`SMTBackend.find_gaming_witness(statement, negated_claim, bound)` with:

- `statement` = `¬established_domain(n)` — the region the proof leaves open;
- `negated_claim` = `_negate(claim)` = `claim_domain(n) ∧ ¬claim_property(n)`.

`find_gaming_witness` returns a model of `statement ∧ negated_claim` (the witness),
or `None` ("survived"). A faithful statement (`established_domain ⊇ claim_domain`)
makes the conjunction UNSAT → no witness.

**2. Z3 over a small, safe predicate DSL** (`leibniz.backends.smt_z3`). Predicates
are boolean/arithmetic expressions over one integer `n` (`+ - *`, comparisons,
`and/or/not`), parsed by a whitelisted `ast` walk — never `eval`. An un-encodable
predicate degrades to "no witness", never a crash and never a false PASS.

**3. SMT only ever kills.** A model = refuted/gamed; UNSAT = survived, never
"proven". The Lean kernel remains the only thing that proves (ADR 0001).

**4. Scope.** This handles arithmetic, decidable-fragment claims (the bulk of
analysis-of-algorithms complexity/correctness bounds expressible over input size).
Claims whose property is not arithmetically expressible fall to the claim-type
probe (mechanical) or, for `OPEN_FORM` only, the bounded JUDGED fallback.

## Consequences / sequencing

- **R2b** wires this into the (trust-guarded) `gates/faithfulness.py`: a real
  `_negate`, the `COMPLEXITY_BOUND` / `CORRECTNESS_OVER_DOMAIN` probes, and
  extraction of `established_domain` from the formal statement. That is the
  guarded-core change and lands behind the PreToolUse hook + operator review.
- **R2c** wires the `OPEN_FORM`-only JUDGED fallback and enforces
  `max_judged_faithfulness_fraction` (the budget counter, per the plan review).
- The honest limit: `established_domain` extraction is only as good as our reading
  of the Lean hypotheses; until that is robust, a measurable claim with no decisive
  probe still returns `DEFER`, never PASS (ADR 0003 guard) — so a weak encoding
  cannot launder an unfaithful statement through.

## Non-goals

- Encoding non-arithmetic claims in Z3 (information-theoretic sorting bounds, etc.)
  — those rely on the kernel + probes, not the SMT witness.
- Letting an UNSAT gaming search count as positive evidence of faithfulness — it
  only means "this cheap adversary found nothing".

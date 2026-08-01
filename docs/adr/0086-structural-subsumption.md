# ADR 0086 — Persist `claim_domain`; detect subsumption structurally

- Status: accepted
- Date: 2026-07-28
- Depends on: ADR 0034 Stage 0 (persisting `claim_property`), ADR 0052 (self-ledger novelty)

## Context

The daemon promulgated `max² − min² = (max − min)(a + b)` while already holding a law whose
**first conjunct is exactly that fact**, commuted. Both sit in the operator's review queue as
separate work.

## The approach that does not work, and why

The obvious test is semantic: ask a solver whether the held property *implies* the candidate's —
`decide([held, ¬candidate])` unsat. **This is vacuous between theorems.** Every held law is true
on its domain, so `¬candidate` is unsatisfiable *on its own* and the premise contributes nothing.
Measured on the live ledger: it flagged **10 of 29** held laws — including `5cad1e53`, the
strongest one and one of the two already published — on the strength of nothing. Verified
directly: for three of the flagged laws, `decide([¬cp])` with **no premise at all** returns
`True`.

That is the third instance of the same vacuity class found today (ADR 0075's coverage leg
`D ∧ ¬D`; its amendment's empty domain). It was caught only because ten flags on twenty-nine laws
looked implausible enough to check rather than report.

An earlier draft also compared claim *domains* — and silently assumed the held law's equalled the
candidate's, because `CorpusEntry` has no `claim_domain` and **the ledger never persisted one**.

## Decision

**1. Persist `claim_domain`** (`runtime.py`), with the same idempotent `ALTER TABLE` migration
pattern the other late-added columns use. Without it nothing downstream can tell *where* a stored
law applies, which is what made a sound comparison impossible.

**2. `structural.subsumes(held_domain, held_property, cand_domain, cand_property)`** — syntactic,
no solver:

- domains must be **identical text**, so the held law applies exactly where the candidate claims
  and nothing is assumed about domains that were never compared;
- the candidate's top-level conjunct set must be a **proper subset** of the held law's, so the
  candidate asserts strictly less.

Conjuncts are canonicalised with commutative `==`/`!=` operands sorted — without which the check
misses the very case it exists for, since the daemon wrote its equality the other way round.

## Consequences

Catches the live pair (`f73da540` ⊂ `5cad1e53`), is asymmetric, and is silent on unrelated laws,
identical laws (that is `contains_equivalent`'s job), differing domains, and any candidate holding
a conjunct the held law lacks.

**Conservative by construction.** It misses semantically-redundant laws written in structurally
different form — algebraically equivalent but differently factored, say. Every miss is a *failure
to flag*, never a false flag, which is the correct direction for anything touching what the
operator reviews.

**Not yet wired to a consumer.** The predicate ships with its tests; where it is used — annotating
the review queue, or quarantining at the novelty gate — is a separate decision, and the earlier
draft showed why that choice deserves its own scrutiny rather than riding along.

# ADR 0074 — `established_domain` is derived, not authored, for decided-fragment claims

- Status: accepted
- Date: 2026-07-24
- Depends on: ADR 0001/0002 (charter + faithfulness gate), ADR 0022 (mechanical contract
  steering), ADR 0056/0058 (the lean-decided backend and the A2 statement-binding argument)
- Evidence: [`gamma3b-verdict-2026-07-24.md`](../results/gamma3b-verdict-2026-07-24.md)

## Context

Roughly half the daemon's dead candidates are dead for **contract** reasons, not mathematical
ones. Of 54 DEFERred ledger rows carrying a DSL property, 25–29 are decidable by procedures
already shipped and registered; 8 of the 12 most recent tail candidates died before any proof
compute.

The mechanism: `established_domain` is free text the autoformalizer writes ("the DSL predicate the
formal statement ACTUALLY establishes the property on"). When the model folds the claim property
into that field, the faithfulness pair's **coverage** leg becomes the theorem itself, the kernel
refuses it (`reason='kernel did not accept coverage'`), and the candidate DEFERs. Worse, it
recurs: `weakening_seeds` re-proposes the same claim, which re-DEFERs — `(a^2 + b^2) % 4 != 3`
DEFERred on five separate days before finally being promulgated.

**Correction to the γ3b write-up.** That document attributed the failure to ADR 0022's
`_steer_contract` "failing closed because its guards need a conclusive `decide_unsat`". That is
not the operative link. `_steer_contract`'s repair trigger is `not encodable(pred)` — a **syntax**
test — and a property-restating `established_domain` is perfectly encodable DSL, so the repair
loop never fires for this defect at all. (The `decide_unsat` fail-closed is real, but it guards
the *property-weakening* check on an already-attempted repair.) The measured `decide_unsat`
`None` results on this fragment stand; their significance was mis-stated.

## Decision

`Formalize._derive_established_domain`, run after `_steer_contract` and before the gate: for a
claim a **registered decided-fragment backend owns**, set `established_domain := claim_domain` —
mechanically derived rather than model-authored.

### Why this is sound

It fires only when some registered sound backend `applies()` to the canonicalized contract — i.e.
a fragment whose `*Demonstrate` fast-path **re-renders the promoted law from
`(claim_domain, claim_property)` and discards the autoformalizer's statement** (ADR 0058 A2). For
such a claim the promoted theorem establishes the property on the whole of `claim_domain` *by
construction*. So `established_domain = claim_domain` is not an assertion about an unseen
statement — it is a fact about the statement that will actually be proved.

Nothing is certified here. The gate then decides the entire pair with the kernel, exactly as
before. A **false** claim still fails its property leg and is refused — pinned by a live-kernel
test: with the identical derivation applied, `(a^2+a*b+b^2) % 9 != 6` and `(a^2+b^2) % 4 != 3`
certify via `lean_decided/kernel`, while `((4*a+1)*(4*b+3)) % 8 == 3` is **DEFERred**.

Placement matters and is forced: the gate's statement-binding template renders the canonical
statement from **prop's own fields**, and the certificate must match it byte-for-byte. A backend
that canonicalized internally would fail that binding. The derivation therefore belongs on the
prop, before the gate, where prop, certificate and template all render the same bytes.

### What it deliberately does not do

- Never touches `claim_property` — no property can be weakened.
- Never widens `claim_domain`.
- Refuses unless `claim_domain` is **conclusively** satisfiable (`decide_unsat` returning `False`);
  unsat would launder a vacuous PASS, and `None` (unknown) fails closed.
- Refuses when no decided backend is registered, when none owns the claim, when the SMT backend
  is absent, and on any classifier exception. Every failure path leaves the contract untouched and
  the candidate DEFERs exactly as it does today.

## Residual gap (pre-existing, now more frequently reached)

If the gate PASSes via a decided backend but the fast-path does **not** promote (e.g. the kernel
rejects the re-rendered law), the candidate falls through to the LLM ensemble, which proves the
autoformalizer's own `theorem_src` — a statement the certificate did not bind. This gap exists
today for every decided-backend PASS; this ADR does not create it, but it does make it reachable
more often. Closing it properly means rendering `Expressio` from the contract for these fragments
(making FORMALIZE mechanical), which is a larger change and deliberately not bundled here.

## Consequences

Expected: a large fraction of the DEFERred ledger becomes reachable by procedures already shipped,
with no new prover reach — the γ3b conclusion inverted into yield. The `steering` block and
`reached_proof` counts in the nightly journal will show it directly.

One observation recorded for honesty: during validation the derivation once silently no-op'd in a
pytest run that could not subsequently be reproduced (4 consecutive green runs afterwards,
including an instrumented one showing all guards satisfied). The direction of that failure is
fail-closed — a missed derivation costs a candidate, never a wrong verdict — but it is noted
rather than dismissed.

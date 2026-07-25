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

It fires only when a backend on an explicit **`_RERENDERING_BACKENDS` allowlist** `applies()` to
the canonicalized contract — a fragment whose `*Demonstrate` fast-path **re-renders the promoted
law from `(claim_domain, claim_property)` and discards the autoformalizer's statement**
(ADR 0058 A2). For such a claim the promoted theorem establishes the property on the whole of
`claim_domain` *by construction*. So `established_domain = claim_domain` is not an assertion about
an unseen statement — it is a fact about the statement that will actually be proved.

The allowlist is explicit, in the idiom of `trust.py`'s `FAITHFULNESS_PRODUCERS`, because
`applies()` **alone is strictly broader and the soundness argument does not cover it**: `walnut`
is also a registered `SoundFaithfulnessBackend` (cost_rank 50, ahead of `lean-decided`'s 90), it
`applies()` to claims the decided backends decline, and it has **no re-rendering prover**.
Deriving for a Walnut-owned claim would assert coverage of a statement nothing re-renders. This
hole was found by adversarial review of the first draft, which shipped the bare `applies()` test;
a test now pins the distinction.

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

## Consequence recorded: the ADR 0004 gaming spine goes vacuous on these candidates

With `established_domain = claim_domain = D`, the gate's independent gaming probe searches
`not(D) AND D AND not(P)` — unsatisfiable for **any** D and P. Every candidate this touches
therefore loses its adversarial gaming leg and rests entirely on the MECHANICAL backend leg (the
kernel deciding the full pair). This is arguably correct under A2 — with no ed/cd mismatch there
is nothing for the spine to find — but it is a real reduction in independent checks and is
recorded here rather than left implicit. It is *bounded* by the allowlist: only re-rendering
fragments are affected.

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

**The flake, now diagnosed.** During validation the derivation once silently no-op'd in a run that
would not reproduce. Adversarial review supplied the mechanism: `decide_unsat` -> `_decide` sets
`solver.set("timeout", 3000)` — a **wall-clock** budget — so under machine load Z3 returns
`unknown`, `decide_unsat` returns `None`, and the conclusive-satisfiability guard fails closed.
(The validation run in question coincided with 40+ Lean containers from parallel review agents
saturating the host.) The derivation is therefore **load-dependent**: it is never wrong, but it
silently yields less on a busy machine. Accepted for now — the direction is fail-closed and the
cost is one candidate — and worth revisiting if journal `reached_proof` counts look load-correlated.

## Review

Reviewed adversarially before merge (four independent attack angles: trust soundness, proposer
bypass, regression surface, code review + test quality). The review found and this change fixes:
the `walnut` soundness hole above; a `str.__ne__` crash on a non-`str` LLM-authored field (these
come from `_parse_expressio` JSON and are not guaranteed to be strings — it now type-checks and
DEFERs); guard ordering that paid for six classifier renders before free structural checks; and
four **vacuous tests**. Every guard is now mutation-tested by hand — removing it turns the suite
red — except one that was found genuinely redundant (`any([])` is already `False`) and was deleted
rather than given a decorative test.

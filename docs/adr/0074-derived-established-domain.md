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

`FaithfulnessGate._retry_with_derived_domain`, invoked **inside the sound-backend dispatch loop**
when a backend DEFERs: re-ask *that same backend* with `established_domain := claim_domain`, and
commit the derived contract to the Propositio **only** if the retry earns a PASS that the gate's
own `_accept_certificate` accepts — re-checked by the gate's re-checker *and* byte-bound to its
statement template. Otherwise the field is restored byte-exactly.

### Why it must live in the loop — a rejected design, and why

The first draft derived the field in `Formalize.run`, before the gate. **Adversarial review
demonstrated that version was unsound**, end-to-end against the real kernel: a FALSE claim reached
`kernel_verified` + `Q.E.D.` + `TrustPolicy.validate_path` ACCEPT.

The flaw: `applies()` is DSL *routing*, not a verdict. When a re-rendering backend applied and
then DEFERred, the mutation survived into paths where **nothing re-renders the statement**, and
`established_domain` is the one field tying the gate to the Lean statement. Two independent checks
went vacuous by construction:

- the coverage leg became `decide_unsat([D, ¬D])` — UNSAT for **every** claim, so it could never
  fail;
- the ADR 0004 gaming spine's target became `¬D ∧ D ∧ ¬P` — empty, so the spine was **disarmed**.

`ClaimProbe` then passed the claim on a bounded `[0,64]` search over a domain the box
misrepresents, and DEMONSTRATE proved the autoformalizer's own, never-bound `theorem_src`.

The in-loop design closes all three: the spine has **already run** on the original contract above
the loop; the probe and the OPEN_FORM judge are reached only *after* rollback; and the derived
value is never visible to any consumer unless the backend that justifies it earned an accepted
certificate with it. `_accept_certificate` is extracted verbatim so there is exactly one place a
certificate becomes a PASS — the retry cannot drift from the normal path.

### Guards (each mutation-tested: removing it turns the suite red)

- Only backends on `_RERENDERING_BACKENDS` — an explicit allowlist in the idiom of `trust.py`'s
  `FAITHFULNESS_PRODUCERS`, because `walnut` is also a registered sound backend and has **no**
  re-rendering prover.
- Only on DEFER. A PASS whose certificate the gate *rejected* gets no second chance.
- Never when already canonical (no wasted kernel call, no Z3 call).
- Only when `claim_domain` is **conclusively** satisfiable; unsat would launder a vacuous PASS and
  `None` (unknown) fails closed.
- Non-`str` contract fields DEFER instead of raising (`_parse_expressio` passes LLM JSON through).
- Byte-exact rollback on DEFER, FAIL, failed re-check, failed statement binding, or any exception.

`claim_property` and `claim_domain` are never touched, so no property can be weakened and no
domain widened.

## Scope note: a PRE-EXISTING probe weakness, not introduced here

The review's exploit claim (`(a*a+b*b) % 16 == 2` over `a,b > 60, ≡ 1 mod 4` — false at
`(61,65)`, but the only in-box point `(61,61)` satisfies it) is passed by `ClaimProbe` on
**`origin/main` too**, verified directly. With this change the derived contract is rolled back and
the gate behaves identically to main on that claim. The bounded probe's blindness to
box-unrepresentative domains is real and worth its own increment; it is **out of scope** here and
is not made worse.

## Consequences

Expected: a large fraction of the DEFERred ledger becomes reachable by procedures already shipped,
with no new prover reach — the γ3b conclusion inverted into yield. Cost: one extra backend
`check()` (four kernel calls) on the DEFER population of allowlisted fragments only. The
`established_domain_derived` flag rides on the edge detail as ledger provenance.

**Load-dependence.** `decide_unsat` uses a 3-second *wall-clock* Z3 budget, so on a busy machine
it returns `None` and the satisfiability guard fails closed — the derivation silently yields less
under load. Never wrong; noted for the journal.

## Review

Reviewed adversarially before merge (trust soundness, proposer bypass, regression surface, code
review + test quality). The soundness angle returned **DO_NOT_SHIP / critical** on the first
draft, with the end-to-end demonstration above; that draft was discarded rather than patched, and
this design is the reviewer's. Review also fixed: a `str.__ne__` crash on non-`str` fields, guard
ordering, and four vacuous tests. Every guard is now mutation-tested by hand.

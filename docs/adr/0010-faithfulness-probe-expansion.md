# ADR 0010 — Expand the Faithfulness Claim-Type Probe Table (Proposed)

- Status: **Proposed**
- Date: 2026-06-21
- Related: ADR 0002 (faithfulness gate), ADR 0004 (structured claim contract);
  `gates/faithfulness.py`, `probes.py`. **Touches the guarded core** (operator
  sign-off via the PreToolUse hook). Roadmap item #3.

## Context

R2b shipped the mechanical fast path for `COMPLEXITY_BOUND` and
`CORRECTNESS_OVER_DOMAIN` (a domain-coverage probe). Every other measurable
`ClaimType` — `OPTIMALITY`, `INVARIANT`, `EXISTENCE`, `STRUCTURAL` — has no probe,
so it returns `DEFER` and cannot promulgate. ADR 0002 named the probe table "the
highest-leverage incremental work": more probes ⇒ more claims adjudicated on the
*sound mechanical path* rather than deferred or laundered.

## Decision (proposed)

Write one decisive probe per measurable `ClaimType`, dispatched by type (the router
stays on the gate, per ADR 0002), each checking that the formal statement actually
encodes the claimed property:

- `OPTIMALITY` → a matching lower bound meets the achieved upper bound (no slack).
- `INVARIANT` → the quantity is preserved across the operation (pre = post).
- `EXISTENCE` → the witness/construction is exhibited and satisfies the predicate.
- `STRUCTURAL` → the algebraic/order shape holds (e.g. the stated morphism laws).

Each probe **PASSes only on a decisive mechanical check; otherwise DEFER, never a
judge** (the non-negotiable from ADR 0002). Probes are SMT/structure-based,
injected via `probes.default_probes` (no guarded edit to add a probe — only wiring
the dispatch in `gates/faithfulness.py` if the dispatch shape changes).

## Options considered

- **(a) Per-type mechanical probes — proposed.** Maximizes sound coverage.
- (b) Rely on the gaming-witness alone. Misses positive certification; more DEFERs.
- (c) Judge fallback for measurable claims. **Rejected** — laundering (ADR 0002).

## Consequences

- More promulgation on the mechanical path; fewer DEFERs.
- The probe table is growable; each probe is independently testable (a vacuous vs.
  faithful example per type).
- Guarded: any change to `gates/faithfulness.py` requires operator sign-off; the 11
  invariant tests must stay green and unedited.

## Open questions

- Some claim types (e.g. OPTIMALITY over arbitrary algorithms) may have no decisive
  arithmetic probe — those legitimately stay DEFER, and that is acceptable.

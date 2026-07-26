# ADR 0076 — Single-variable claims enter the decided fragments

- Status: accepted
- Date: 2026-07-25
- Depends on: ADR 0056/0058 (the lean-decided fragment), ADR 0075 (which made the old rationale
  untenable)

## Context

`lean_decided.MIN_VARS` was 2, with the comment *"1-var claims stay on the cheap Z3 probe
(invariant 5)"*. Invariant 5 says run the cheap gates before the expensive one, and the premise was
that Z3 handles the single-variable modular fragment cheaply.

**That premise is false**, and ADR 0075 removed what was left of it:

- Z3 does not decide much of this fragment. Measured: `(n^4) % 16 in {0,1}`, `(n^4) % 10 in
  {0,1,5,6}` and `(n^2) % 8 in {0,1,4}` all return `unknown` inside the box.
- Since ADR 0075 the probe requires **both** legs decidable *unbounded*, so those claims now have
  no certifying path at all — not the probe, and not a fragment that excluded them by arity.
- **18 of the daemon's 23 promulgated laws are single-variable.** The largest population it
  actually produces was outside every kernel decision procedure it has.

## Decision

`MIN_VARS = 1`. One constant: every guard (`lean_decided` :430/:501, `residue_prover` :123, and the
sibling fragments) reads the shared value.

## Consequences

Single-variable claims now reach the kernel backends, which run **before** the probe in the gate's
cost-ordered dispatch — so this does invert the original invariant-5 intent for that population:
roughly four kernel calls per candidate where previously there were none. Measured on live claims:
10.3 s cold, 0.2 s warm. That is affordable at nightly-beat volume, and it buys the fragment's
whole point — a single-variable claim can now become a kernel-verified law instead of dying at a
solver that cannot decide it.

The kernel still decides: a false single-variable control (`(n^4) % 5 == 2`) is refused, and two
true ones certify via `lean_decided/kernel`.

Five existing tests pinned the old boundary by using a 1-var claim as their "outside the fragment"
example. Each keeps its intent — arity outside `[MIN_VARS, MAX_VARS]` must abstain — with a 4-var
claim instead. No guard was removed.

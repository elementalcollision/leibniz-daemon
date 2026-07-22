# ADR 0071 — The Z3-unknown second opinion (Phase γ, leg 2)

- Status: accepted
- Date: 2026-07-22
- Depends on: ADR 0067 (cvc5 cross-solver attestation — the infrastructure and the activation
  flag this reuses)

## Context

ADR 0067 pointed cvc5 at Z3's conclusive **unsat** verdicts (attestation, kill-only). The queued
follow-on was the opposite direction: Z3's **unknown** verdicts, where a probe simply loses —
`decide_unsat` returns None, a faithfulness probe cannot certify, a triviality check cannot
conclude. Every unknown is yield silently left on the table. cvc5's different engine
(CDCL(T) vs Z3's tactics; different nonlinear handling) will conclude on some queries Z3 gives
up on.

## Decision

`_second_opinion_unknown(solver)` on `_decide`'s unknown tail, symmetric in shape to
`_cross_check_unsat` and behind the **same activation** (`LEIBNIZ_CVC5_CROSSCHECK` + the cvc5
extra — one operator switch for both cvc5 roles):

- cvc5 re-decides the EXACT SMT-LIB2 script Z3 could not conclude on.
- **Only an `unsat` rescue is adopted** (→ the probe's conclusive True). A cvc5 `sat` here
  carries no re-verifiable witness (the cross-check pipeline keeps models off), so it is counted
  (`unknown_kept`) but NOT adopted — refutation witnesses remain Z3's job, where the model is
  extracted and self-validating. `unknown`/`None`/any exception keep `unknown`: a second opinion
  must never break a probe.
- Two new `CROSS_STATS` counters — `unknown_rescued` / `unknown_kept` — flow into the heartbeat
  journal's existing `cross_stats_delta` automatically, so the morning read shows how much yield
  the second opinion actually recovers (if it stays 0, this was free; if it grows, it earned its
  keep).

## Trust argument

Adopting cvc5's unsat where Z3 had no opinion is the **same trust class** as adopting Z3's own
unsat: a mechanical solver's kill/probe verdict. Nothing about promotion changes — solvers still
never promote; `kernel_verified` is still written only by `LeanVerifier.discharge`; the ADR 0041
producer whitelist is untouched. The asymmetry (unsat adopted, sat not) is deliberate: unsat
feeds gates that fail closed anyway, while sat would assert the existence of a counterexample we
cannot exhibit — so it is not asserted.

## Consequences

- Probes blocked by Z3-unknown (typically nonlinear shapes near the box edges) now conclude when
  cvc5 can decide them; measured, not assumed, via the journal counters.
- Cost: one extra cvc5 call per Z3-unknown (rare), only when the operator has cvc5 active.
- Future (if `unknown_kept` shows many cvc5-sats): a model-extracting path whose witness is
  re-verified by ground evaluation before adoption — sound sat-rescue, deferred until the
  counters justify it.

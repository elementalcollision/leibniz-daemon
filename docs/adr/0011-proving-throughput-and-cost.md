# ADR 0011 — Proving Throughput & Cost Governance (Proposed)

- Status: **Proposed**
- Date: 2026-06-21
- Related: ADR 0003 (Lean backend), ADR 0006 (consensus proving);
  `backends/lean_cli.py`, `consensus.py`, `assembly.py`. Non-guarded. Roadmap #4.

## Context

Measured in the live runs: each Lean check is ~1.3 s (Mathlib oleans reload per
`lake env lean` invocation), the N+1 consensus provers run **sequentially**, there
is no cross-cycle result cache, and there is no spend cap on a deliberately costly
("even if costly") consensus proof. Once ADR 0009 produces candidates at volume,
the proof stage dominates wall-clock and cost.

## Decision (proposed)

1. **Persistent Lean container.** Wire `LeanCliBackend(persistent=True)` (built in
   R1c, unused in `build_daemon`) — removes ~25% per-check container churn.
2. **Lean REPL backend (the big win).** A long-lived Lean process with the candidate's
   import set preloaded, so Mathlib isn't reloaded per check. New `LeanReplBackend`
   behind the same `LeanBackend` protocol; falls back to the CLI backend.
3. **Concurrent prover ensemble.** Run the consensus provers' drafts + discharges
   concurrently (threads/async) instead of sequentially — N-way speedup on proof.
4. **Cross-cycle result cache.** Persist the structural-hash-keyed result cache so
   identical statements/proofs are never re-checked across cycles.
5. **USD budget cap.** A token-based spend estimator + `LEIBNIZ_DAILY_USD_CAP`;
   stop the cycle when the cap is hit; surface spend in `CycleReport` (mirrors
   Leonardo's `LEONARDO_DAILY_USD_CAP`).

## Options considered

- Persistent container vs REPL: do both — container is cheap and immediate; the
  REPL is the real throughput lever but more work. Cache + concurrency are additive.
- Budget as a hard stop vs advisory: **hard stop** (consensus is costly by design).

## Consequences

- Lower `$ / promulgation` and wall-clock; sustained autonomous runs become
  affordable and bounded.
- Soundness unaffected — these are performance/cost mechanisms; the kernel + N+1
  consensus still decide (ADR 0001/0006). All non-guarded.

## Open questions

- REPL crash/restart handling and per-import-set process pooling.
- Spend estimation accuracy across Anthropic vs OpenRouter pricing.

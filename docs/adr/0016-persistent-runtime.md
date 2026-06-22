# ADR 0016 — Persistent runtime (the Chimera seam, self-contained) (Accepted)

- Status: **Accepted** (implemented 2026-06-21)
- Date: 2026-06-21
- Related: ADR 0001 (trust hierarchy), `adapters.RuntimeAdapter` (the "Chimera"
  seam). `leibniz/runtime.py`, `assembly.py`. Non-guarded. Roadmap: Tier 3.

## Context

`adapters.RuntimeAdapter` is the body ("Chimera") seam: scheduling, persistence,
witness/telemetry. The only implementation was `assembly.SimpleRuntime`, a stub —
memory was an in-process list that vanished on exit, and `now_phase()` was the
constant `"WAKE"`. For sustained autonomous discovery the runtime needs to be real:
a candidate ledger that survives restarts, and a genuine circadian phase.

The external Chimera system is not available as a checkout in this environment
(unlike Leonardo's Forge, wired via `LEONARDO_FORGE_PATH`). Operator decision: build
a **self-contained** real runtime now and keep external-Chimera wiring as a
documented drop-in behind the same Protocol.

## Decision

`leibniz/runtime.py::PersistentRuntime` implements `RuntimeAdapter`:

1. **SQLite-backed memory.** `remember(prop)` upserts the candidate's record
   (statement, claim type, formal hash, kernel_verified, qed, finish reason,
   lineage); `recall_recent(n)` returns the newest-first reconstruction. The ledger
   **survives restarts** — a new process on the same DB sees prior sessions. Path
   via `LEIBNIZ_RUNTIME_DB` (default `.leibniz/memory.db`, gitignored); `:memory:`
   for ephemeral use.
2. **Clock-based circadian phase.** `now_phase()` returns WAKE / NREM / REM by
   hour-of-day, with an injectable clock for tests — not a constant.
3. **Witness seam.** `witness()` returns `[]` (documented): cross-model agreement
   needs a provider ensemble wired here, future work. The faithfulness
   gaming-witness uses Z3 (mechanical), so nothing in the trust path depends on it.
4. **Lazy connection.** The DB opens on first `remember`/`recall`, so constructing
   the runtime in `build_daemon` touches no filesystem until the daemon runs —
   `build_daemon` stays construct-only.

The real assembly uses `PersistentRuntime`; `SimpleRuntime` remains for the
deterministic demo/fakes.

## Options considered

- Integrate the external Chimera vs. a self-contained runtime: **self-contained** —
  no Chimera checkout exists here; this removes the stub now and the external system
  drops in later behind the unchanged Protocol.
- JSON file vs. SQLite for memory: **SQLite** — concurrent-safe, queryable
  (newest-first, caps), and the natural shape for the eventual Chimera memory.

## Consequences

- The body's substrate is real: memory persists, phase is genuine. Sustained runs
  accumulate a durable ledger.
- Trust unaffected: the runtime records and recalls only — it writes no
  `EdgeEvidence`, sets no `kernel_verified`, and is not in the promotion path.
  `tests/test_invariants.py` byte-identical.

## Open questions

- `now_phase()` is not yet a *gate* — the loop doesn't throttle work by phase. Using
  the phase to schedule cheap vs. expensive stages is a future enhancement.
- Cross-model `witness()` and full external-Chimera scheduler/telemetry remain
  seams.

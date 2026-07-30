# ADR 0082 — The beat watches for equilibria, not just errors

- Status: accepted
- Date: 2026-07-28
- Depends on: ADR 0068 (the heartbeat and its anomaly scan)

## Context

On 2026-07-26..28 every beat exited 0 with no alarm, and the daemon was mining its easiest genre
at its lowest difficulty. The frontier band had saturated against its floor (ADR 0080) and the
family key was too fine to ever retire a genre (ADR 0081). **Both controllers were working exactly
as written, toward a worse and worse place.**

`detect_anomalies` could not have caught it. It looks at one beat and asks *what broke* —
cross-solver disagreement, errored candidates, leaked containers, zero seeds. Nothing broke. The
condition was only visible by reading several beats side by side, which is what the operator
happened to do when they asked whether last night's run had happened.

## Decision

`detect_equilibria(entry, home)` reads the **journal's history**, not one beat, and reports drift:

- **a band that has not moved at all** across the window — converged or pinned; at a bound it is
  pinned, the case ADR 0080 exists to break;
- **`too_hard` at capacity with no genre retired** — the weakening loop recycling the same
  near-misses;
- **the review queue past 30** — publication, not discovery, is the throughput limit;
- **amplification targets queued and unconsumed** — the feed filling with nothing reading it.

Reported alongside anomalies, journaled under `equilibria`, and alarmed with a `DRIFT:` prefix.
**Advisory: drift alone never changes the exit code.** A daemon that has stopped exploring has not
broken, and treating it as a failure would train the operator to ignore rc=3.

## Consequences

The signals are cheap — all four are computed from files the beat already writes.

Validated against the live journal: the `too_hard` detector fires (a real standing condition), and
the band detector correctly stays **silent**, because ADR 0080 fired in production between beats —
the band history is `[0.15, 0.15, 0.57, 0.502]`, escaped and homing back down. That is both a test
of the detector and the first production confirmation of ADR 0080.

Thresholds (3 beats, 12, 30, 5) are judgment, not measurement. They should move once there is
enough journal history to know what normal looks like.

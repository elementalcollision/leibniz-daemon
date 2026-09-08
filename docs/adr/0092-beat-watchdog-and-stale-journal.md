# ADR 0092 — A hung beat must not be silent

- Status: **accepted — landed, mutation-checked, and validated against the live production journal**
- Date: 2026-09-08
- Depends on: ADR 0068 (the heartbeat), ADR 0082 (drift detection — the sibling that watches for a
  daemon that stopped exploring, where this watches for one that stopped *finishing*)

## Context

The journal entry is written at the **end** of a beat. So a beat that hangs writes nothing: no
entry, no anomaly, no alarm. It is indistinguishable from a night the schedule has not reached yet,
and the daemon's own silence is its failure mode.

Observed live on 2026-09-08 while running a beat for an unrelated reason: the 01:30 launchd beat
had been running **6h57m**, holding two Lean containers, with the last journal entry still dated
`2026-09-06T01:30:07Z`. Fifty-five hours of silence, two missed nights, and nothing watching.

It is not a one-off. The journal already records a **26931 s (7.5 h)** beat that *did* complete —
and raised nothing, because `detect_anomalies` inspected cross-solver disagreement, errored cycles,
leaked containers and preflight degradation, but never duration.

## Decision — three guards, because there are three distinct failures

**1. A hard watchdog that journals before it kills** (`_arm_watchdog`). A daemon thread armed
around the beat; at `LEIBNIZ_BEAT_MAX_S` (default **14400**; see below) it closes the Lean backends, writes a `timed_out` journal entry,
alarms, and exits 3.

It journals **before** exiting on purpose. A watchdog that killed silently would fix the container
leak and keep the blind spot — the operator would still see no entry and still could not tell a
hang from a quiet night. Pinned by a subprocess test, because the path ends in `os._exit`.

**2. A soft budget between cycles.** Past half the ceiling the beat stops *starting* new cycles,
records why, and finishes normally. This is for the beat that is merely slow: it should journal
like any other beat rather than be killed mid-cycle. It explicitly **cannot** help a beat wedged
inside a single cycle — which is what seven hours means — and that is the watchdog's job. The two
guards are not redundant; they cover different failures.

**3. A stale-journal alarm** (`stale_journal_alarm`), run at beat start, before anything can hang.
This is the *outside* view: the watchdog fixes future beats, this notices that past beats went
missing. Alarms when the newest entry is older than `LEIBNIZ_JOURNAL_MAX_AGE_H` (default **48** —
the schedule is daily, so two missed nights is unambiguous).

Deliberately silent when there is **no journal at all**: a daemon that has never run is not a
daemon that broke. It only reads, so it is safe to call from a cron or a health check as well as
from the beat.

And `detect_anomalies` now inspects `duration_s`, warning above half the ceiling — so a beat that
is degrading is visible before one that is wedged gets killed. The historical 26931 s beat would
now alarm.

## Evidence

Run against the real production state at `/Users/dave/Claude_Primary/leibniz/.leibniz`:

```
stale_journal_alarm(production) ->
  STALE JOURNAL: no beat has journalled in 55.2h (limit 48h; last entry 2026-09-06T01:30:07Z).
  A hung beat writes nothing — check for a live heartbeat process before assuming the schedule
  simply did not fire.
```

That is the live incident, detected by the check written for it. All three guards are
mutation-checked: disabling the age comparison, the duration check, or the watchdog's wait each
turns its tests red.

## Consequences

A beat can no longer disappear. The worst case is now a `timed_out` entry and an alarm, which is a
strictly better failure than silence.

**No trust surface.** `scripts/heartbeat.py` is orchestration: it turns cycles, journals, and
regenerates the review queue. It promulgates nothing and publishes nothing; the trust boundary and
the ADR 0033 operator act are untouched.

**What this does not do:**

- It does not diagnose *why* a beat hangs. Both observed hangs held Lean containers, which points
  at the REPL, but neither was traced. The watchdog converts an invisible hang into a loud one; it
  does not remove the cause.
- **The first default was wrong, and measurement caught it within the hour.** 3600 s was chosen as
  ~9x the 404 s production median. A beat running *while this ADR was being written* was then
  measured at **1h51m and 96% CPU sustained** (106 min of CPU in 111 min elapsed) — healthy, heavy,
  and it would have been killed by its own new watchdog. Raised to 14400 s (4 h), which still kills
  both observed hangs (6h57m and 7.5h) with room to spare.
- **Duration is the wrong discriminator; CPU rate is the right one.** The hang sat at ~14% CPU; the
  healthy heavy beat at 96%. A wedged beat is *idle*, and idleness separates the two cases far more
  sharply than wall-clock does. Implementing that needs per-process CPU accounting the beat does
  not collect today, so this ADR ships the blunt instrument and names the sharp one.
- `LEIBNIZ_BEAT_MAX_S=0` disables the watchdog entirely, for an operator-supervised run. That is an
  escape hatch, not a default.
- Nothing here runs the stale check *between* beats. If the daemon stops being scheduled at all,
  the next beat is what notices — and there is no next beat. An external cron calling
  `stale_journal_alarm` would close that gap; this ADR only makes the function available to one.

# ADR 0094 — Wedged is not slow: detect stalls, don't guess durations

- Status: **accepted — landed, mutation-checked, and forced by a beat that falsified its predecessor twice**
- Date: 2026-09-08
- Amends: ADR 0092 (the watchdog and its duration ceiling)

## Context

ADR 0092 gave the beat a wall-clock ceiling, and the number was wrong twice in one day.

| ceiling | chosen because | refuted by |
|---|---|---|
| 3600 s | "~9x the 404 s production median" | a healthy beat at **1h51m, 96% CPU** — measured while the ADR was being written |
| 14400 s | "4 h separates a heavy beat from a wedged one" | the same beat, still healthy at **3h41m, 96.6% CPU**, 30 min from the new ceiling |

A threshold that needs re-tuning on every fresh observation is not measuring the thing that
matters. ADR 0092 already said so — *"duration is the wrong discriminator; CPU rate is the right
one"* — and shipped the blunt instrument because the sharp one needed accounting the beat did not
collect. **That claim was also too strong**, and this ADR is the correction.

## The measurement that killed the simple idea

Two facts from the same machine on 2026-09-08:

- The 7 h production hang sat at **~14% CPU**.
- A **healthy** beat sat at **96.6% CPU for 3h41m** — and wrote **nothing** to its state directory
  for the last 3.5 h of that.

So each signal, alone, is unsound:

- **Low CPU** means *wedged* **or** *blocked on a Lean container*. The kernel runs in Docker, so a
  beat waiting on a proof is idle **by design**. A CPU-only check kills legitimate work.
- **No progress** means *wedged* **or** *computing hard*. A progress-only check would have killed
  the healthy beat above, which advanced nothing on disk for hours.

## Decision — the conjunction, over a window, after a floor

`_StallWatch` samples `(wall, cpu_seconds, newest_state_mtime)` every 60 s and calls a beat
**wedged** only when, across a sustained window, CPU is low **and** state has not advanced:

```
low CPU  AND  no progress   -> wedged      (the 7h hang)
low CPU  AND  progress      -> alive       (blocked on Lean, advancing)
high CPU AND  no progress   -> alive       (the healthy heavy beat)
window not full / too early -> unknown     (never kill on thin evidence)
```

Defaults: 1800 s window, 1800 s floor, 10% of one core. Pure logic with no clocks or threads of its
own, so the decision is unit-testable — the thread only feeds it samples.

**The duration ceiling is demoted to a backstop** and raised to 8 h. It no longer decides anything
the stall detector can see; it only bounds what the stall detector misses. The stall detector
catches the real case in ~30 minutes instead of 7 hours.

**Telemetry is journalled on every beat**, not only on a kill. ADR 0092 admitted the hang was never
diagnosed; `cpu_rate`, `samples`, `progressed_in_window` now appear in each entry so the next one
can be.

## Consequences

The three observed shapes are classified correctly, each pinned by a test named for the case that
refutes the naive rule. All three guards are mutation-checked: dropping the progress term, dropping
the CPU term, or removing the floor each turns tests red.

**No trust surface.** `scripts/heartbeat.py` is orchestration; it promulgates nothing and publishes
nothing.

**What this does not do:**

- It still does not diagnose *why* a beat wedges. Both hangs held Lean containers, which points at
  the REPL, and neither was traced. This makes the next one loud and leaves telemetry behind; it
  does not remove the cause.
- `os.times()` counts only **reaped** children, so CPU burned inside a live Docker container is
  invisible. That is fine for the cases measured — the healthy beat burned CPU in the Python
  process itself — but a beat whose work is *entirely* inside a container would read as low-CPU and
  rely on the progress signal alone.
- The window and floor are still numbers, and still chosen from few observations. The difference
  from ADR 0092 is that they now bound *evidence gathering*, not the verdict: getting them somewhat
  wrong delays a kill, where getting the old ceiling wrong killed healthy work.

# ADR 0068 — The heartbeat: Phase α of the autonomy plan

- Status: accepted
- Date: 2026-07-21
- Depends on: ADR 0033 (operator publish gate), ADR 0055–0067 (the activated pipeline the
  heartbeat turns), the frontier path split (#378)

## Context

The autonomy plan (delivered 9 July 2026) asks for Leonardo-class autonomy: a slow,
ever-moving-forward freedom to explore, create, and conjecture. Until now every activated
discovery run was a hand-launched terminal session — the daemon only "lived" while an
operator (or an operator's agent) was watching it. Phase α is the smallest increment that
changes this: **the daemon acquires a pulse** — a scheduled, capped, journaled beat that
runs without anyone present — while changing *nothing* about what may reach the world.

## Decision

A nightly launchd LaunchAgent (`com.elementalcollision.leibniz.heartbeat`, 02:30 local)
runs one **beat** via a bootstrap installed *outside* any checkout
(`~/.leibniz-heartbeat/launch.sh`), which:

1. **Runs operator-merged code only.** The bootstrap fetches and hard-syncs a dedicated
   worktree (`.leibniz/heartbeat-wt`) to `origin/main` before every beat. The daemon never
   executes a working tree or a feature branch unattended; what runs at night is exactly
   what was reviewed and merged by day.
2. **Preflight or abort loudly** (`scripts/heartbeat.py::preflight`): Docker daemon up
   (auto-restarting OrbStack, the failure observed twice in live operation), Lean REPL
   image present, Z3 importable, `.env` present. Any hard failure → journaled abort,
   alarm, exit 2 — never a silently skipped night.
3. **Beat = N capped circadian cycles** (`LEIBNIZ_HEARTBEAT_CYCLES`, default 2) with
   `LEIBNIZ_LEAN_DECIDED` defaulted on, the operator's standing `.env` activation
   (including the ADR 0067 cvc5 cross-check), and `LEIBNIZ_DAILY_USD_CAP` defaulted to
   $5 — never uncapped on a schedule. State is canonical: the primary repo's
   `.leibniz/memory.db` and frontier band, via the #378 split env vars.
4. **Journal every beat** (`.leibniz/journal.jsonl`): funnel counts, dispositions, ADR
   0067 `CROSS_STATS` delta, duration, anomalies. Append-only; the operator can read a
   morning's beat in one line.
5. **Anomalies are loud, kill-only** (`detect_anomalies`): cross-solver disagreement,
   errored candidates/cycles, leaked Lean containers (image-filtered count — foreign
   containers are none of our business), and the all-zero-seeds signature of the
   2026-07-09 frontier misconfiguration. Anomalies → `alarms.log` + best-effort macOS
   notification + exit 3.
6. **Nothing publishes itself.** Promulgations land in the runtime DB and are surfaced in
   a regenerated `review_queue.md` ("Promulgated ≠ published"). Publication to
   codexcalculemus.com remains the operator's ADR 0033 act, exactly as before.

## Trust argument

The heartbeat adds **zero** new trust edges. It calls `build_daemon()` +
`circadian_cycle()` — the same assembly every hand-launched run uses — so every decision
inside a beat is still made by the kernel/Z3 behind the unchanged `TrustPolicy`. The only
new powers are *scheduling* (launchd), *observation* (journal/alarms/queue), and *spend*
(explicitly capped). The `.env` credentials copy in the run worktree is deleted after
every beat.

## Consequences

- The daemon now moves forward nightly without attention; the operator reviews a journal
  and a queue instead of babysitting terminals.
- A wedged night self-reports (exit codes 2/3, alarms.log, notification) instead of
  silently not happening.
- Phase β (seed self-steering, arXiv amplification feed) can build on the journal's
  funnel telemetry; Phase γ/δ unchanged.
- Disable at any time: `launchctl bootout gui/$(id -u)/com.elementalcollision.leibniz.heartbeat`.

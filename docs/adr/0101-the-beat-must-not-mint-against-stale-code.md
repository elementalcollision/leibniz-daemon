# ADR 0101 — the beat must not mint against stale code, silently

**Status:** **BUILT.** `deploy/heartbeat/launch-heartbeat.sh` now verifies that the beat worktree is
at `origin/main` and **aborts** if it is not, matching how the docker precondition already behaves.
The trust boundary is untouched; this is the *delivery* path, not the checker.

## What happened

ADR 0068 says the daemon *"always runs the latest OPERATOR-MERGED code, never a working tree."* That
was an **intention, not a check**. Both worktree-sync failures printed
`WARN: ... running last-synced code` and carried on.

Observed live, from `.leibniz/heartbeat-launch.log`:

| night | outcome |
|---|---|
| 2026-09-11 | healthy, rc=0 |
| 09-12 / 09-13 / 09-14 | `Could not resolve host: github.com`, then **ABORT — docker daemon unreachable**, rc=2 |
| 09-15 | git failed, **`WARN: worktree sync failed — running last-synced code`**, beat completed rc=0 |

On 09-15 the beat ran pinned to `9484d5e` — **four trust-boundary ADRs behind** `origin/main`,
missing ADR 0097 (the axiom check), 0098 (the kernel replay), 0099 and 0100 (the denotation check).
That is the build in which `kernel_verified=True` was *demonstrated* on FLT derived from `False`.
It promulgated one law, `bc7bec66`.

Nothing was published — publication is the operator's ADR 0033 act and the queue is held — so no
false result escaped. But a verdict was minted by a build with a known hole, and **nothing said so**.
The three docker aborts each raised an alarm; running stale code raised none.

## The shape of the defect

This is the failure mode that looks like success, again:

- A beat that **cannot run** aborts loudly (docker precondition, ADR 0093).
- A beat that runs the **wrong code** returned `rc=0` and journalled a normal-looking entry.

The second is worse, because it is indistinguishable from a healthy night in every artifact the
operator reads. Four consecutive nights of `git fetch` failure were invisible for the same reason:
the only record was a `WARN` in a log that no alarm watched.

## Decision

1. **A worktree that cannot be synced ABORTS** (rc=2) and raises an alarm, instead of running
   whatever was there.
2. **Verify, do not assume.** The launcher compares `git rev-parse origin/main` against the
   worktree's `HEAD` and aborts on mismatch. A sync command that silently no-ops, or a HEAD someone
   moved by hand, passes every command that used to run and only this catches it.
3. **A failed fetch raises an alarm** rather than only a `WARN`. It remains survivable — the
   worktree may already be at the newest merged commit — but it is no longer silent.
4. **Every beat is attributable to a commit.** The launcher logs `beat code: <sha> (…)` and exports
   `LEIBNIZ_BEAT_COMMIT`, so the journal can answer "which code produced this verdict" — the
   question the 09-15 beat could not.

## The bug the tests found, which predates this ADR

Writing the test surfaced something worse than the fail-open, and present in the **original**
launcher: if an ordinary directory sits at the worktree path, `git -C "$WT" …` walks **up** and
operates on the **canonical repo**. Measured:

```
canonical repo branch BEFORE: main
  (checkout in the squatter dir SUCCEEDED)
canonical repo branch AFTER : HEAD
```

The nightly daemon was one stray directory away from detaching the operator's own working checkout.
The first version of the ADR 0101 fix did not catch this either — its `HEAD` comparison *passed*,
because it too was reading the parent repo's HEAD. The launcher now confirms `$WT` is a worktree
whose root is exactly `$WT` **before any git command runs inside it**.

That is the argument for the tests executing the script rather than reading it: the guard and its
first fix were both wrong in the same invisible way, and only running them showed it.

## Evidence

`tests/test_beat_runs_merged_code_r0101.py` — four tests that RUN the launcher against a real
throwaway git repo:

- a worktree that cannot sync aborts, raises an alarm, and does **not** execute the stale beat
  (the fixture's `heartbeat.py` would print `STALE CODE RAN`);
- a squatting directory aborts and leaves the canonical checkout on `main`;
- a healthy worktree proceeds and records `beat code: <sha>`;
- a failed fetch alarms, and remains survivable.

## Consequences

- A night the beat cannot run correctly is now a night it does not run — and says so.
- **The operator must re-run `scripts/install_heartbeat.sh`**: launchd executes the installed copy
  at `~/.leibniz-heartbeat/launch.sh`, so merging this changes nothing until it is reinstalled.
- `bc7bec66` (promulgated 2026-09-15 by the stale build) should be re-discharged under the current
  guards before it is considered for publication.
- The standing pattern, once more: the check that was never run is the one that was wrong. ADR 0068
  stated this invariant in prose for 33 ADRs and nothing enforced it.

#!/bin/zsh
# ADR 0068 Phase α — the heartbeat bootstrap (the copy launchd runs lives at
# ~/.leibniz-heartbeat/launch.sh, installed by scripts/install_heartbeat.sh, so it never depends on
# which branch the primary checkout happens to be on).
#
# Each beat: fetch origin in the canonical repo → sync a dedicated worktree to origin/main (the
# daemon always runs the latest OPERATOR-MERGED code, never a working tree) → copy .env → run one
# capped, journaled beat against the canonical runtime DB + frontier band. All state lands in the
# primary repo's .leibniz/ (journal.jsonl, review_queue.md, alarms.log).
#
# ADR 0101 — that "always runs the latest OPERATOR-MERGED code" was an intention, not a check.
# Both sync failures used to print `WARN: ... running last-synced code` and CARRY ON, so a beat
# could mint against arbitrarily old code with nothing but a line in a log that no alarm watched.
# Observed live: on 2026-09-15 the beat ran pinned to 9484d5e — four trust-boundary ADRs behind
# origin/main, including the one that fixed a demonstrated `kernel_verified=True` on a false
# theorem — and promulgated a law. Nothing was published (publication is the operator's ADR 0033
# act), but the verdict came from a build with a known hole and nothing said so.
#
# The beat now VERIFIES the worktree is at origin/main and ABORTS if it is not, matching how the
# docker precondition already behaves. ADR 0093: a lane that cannot run must say so.
set -u
REPO="${LEIBNIZ_REPO:-/Users/dave/Claude_Primary/leibniz}"
WT="$REPO/.leibniz/heartbeat-wt"
LOG="$REPO/.leibniz/heartbeat-launch.log"
ALARMS="$REPO/.leibniz/alarms.log"
mkdir -p "$REPO/.leibniz"

# Same shape heartbeat.py's `alarm()` writes, so one log carries every reason a beat did not run.
alarm() { printf '%s  %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" >> "$ALARMS"; }
die()   { echo "ABORT: $1"; alarm "beat ABORTED at bootstrap: $1"; exit 2; }

{
  echo "=== beat launch $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  cd "$REPO" || { echo "repo missing: $REPO"; alarm "beat ABORTED at bootstrap: repo missing"; exit 2; }

  # A fetch failure is survivable -- the worktree may already be at the newest merged commit -- but
  # it is NOT silent. Four consecutive nights of `Could not resolve host` went unnoticed because
  # the only record was a WARN in a log nothing watched.
  fetched=1
  git fetch origin --quiet || { fetched=0; alarm "beat could not fetch origin — running the last commit it saw"; }

  if [ ! -d "$WT" ]; then
    git worktree add --detach "$WT" origin/main || die "worktree create failed"
  else
    # `$WT` must be a worktree whose ROOT is exactly `$WT`. If it is an ordinary directory -- a
    # leftover, a squatter, a half-removed worktree -- then `git -C "$WT" ...` walks UP and
    # operates on the CANONICAL repo instead. Measured: `git -C <plain-dir> checkout --detach
    # origin/main` succeeds and leaves the operator's primary checkout detached (main -> HEAD),
    # and the HEAD comparison below then passes because it is reading the parent repo's HEAD.
    # So this check must come BEFORE any git command runs inside `$WT`.
    top=$(git -C "$WT" rev-parse --show-toplevel 2>/dev/null) || die "beat worktree is not a git worktree"
    [ "$(cd "$top" 2>/dev/null && pwd -P)" = "$(cd "$WT" 2>/dev/null && pwd -P)" ] \
      || die "beat worktree path is not a worktree root (would act on the canonical repo)"
    git -C "$WT" checkout --detach --quiet origin/main 2>/dev/null \
      || git -C "$WT" reset --hard --quiet origin/main \
      || die "worktree sync failed"
  fi

  # Verify, do not assume. A sync command that silently no-ops, a detached HEAD left somewhere
  # else, or a worktree someone poked by hand all pass the commands above; only this catches them.
  want=$(git rev-parse origin/main 2>/dev/null) || die "cannot resolve origin/main"
  have=$(git -C "$WT" rev-parse HEAD 2>/dev/null) || die "cannot read the beat worktree HEAD"
  [ "$want" = "$have" ] || die "worktree is not at origin/main (want ${want:0:12}, have ${have:0:12})"

  # Every beat is now attributable to a commit. Without this line the journal could not say which
  # code produced a verdict, which is exactly the question the 2026-09-15 beat raised.
  if [ "$fetched" -eq 1 ]; then
    echo "beat code: ${have:0:12} (origin/main, freshly fetched)"
  else
    echo "beat code: ${have:0:12} (origin/main as last seen — fetch failed, may be behind)"
  fi

  [ -f "$WT/scripts/heartbeat.py" ] || { echo "heartbeat.py not on origin/main yet — skipping beat"; exit 0; }
  cp "$REPO/.env" "$WT/.env" 2>/dev/null || echo "WARN: no .env to copy"
  export LEIBNIZ_HEARTBEAT_HOME="$REPO/.leibniz"
  export LEIBNIZ_RUNTIME_DB="$REPO/.leibniz/memory.db"
  export LEIBNIZ_FRONTIER_STATE="$REPO/.leibniz/frontier.json"
  export LEIBNIZ_BEAT_COMMIT="$have"
  export LEIBNIZ_DAILY_USD_CAP="${LEIBNIZ_DAILY_USD_CAP:-5}"
  export LEIBNIZ_HEARTBEAT_CYCLES="${LEIBNIZ_HEARTBEAT_CYCLES:-2}"
  cd "$WT" && PYTHONPATH="$WT" python3 scripts/heartbeat.py
  rc=$?
  rm -f "$WT/.env"                       # never leave the credentials copy at rest between beats
  echo "=== beat done rc=$rc ==="
  exit $rc
} >> "$LOG" 2>&1

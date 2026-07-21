#!/bin/zsh
# ADR 0068 Phase α — the heartbeat bootstrap (the copy launchd runs lives at
# ~/.leibniz-heartbeat/launch.sh, installed by scripts/install_heartbeat.sh, so it never depends on
# which branch the primary checkout happens to be on).
#
# Each beat: fetch origin in the canonical repo → sync a dedicated worktree to origin/main (the
# daemon always runs the latest OPERATOR-MERGED code, never a working tree) → copy .env → run one
# capped, journaled beat against the canonical runtime DB + frontier band. All state lands in the
# primary repo's .leibniz/ (journal.jsonl, review_queue.md, alarms.log).
set -u
REPO="${LEIBNIZ_REPO:-/Users/dave/Claude_Primary/leibniz}"
WT="$REPO/.leibniz/heartbeat-wt"
LOG="$REPO/.leibniz/heartbeat-launch.log"
mkdir -p "$REPO/.leibniz"
{
  echo "=== beat launch $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  cd "$REPO" || { echo "repo missing: $REPO"; exit 2; }
  git fetch origin --quiet || echo "WARN: git fetch failed — running last-synced code"
  if [ ! -d "$WT" ]; then
    git worktree add --detach "$WT" origin/main || { echo "worktree create failed"; exit 2; }
  else
    git -C "$WT" checkout --detach --quiet origin/main 2>/dev/null \
      || git -C "$WT" reset --hard --quiet origin/main \
      || echo "WARN: worktree sync failed — running last-synced code"
  fi
  [ -f "$WT/scripts/heartbeat.py" ] || { echo "heartbeat.py not on origin/main yet — skipping beat"; exit 0; }
  cp "$REPO/.env" "$WT/.env" 2>/dev/null || echo "WARN: no .env to copy"
  export LEIBNIZ_HEARTBEAT_HOME="$REPO/.leibniz"
  export LEIBNIZ_RUNTIME_DB="$REPO/.leibniz/memory.db"
  export LEIBNIZ_FRONTIER_STATE="$REPO/.leibniz/frontier.json"
  export LEIBNIZ_DAILY_USD_CAP="${LEIBNIZ_DAILY_USD_CAP:-5}"
  export LEIBNIZ_HEARTBEAT_CYCLES="${LEIBNIZ_HEARTBEAT_CYCLES:-2}"
  cd "$WT" && PYTHONPATH="$WT" python3 scripts/heartbeat.py
  rc=$?
  rm -f "$WT/.env"                       # never leave the credentials copy at rest between beats
  echo "=== beat done rc=$rc ==="
  exit $rc
} >> "$LOG" 2>&1

#!/usr/bin/env bash
# ADR 0034 A/B organic runner.
#
#   A = Stage 0+1 (instrumentation + steering graft)  — run tonight, on this commit.
#   B = Stage 0+1+2 (+ empirical pattern-mining)       — run tomorrow, after Stage 2 merges.
#
# The two arms must differ ONLY in the code. This wrapper pins everything else so the
# comparison is clean (we have been burned by confounds before — a dead prover, a panel of 2,
# a feed that changed):
#   • FRESH, isolated ledger per arm  (genre-kill/exemplars build from a clean slate)
#   • the SAME pinned feed snapshot   (identical seeds on both days, not the regenerating "latest")
#   • the SAME prover/panel/repair config, sourced from one file (.leibniz-ab/ab_config.env)
#   • a per-arm report + the Stage-0 novelty metric, captured next to the ledger
#
# Run it in YOUR terminal under nohup+caffeinate (billable, long):
#   cp .leibniz-ab/ab_config.env.example .leibniz-ab/ab_config.env   # then fill the panel/gateway
#   nohup caffeinate -i ./scripts/run_organic_ab.sh A > /tmp/organic6A.log 2>&1 &
#   # tomorrow, after Stage 2 is on main:
#   nohup caffeinate -i ./scripts/run_organic_ab.sh B > /tmp/organic6B.log 2>&1 &
#
# Usage: run_organic_ab.sh <A|B> [cycles] [seeds_per_cycle] [cap_usd]   (defaults 8 3 40, = organic5)
set -euo pipefail

ARM="${1:?usage: run_organic_ab.sh <A|B|SA> [cycles seeds cap]}"
CYCLES="${2:-8}"; SEEDS="${3:-3}"; CAP="${4:-40}"
case "$ARM" in A|B|SA) ;; *) echo "arm must be A, B, or SA, got '$ARM'" >&2; exit 2 ;; esac

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ABDIR="$REPO/.leibniz-ab"
RUNDIR="$ABDIR/$ARM"
PINNED_FEED="$ABDIR/feed_pinned.json"
LIVE_FEED="/Users/dave/Agent_Data/Agents (Chimera, Newton, Leibniz)/arxiv_feed/feeds/latest/leibniz.json"
CONFIG="$ABDIR/ab_config.env"
mkdir -p "$RUNDIR"

# Resolve the Python interpreter once (some systems have only python3, others only python).
PY="$(command -v python3 || command -v python || true)"
[[ -n "$PY" ]] || { echo "no python3/python on PATH" >&2; exit 3; }
# Stream Python stdout live (unbuffered) so the tee'd run.log shows progress instead of flushing
# in chunks — arm A's log only filled at the end because CPython block-buffers when piped.
export PYTHONUNBUFFERED=1

# --- shared, code-independent config (IDENTICAL for A and B) --------------------------------
if [[ ! -f "$CONFIG" ]]; then
  echo "missing $CONFIG — copy .leibniz-ab/ab_config.env.example to it and fill the panel/gateway." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090  # operator-filled config path is intentionally non-constant
source "$CONFIG"
set +a

# --- pin the feed once: arm A snapshots the live feed; arm B reuses the SAME snapshot --------
if [[ ! -f "$PINNED_FEED" ]]; then
  cp "$LIVE_FEED" "$PINNED_FEED"
  echo "[ab] pinned the live feed -> $PINNED_FEED"
fi
export LEIBNIZ_FEED_PATH="$PINNED_FEED"
_FEED_DATE="$("$PY" -c "import json,sys; print(json.load(open(sys.argv[1])).get('run_date'))" "$PINNED_FEED")"

# --- the experimental variable, set EXPLICITLY per arm (no stray-env confound) ----------------
#   A  = Stage 0+1 baseline           (mining off, symbolic-exp off)
#   B  = Stage 0+1+2                   (mining on,  symbolic-exp off)  — ADR 0034 A/B
#   SA = ADR 0035 Stage A experiment  (mining off, symbolic-exp ON)   — base^n % m invited
# AB_MINE_K overrides B's mined seeds-per-cycle (default 2).
export LEIBNIZ_PATTERN_MINE=0
export LEIBNIZ_DSL_SYMBOLIC_EXP=0
if [[ "$ARM" == "B" ]]; then
  export LEIBNIZ_PATTERN_MINE="${AB_MINE_K:-2}"
elif [[ "$ARM" == "SA" ]]; then
  export LEIBNIZ_DSL_SYMBOLIC_EXP=1
fi

# --- fresh, isolated ledger for this arm (clean slate) --------------------------------------
export LEIBNIZ_INSTANCE="dev"
export LEIBNIZ_RUNTIME_DB="$RUNDIR/memory.db"
export LEIBNIZ_NOTEBOOK_PATH="$RUNDIR/notebook.json"
export LEIBNIZ_FRONTIER_PATH="$RUNDIR/frontier.json"
rm -f "$LEIBNIZ_RUNTIME_DB" "$LEIBNIZ_NOTEBOOK_PATH" "$LEIBNIZ_FRONTIER_PATH"

echo "[ab] arm=$ARM  commit=$(git -C "$REPO" rev-parse --short HEAD)  feed run_date=$_FEED_DATE"
echo "[ab] ledger=$RUNDIR  prover=${LEIBNIZ_PROVER_MODELS:-<unset>}  consensus=${LEIBNIZ_PROOF_CONSENSUS:-2}"
echo "[ab] repair=${LEIBNIZ_PROOF_REPAIR:-<off>}  panel=${LEIBNIZ_REPAIR_PANEL:-<none>}  pattern_mine=$LEIBNIZ_PATTERN_MINE  symbolic_exp=$LEIBNIZ_DSL_SYMBOLIC_EXP"

# --- run ------------------------------------------------------------------------------------
cd "$REPO"
"$PY" scripts/calibrate_discovery.py "$CYCLES" "$SEEDS" "$CAP" 2>&1 | tee "$RUNDIR/run.log"

# --- capture per-arm outputs (the global report is overwritten each run) --------------------
cp -f "$REPO/calibration_report.json" "$RUNDIR/calibration_report.json"
echo "[ab] === Stage-0 novelty metric for arm $ARM ==="
"$PY" scripts/novelty_report.py --db "$LEIBNIZ_RUNTIME_DB" | tee "$RUNDIR/novelty_report.txt"
echo "[ab] arm $ARM complete. Artifacts in $RUNDIR/"

#!/usr/bin/env bash
# Leibniz instance launcher (ADR 0033 Slice 4).
#
# Sources a deploy profile, runs the ADR 0033 isolation guard (the EARLY check that this
# instance's state is separate from PROD — the runtime write-barrier is the backstop), then
# execs the command for that instance.
#
# Usage:
#   scripts/run_instance.sh <prod|uat|dev> [-- <command...>]
#
# With no command, runs the calibrate discovery harness (8 cycles x 3 seeds) at the profile's
# USD cap. Examples:
#   scripts/run_instance.sh uat
#   scripts/run_instance.sh prod -- python3 -u scripts/calibrate_discovery.py 8 3 20
set -euo pipefail
cd "$(dirname "$0")/.."

inst="${1:-}"
if [[ -z "$inst" ]]; then
  echo "usage: $0 <prod|uat|dev> [-- cmd...]" >&2
  exit 2
fi
shift || true
[[ "${1:-}" == "--" ]] && shift || true

profile="deploy/profiles/${inst}.env"
if [[ ! -f "$profile" ]]; then
  echo "missing $profile — copy deploy/profiles/${inst}.env.example to it and adjust" >&2
  exit 2
fi

# Export every KEY=value in the profile into the environment.
set -a
# shellcheck disable=SC1090
source "$profile"
set +a

# Early isolation guard (ADR 0033). The runtime write-barrier still fails closed regardless,
# but this gives a clear message before any billable work runs.
if ! python3 -m leibniz.deploy; then
  echo "refusing to launch ${inst}: fix the profile problems above" >&2
  exit 1
fi

cmd=("$@")
if [[ ${#cmd[@]} -eq 0 ]]; then
  cmd=(python3 -u scripts/calibrate_discovery.py 8 3 "${LEIBNIZ_DAILY_USD_CAP:-20}")
fi

echo "[run_instance] LEIBNIZ_INSTANCE=${LEIBNIZ_INSTANCE} -> ${cmd[*]}"
exec "${cmd[@]}"

#!/usr/bin/env bash
# Kernel-soak baseline + skip-count guard (validation plan Tier 2, GATE-5 broad arm).
#
# Runs the FULL test suite WITH the Lean kernel present (docker), so the docker-gated render->kernel tests
# actually execute, and reports pass/fail/skip + the slowest files. Unlike scripts/run_kernel_tests.sh
# (the STRICT lane: a curated set that must run with ZERO skips), this soak runs everything and GUARDS THE
# SKIP COUNT: with the image present only a small, known number of tests should skip (e.g. a live-API test).
# If the skip count jumps, a gate has silently turned into a no-op (the failure mode GATE-5 exists to catch).
#
# RUNS WHERE: operator machine with docker + leibniz-lean:v4.31.0 (or the self-hosted `lean` runner). On a
# GitHub-hosted runner (no image) it refuses (exit 2) rather than reporting a false baseline.
#
# Usage: scripts/run_kernel_soak.sh [--max-skips N]   (default N=3; calibrate to your environment's baseline)
set -euo pipefail
cd "$(dirname "$0")/.."

MAX_SKIPS=3
while [ $# -gt 0 ]; do
  case "$1" in
    --max-skips) MAX_SKIPS="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
done

# 1. the kernel must be available; the soak's whole point is to exercise it with everything else.
if ! python3 -c "import sys; sys.path.insert(0,'.'); from leibniz.backends.lean_cli import available; sys.exit(0 if available() else 1)"; then
  echo "FAIL: this soak requires docker + the leibniz-lean image (operator-local; not on GitHub-hosted runners)." >&2
  exit 2
fi

# 2. run the full suite; -rs surfaces skip reasons, --durations shows the slowest files.
echo "kernel soak: running the full suite with the Lean kernel present (this includes ~30 docker-gated tests)..."
set +e
out="$(python3 -m pytest tests/ -rs -p no:cacheprovider --durations=25 -q 2>&1)"
code=$?
set -e
echo "$out"

# 3. parse counts + guard the skip count (a jump = a silently no-opping gate).
python3 - "$MAX_SKIPS" <<PY
import re, sys
out = """$out"""
maxskips = int(sys.argv[1])
def n(word):
    m = re.search(r"(\d+) " + word, out)
    return int(m.group(1)) if m else 0
passed, failed, skipped, errors = n("passed"), n("failed"), n("skipped"), n("error")
print(f"\nkernel soak summary: {passed} passed, {failed} failed, {skipped} skipped, {errors} errors")
problems = []
if failed or errors:
    problems.append(f"{failed} failed / {errors} errors")
if skipped > maxskips:
    problems.append(f"{skipped} skipped > --max-skips {maxskips} (a kernel/z3 gate may be silently no-opping; "
                    f"check the 'SKIPPED' reasons above)")
if problems:
    print("SKIP-GUARD / SOAK FAIL: " + "; ".join(problems), file=sys.stderr)
    sys.exit(1)
print(f"SOAK OK — kernel exercised across the full suite; skips ({skipped}) within budget ({maxskips}).")
PY

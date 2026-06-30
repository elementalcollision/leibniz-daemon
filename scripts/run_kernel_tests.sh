#!/usr/bin/env bash
# Kernel-CI lane (testing-gap remediation): run the docker-gated render->kernel tests that the main `ci`
# lane (GitHub-hosted, no Lean image) cannot run. This lane exists precisely to RUN the kernel, so an
# absent image or a silently-skipped kernel test is a FAILURE here — mirroring ci.yml's "0-collected must
# not masquerade as a pass" discipline. Use pre-merge, via local cron, or from the self-hosted nightly.
set -euo pipefail
cd "$(dirname "$0")/.."

# 1. the kernel must be available; this lane's whole point is to exercise it.
if ! python3 -c "import sys; sys.path.insert(0,'.'); from leibniz.backends.lean_cli import available; sys.exit(0 if available() else 1)"; then
  echo "FAIL: this lane requires docker + the leibniz-lean image (operator-local; not on GitHub-hosted runners)." >&2
  exit 2
fi

# 2. run the kernel-exercising tests; -rs surfaces skip reasons so a silent skip is visible.
out="$(python3 -m pytest tests/test_kernel_smoke.py tests/test_covering_decider.py -q -rs -p no:cacheprovider 2>&1)"
echo "$out"

# 3. a SKIP here means a kernel test did not actually run — treat as failure (no silent pass).
if echo "$out" | grep -qiE "[0-9]+ skipped|SKIPPED"; then
  echo "FAIL: a kernel test skipped; this lane must RUN the kernel, not skip it." >&2
  exit 1
fi
echo "kernel lane OK — render->kernel paths exercised on the real Lean kernel."

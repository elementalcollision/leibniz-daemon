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
#    These files are skip-FREE when the image is present (every test runs), so the zero-skip rule (step 3)
#    holds. test_native_eval_redteam is the ADR 0097 gate — the published Lean native-evaluation
#    exploit driven through the sole kernel writer. test_kernel_false_theorem_rejection is GATE-4: the audit-tier "nothing false is KERNEL-VERIFIED"
#    backstop. (For BROAD coverage with a calibrated skip budget, use scripts/run_kernel_soak.sh instead.)
#    test_novelty_corpus_r3 is here per ADR 0095 Decision 3: it is the ONLY test that recomputes a
#    corpus hash against the live kernel, so it is the only thing that catches a corpus gone stale
#    after a toolchain bump -- and it used to run in neither enforced lane (marker-skipped on the
#    GitHub-hosted `ci`, absent from this list), which is the ADR 0093 shape one layer in.
out="$(python3 -m pytest tests/test_kernel_smoke.py tests/test_covering_decider.py \
       tests/test_kernel_false_theorem_rejection.py tests/test_novelty_corpus_r3.py \
       tests/test_native_eval_redteam.py \
       -q -rs -p no:cacheprovider 2>&1)"
echo "$out"

# 3. a SKIP here means a kernel test did not actually run — treat as failure (no silent pass).
if echo "$out" | grep -qiE "[0-9]+ skipped|SKIPPED"; then
  echo "FAIL: a kernel test skipped; this lane must RUN the kernel, not skip it." >&2
  exit 1
fi
echo "kernel lane OK — render->kernel paths exercised on the real Lean kernel."

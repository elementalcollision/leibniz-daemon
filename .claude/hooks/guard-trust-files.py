#!/usr/bin/env python3
"""PreToolUse guard for Leibniz trust-boundary files.

Enforcement layer 4 (HANDOFF.md §4): a memory file is context, not enforcement;
this hook is the one true *block*. It intercepts Edit/Write/MultiEdit on the
files that define or tier the trust boundary and returns an "ask" decision so the
operator must consciously approve any change to them.

Guarded files (every file that produces or tiers an EdgeEvidence on a trust edge,
plus the executable invariants):
  leibniz/trust.py                 -- TrustPolicy.validate_path (runtime guard)
  leibniz/verifiers.py             -- LeanVerifier.discharge (sole kernel_verified writer)
  leibniz/types.py                 -- TrustTier / Role / EdgeEvidence
  leibniz/propositio.py            -- Demonstratio.seal / kernel_verified (invariant 7)
  leibniz/gates/verification.py    -- VerificationGate.is_promotable
  leibniz/gates/faithfulness.py    -- the gaming-witness / DEFER routing
  leibniz/gates/novelty.py         -- novelty == MECHANICAL only
  tests/test_invariants.py         -- the 11 invariant tests (never edit to pass)

Input: a PreToolUse JSON event on stdin.
Output: a PreToolUse JSON decision on stdout ("ask" when a guarded file is the
target; silent allow otherwise).
"""
from __future__ import annotations

import json
import sys

PROTECTED_SUFFIXES = (
    "leibniz/trust.py",
    "leibniz/verifiers.py",
    "leibniz/types.py",
    "leibniz/propositio.py",          # Demonstratio.seal / kernel_verified (invariant 7)
    "leibniz/gates/verification.py",
    "leibniz/gates/faithfulness.py",
    "leibniz/gates/novelty.py",
    "tests/test_invariants.py",
)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        # Never fail open loudly; if we cannot parse, allow (other layers cover us).
        return 0

    tool = event.get("tool_name", "")
    if tool not in ("Edit", "Write", "MultiEdit"):
        return 0

    path = (event.get("tool_input", {}) or {}).get("file_path", "") or ""
    norm = path.replace("\\", "/")
    hit = next((s for s in PROTECTED_SUFFIXES if norm.endswith(s)), None)
    if hit is None:
        return 0

    decision = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                f"TRUST-BOUNDARY FILE ({hit}). Editing this file can weaken the "
                f"Leibniz trust boundary (CLAUDE.md invariants 1-7). If the change "
                f"would require editing tests/test_invariants.py to pass, STOP. "
                f"Operator sign-off required."
            ),
        }
    }
    print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())

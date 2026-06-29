"""Regression for the end-to-end demo (scripts/demo_stack.py): the pure (no-docker) stages must keep
working, so the showcase of the ADR 0041 stack stays green even where the Lean kernel / sandbox are
unavailable. Docker-gated behaviors are covered by test_cwc_check / test_tool_sandbox / test_seed_trust.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("demo_stack", _ROOT / "scripts" / "demo_stack.py")
demo = importlib.util.module_from_spec(_spec)
sys.modules["demo_stack"] = demo
_spec.loader.exec_module(demo)


def test_stage_a_verify_only_accepts_valid_rejects_false():
    rows = demo.stage_a_verification(use_kernel=False, full=False)
    fano = next(r for r in rows if "Fano" in r["label"])
    false = next(r for r in rows if "false" in r["label"])
    assert fano["verify_ok"] is True and "equals record" in fano["novelty"]
    assert false["verify_ok"] is False


def test_stage_b_registry_is_state1_dormant():
    b = demo.stage_b_tool_seam(use_sandbox=False)
    assert b["dormant_recheckers"] and b["dormant_templates"]   # no decider admitted


def test_stage_c_seeds_validate_and_guard():
    c = demo.stage_c_seeds()
    assert c["rosin_status"] == "validated" and c["rosin_floor_unchanged"]   # no behavior change
    assert c["fabricated_status"] == "quarantined" and c["fabricated_floor_held"]  # floor-raising guard
    assert c["target_kind"] == "target" and c["target_status"] == "validated"

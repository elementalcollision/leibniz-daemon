"""Guard the LLM FunSearch pilot (the billable proposer wired to the sandbox).

No-spend tests (fake proposer + monkeypatched sandbox). The load-bearing soundness property: an
oracle-flagged "beat" is a beat ONLY if the Lean kernel confirms it; the pilot never promulgates and
never sets kernel_verified. Program extraction + budget caps are pinned too.
"""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


pilot = _load("funsearch_llm_pilot", "scripts/funsearch_llm_pilot.py")


def _snap():
    from cwc_table_oracle import load_snapshot
    return load_snapshot()[0]


def test_extract_program_fenced_and_raw():
    assert "construct" in pilot.extract_program("```python\ndef construct(n,d,w):\n  return []\n```")
    assert pilot.extract_program("def construct(n,d,w):\n  return []").startswith("def construct")


def test_parse_completion_handles_null_content_reasoning_and_errors():
    import pytest
    # normal content
    assert "code" in pilot._parse_completion(
        {"choices": [{"message": {"content": "code"}}]})
    # null content but reasoning present (reasoning models) -> fall back
    assert "fromreason" in pilot._parse_completion(
        {"choices": [{"message": {"content": None, "reasoning": "fromreason"}}]})
    # the exact failure that voided run 1: null content, no reasoning -> descriptive raise (not a None)
    with pytest.raises(RuntimeError, match="empty content"):
        pilot._parse_completion({"choices": [{"message": {"content": None}, "finish_reason": "length"}]})
    # API error object -> raise
    with pytest.raises(RuntimeError, match="API error"):
        pilot._parse_completion({"error": {"message": "bad model"}})
    # no choices -> raise (never index into nothing)
    with pytest.raises(RuntimeError, match="no choices"):
        pilot._parse_completion({"choices": []})


def test_extract_program_tolerates_none():
    assert pilot.extract_program(None) == ""        # never crashes on null content


def test_extract_program_prefers_block_defining_construct():
    reply = ("Here's a sketch:\n```python\nx = 1\n```\nand the final program:\n"
             "```python\ndef construct(n, d, w):\n    return []\n```\n")
    assert pilot.extract_program(reply).startswith("def construct")   # picks the construct block


def test_fake_proposer_cycles_and_counts():
    p = pilot.FakeProposer()
    a = p.propose(11, 8, 5, 2, [])
    b = p.propose(11, 8, 5, 2, [])
    assert "def construct" in a and "def construct" in b and a != b   # cycles two distinct programs
    assert p.calls == 2


def test_targets_are_preregistered_and_well_formed():
    targets = pilot.load_targets()
    assert len(targets) == 12
    assert all({"n", "d", "w", "floor_to_beat"} <= set(t) for t in targets)


def test_run_cell_no_beat_when_below_floor(monkeypatch):
    snap = _snap()
    monkeypatch.setattr(pilot.sandbox, "evaluate_program",
                        lambda src, n, d, w, sn: {"sandbox_ok": True, "valid": True, "fitness": 1, "size": 1})
    r = pilot.run_cell(pilot.FakeProposer(), 18, 10, 6, snap, per_cell=3, budget_left=3,
                       wall_deadline=time.time() + 30)
    assert r["beat"] is None and r["best_size"] == 1 and r["programs"] == 3


def test_beat_requires_kernel_confirmation(monkeypatch):
    snap = _snap()
    # evaluator claims a valid code above the floor on every program
    monkeypatch.setattr(pilot.sandbox, "evaluate_program",
                        lambda src, n, d, w, sn: {"sandbox_ok": True, "valid": True, "fitness": 99, "size": 99})
    # witness must itself exceed the floor (4) for the size-gate; content irrelevant (kernel mocked)
    monkeypatch.setattr(pilot, "_rerun_for_witness", lambda src, n, d, w: [[0, 1, 2, 3, 4, 5]] * 5)
    # (1) kernel REFUSES -> NOT a beat (oracle/evaluator flag alone is never sufficient)
    monkeypatch.setattr(pilot, "_kernel_confirms", lambda witness, n, d, w: False)
    r = pilot.run_cell(pilot.FakeProposer(), 18, 10, 6, snap, per_cell=2, budget_left=2,
                       wall_deadline=time.time() + 30)
    assert r["beat"] is None
    # (2) kernel CONFIRMS -> beat recorded, with witness, and NEVER promulgated
    monkeypatch.setattr(pilot, "_kernel_confirms", lambda witness, n, d, w: True)
    r2 = pilot.run_cell(pilot.FakeProposer(), 18, 10, 6, snap, per_cell=2, budget_left=2,
                        wall_deadline=time.time() + 30)
    assert r2["beat"] is not None and r2["beat"]["witness"] is not None
    assert "kernel_verified" not in r2 and "promulgated" not in r2 and "qed" not in r2


def test_nondeterministic_rerun_to_floor_size_is_not_a_beat(monkeypatch):
    # eval claims size>floor, but the witness re-run returns only a floor-sized code: even if the
    # kernel validates that (true) theorem, it does NOT beat the record -> must NOT be flagged a beat.
    snap = _snap()
    floor = pilot.effective_best_known(18, 10, 6, snap)       # 4
    monkeypatch.setattr(pilot.sandbox, "evaluate_program",
                        lambda src, n, d, w, sn: {"sandbox_ok": True, "valid": True, "fitness": floor + 1, "size": floor + 1})
    monkeypatch.setattr(pilot, "_rerun_for_witness",
                        lambda src, n, d, w: [[0]] * floor)     # only floor codewords on re-run
    monkeypatch.setattr(pilot, "_kernel_confirms", lambda witness, n, d, w: True)
    r = pilot.run_cell(pilot.FakeProposer(), 18, 10, 6, snap, per_cell=2, budget_left=2,
                       wall_deadline=time.time() + 30)
    assert r["beat"] is None                                   # floor-sized witness is not a record


def test_run_cell_respects_budget(monkeypatch):
    snap = _snap()
    monkeypatch.setattr(pilot.sandbox, "evaluate_program",
                        lambda src, n, d, w, sn: {"sandbox_ok": True, "valid": False, "fitness": 0, "size": 0, "verify_reason": "x"})
    r = pilot.run_cell(pilot.FakeProposer(), 18, 10, 6, snap, per_cell=20, budget_left=3,
                       wall_deadline=time.time() + 30)
    assert r["programs"] <= 3                              # global budget cap honored


def test_proposer_failure_is_not_a_crash(monkeypatch):
    snap = _snap()

    class _Boom:
        def propose(self, *a):
            raise RuntimeError("api down")

    r = pilot.run_cell(_Boom(), 18, 10, 6, snap, per_cell=2, budget_left=2,
                       wall_deadline=time.time() + 30)
    assert "error" in r and r["beat"] is None

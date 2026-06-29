"""Light guard for the exact CP-SAT covering producer (ADR 0042/0043 Track-D escalation).

ortools is an operator-local dependency (not in CI), so this skips cleanly when it is absent. When
present, it pins the definitive behaviour: CP-SAT proves a tiny record optimal, and any reported beat is
a genuinely valid covering. Measurement asset — never promulgates.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("ortools", reason="ortools is operator-local; CP-SAT producer test skipped in CI")

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ep = _load("covering_exact_producer", "scripts/covering_exact_producer.py")


def test_proves_tiny_record_optimal():
    r = ep.attack(9, 3, 2, time_cap=20)              # C(9,3,2)=12 is optimal (STS(9))
    assert r["found"] == 12 and r["proven_optimal"] is True
    assert r["verdict"].startswith("OPTIMAL-CONFIRMED")


def test_a_reported_beat_would_be_valid():
    # we don't expect a beat on this optimal cell; assert the producer never claims an invalid beat
    r = ep.attack(10, 4, 2, time_cap=20)
    assert r["verdict"] != "BUG(false-beat)"
    assert r["found"] >= 9 or r["verdict"] == "BEATS"

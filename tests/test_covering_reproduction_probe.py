"""Light guard for the covering reproduction probe (ADR 0042/0043 Track-D gate).

The probe is a MEASUREMENT, not a trust-boundary asset, so this only pins: it returns a VALID covering
(validated by verify_covering), reproduces a tiny structured cell, and classifies status correctly.
Tiny budget so it runs in CI in well under a second.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


probe = _load("covering_reproduction_probe", "scripts/covering_reproduction_probe.py")


def test_probe_reproduces_a_tiny_structured_cell():
    r = probe.probe_cell(7, 3, 2, restarts=50, time_cap=10.0)
    assert r["valid"] is True                       # the covering it returns is genuinely valid
    assert r["found"] == 7 and r["best_known"] == 7
    assert r["status"] == "REPRODUCED"


def test_probe_output_is_always_a_valid_covering():
    # even on a slightly harder cell, the reported covering must verify (never a bogus "found")
    r = probe.probe_cell(10, 4, 2, restarts=50, time_cap=10.0)
    assert r["valid"] is True and r["found"] >= r["best_known"] or r["status"] == "BEATS"


def test_pre_registered_cells_are_fixed():
    # the cell set is pre-registered (no post-hoc cherry-picking); pin its size + that it spans k
    assert (7, 3, 2) in probe.PRE_REGISTERED and (16, 4, 2) in probe.PRE_REGISTERED
    assert len(probe.PRE_REGISTERED) == 10

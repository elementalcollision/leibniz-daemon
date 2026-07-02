"""Guard F2a weak duality (scripts/terwilliger_f2a.py, task #101). The Lean checks need the Mathlib REPL
image (operator-local docker; CI skips). Trust points: both theorems must elaborate with zero errors AND
the two corrupted controls (α-sign flip; Gram scale weakened to s ≥ 0) must FAIL — signs and strict
positivity are load-bearing, exactly as weak_duality_holds/corruption_detected_wd validate numerically."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _repl_ok() -> bool:
    try:
        r = subprocess.run(["docker", "image", "inspect", "leibniz-lean-repl:v4.31.0"],
                           capture_output=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


_needs = pytest.mark.skipif(not _repl_ok(), reason="leibniz-lean-repl image unavailable")


def _load():
    spec = importlib.util.spec_from_file_location("terwilliger_f2a", _ROOT / "scripts" / "terwilliger_f2a.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


f2a = _load()


def test_controls_are_real_mutations():
    ctl = f2a.controls(f2a.LEAN_SRC)
    assert set(ctl) == {"alpha_sign_flip", "gram_scale_weakened"}
    for src in ctl.values():
        assert src != f2a.LEAN_SRC


def test_source_states_the_right_bound_and_uses_no_sorry():
    assert "sorry" not in f2a.LEAN_SRC
    assert "(∑ t, γ t) - ν" in f2a.LEAN_SRC                  # bound = Σγ − ν, the scope-doc statement
    assert "PosSemidef" in f2a.LEAN_SRC and "diagonal" in f2a.LEAN_SRC


@_needs
def test_theorems_verify_and_controls_fail():
    assert f2a.main() == 0                                   # GREEN = theorems ok AND both controls fail

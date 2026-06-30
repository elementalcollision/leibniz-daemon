"""Guards for the construction-intake soundness primitives (ADR 0045 §2.1/§2.3 scaffolding).

Pins the corrected-design CRITICAL fixes: the locked prelude is byte-identical to the verifiers (no
drift); a construction theorem_src must be one clean `theorem … := by decide` over literals (no defs/
axioms/native_decide — the self-contained renderer blob is REJECTED, forcing prelude-separate); and the
canonical claim derives (params, size, statement) from the witness via the operator template, size never
tool-supplied. Pure functions; CI-safe.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ci = _load("construction_intake", "scripts/construction_intake.py")
cv = _load("covering_verify_ci", "scripts/covering_verify.py")
pb = _load("probe_ci", "scripts/probe_beta_cwc_pilot.py")

_CLEAN = "theorem cov_9_3_2_le_12 : validCovering [[0,1,2],[3,4,5]] 9 3 2 2 = true := by decide"


def test_locked_preludes_match_the_verifiers_no_drift():
    assert ci.LOCKED_COVERING_PRELUDE == cv._LEAN_HELPERS
    assert ci.LOCKED_CWC_PRELUDE == pb._LEAN_HELPERS


def test_guard_accepts_a_clean_theorem():
    ok, reason = ci.theorem_structural_guard(_CLEAN)
    assert ok, reason


def test_guard_rejects_the_self_contained_renderer_blob():
    # render_covering_lean emits helpers (def …) + theorem in ONE string -> must be REJECTED (CRITICAL #1)
    blob = cv.render_covering_lean(9, 3, 2, [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7],
                                           [2, 5, 8], [0, 4, 8], [1, 5, 6], [2, 3, 7], [0, 5, 7],
                                           [1, 3, 8], [2, 4, 6]])
    ok, reason = ci.theorem_structural_guard(blob)
    assert not ok and "forbidden" in reason


@pytest.mark.parametrize("bad", [
    "def x := 1\ntheorem t : p = true := by decide",      # smuggled def
    "axiom h : p\ntheorem t : p = true := by decide",      # smuggled axiom
    "theorem t : p = true := by native_decide",            # native_decide routes to host
    "theorem a : p := by decide\ntheorem b : q := by decide",  # two theorems
    "theorem t : p = true := by simp := rfl",              # two :=
])
def test_guard_rejects_unsafe_or_malformed(bad):
    assert ci.theorem_structural_guard(bad)[0] is False


def test_canonical_claim_binds_to_the_witness():
    cov = ci.canonical_claim({"domain": "covering", "v": 9, "k": 3, "t": 2,
                              "blocks": [[0, 1, 2]] * 12})
    assert cov["statement"] == "C(9,3,2) <= 12" and cov["size"] == 12 and cov["params"] == (9, 3, 2)
    cwc = ci.canonical_claim({"domain": "cwc", "n": 7, "d": 4, "w": 3, "code": [[0, 1, 2]] * 7})
    assert cwc["statement"] == "A(7,4,3) >= 7" and cwc["size"] == 7
    with pytest.raises(ValueError):
        ci.canonical_claim({"domain": "graph"})

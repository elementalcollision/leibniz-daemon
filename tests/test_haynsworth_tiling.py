"""Guard the Haynsworth / block-LDLᵀ tiling soundness lemma (docs/crt/haynsworth_tiling_soundness.lean) — the
once-proved 'Half 1' for the deferred large-block-PSD Schur-tiling path. Artifact well-formedness is CI-safe;
the axiom-clean kernel check is REPL-gated. Pure Mathlib theorem — no trust surface (tests/test_invariants.py
untouched)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_ART = _ROOT / "docs" / "crt" / "haynsworth_tiling_soundness.lean"
_THEOREMS = ("psd_of_congruence", "psd_of_sum_congruence")


def test_artifact_wellformed_and_no_cheating():
    src = _ART.read_text(encoding="utf-8")
    for name in _THEOREMS:
        assert f"theorem {name}" in src
    # the load-bearing Mathlib lemma the soundness rests on, and the block-LDLᵀ sum structure
    assert "conjTranspose_mul_mul_same" in src
    assert "PosSemidef" in src
    for banned in ("sorry", "native_decide", "admit"):
        assert banned not in src


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_verifies_clean_axioms():
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    src = _ART.read_text(encoding="utf-8")
    run_src = "".join(ln for ln in src.splitlines(keepends=True) if not ln.startswith("import "))
    bk = LeanReplBackend(timeout_s=300)
    try:
        r = bk._run(run_src, ("Mathlib.LinearAlgebra.Matrix.PosDef",))
    finally:
        bk.close()
    msgs = (r or {}).get("messages", []) or []
    assert not [x for x in msgs if x.get("severity") == "error"]
    axiom_lines = [x.get("data", "") for x in msgs if "axiom" in (x.get("data") or "")]
    assert len(axiom_lines) == len(_THEOREMS)
    std = {"propext", "Classical.choice", "Quot.sound"}
    for ln in axiom_lines:
        toks = [t.strip() for t in ln.split("[", 1)[-1].rstrip("]").split(",") if t.strip()]
        assert all(t in std for t in toks), ln

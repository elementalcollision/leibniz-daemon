"""Guard the F2b engine lemma (scripts/f2b_engine_lemma_lean.py) — the block-diagonal PSD-iff, F2b-M2.
CI-safe checks are structural (the Lean source is well-formed, names the escape-hatch lemmas, has no stray
sorry); the real-kernel discharge (0 sorries, clean axioms, DISCHARGED) is a REPL-gated test. No trust surface
touched."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("f2b_engine_lemma_lean",
                                                  _ROOT / "scripts" / "f2b_engine_lemma_lean.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_source_states_the_block_diagonal_iff():
    m = _load()
    # The theorem is exactly the block-diagonal PSD-iff over ℝ.
    assert "block_diag_posSemidef_iff" in m.THEOREM_SRC
    assert "Matrix.fromBlocks A 0 0 D).PosSemidef ↔ A.PosSemidef ∧ D.PosSemidef" in m.THEOREM_SRC


def test_proof_rests_on_the_finsupp_escape_hatch_lemmas():
    # The whole point: bypass Mathlib's Finsupp-based PosSemidef via the plain-function characterization
    # and split the fromBlocks quadratic form. These names must appear in the proof.
    m = _load()
    for name in ["of_dotProduct_mulVec_nonneg", "dotProduct_mulVec_nonneg",
                 "fromBlocks_mulVec", "isHermitian_fromBlocks_iff"]:
        assert name in m.PROOF_SRC, f"proof should use {name}"


def test_proof_has_no_stray_sorry_or_admit():
    m = _load()
    src = m.full_source()
    for banned in ["sorry", "admit", "native_decide", "axiom "]:
        assert banned not in src, f"engine-lemma source must not contain {banned!r}"


def test_full_source_prints_axioms():
    m = _load()
    src = m.full_source()
    assert "#print axioms block_diag_posSemidef_iff" in src


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_discharges_clean():
    # The actual result: the engine lemma elaborates with 0 sorries and only the three standard axioms,
    # classifying DISCHARGED under the F2b validator.
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    fv_spec = importlib.util.spec_from_file_location("f2b_validate", _ROOT / "scripts" / "f2b_validate.py")
    fv = importlib.util.module_from_spec(fv_spec)
    fv_spec.loader.exec_module(fv)
    bk = LeanReplBackend(timeout_s=400)
    try:
        v = fv.classify(bk, m.THEOREM_SRC, m.PROOF_SRC, imports=m.IMPORTS)
    finally:
        bk.close()
    assert v["verdict"] == "DISCHARGED", v
    assert v["has_sorry"] is False
    assert set(v["axioms"]) == {"propext", "Classical.choice", "Quot.sound"}

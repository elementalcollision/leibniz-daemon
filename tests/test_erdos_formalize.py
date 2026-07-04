"""Guard the Erdős statement-formalization lane (scripts/erdos_formalize.py). CI-safe checks are structural
(the registry + artifacts are well-formed, cite their source, carry a faithfulness anchor, no stray sorry);
the faithfulness gate against the real kernel is a REPL-gated test. Presentation lane; no trust surface."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("erdos_formalize", _ROOT / "scripts" / "erdos_formalize.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_registry_covers_367_and_477_with_citations():
    m = _load()
    ids = {p["id"] for p in m.REGISTRY}
    assert {"367", "477"} <= ids
    for p in m.REGISTRY:
        assert p["apa"] and p["url"].startswith("https://www.erdosproblems.com/")
        assert p["anchor"] and p["non_vacuity"]                # every statement records its faithfulness basis


def test_artifacts_exist_state_the_conjecture_and_are_sorry_free():
    m = _load()
    for p in m.REGISTRY:
        src = (_ROOT / p["artifact"]).read_text(encoding="utf-8")
        assert f"def {p['conjecture']}" in src and ": Prop" in src
        # the STATEMENT carries no proof obligation discharged by cheating: no `:= sorry` / `by sorry` / admit
        # anywhere (native_decide is allowed only as a faithfulness anchor on a definition).
        assert ":= sorry" not in src and "by sorry" not in src and " admit" not in src


def test_477_states_unique_representation_and_thirteenth_powers():
    src = (_ROOT / "docs" / "erdos" / "erdos_477.lean").read_text(encoding="utf-8")
    assert "IsTilingComplement" in src and "∃! p" in src           # the ∃! is the content
    assert "m ^ 13" in src and "tiling_sanity" in src              # thirteenth powers + the sanity anchor


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_faithfulness_gate_passes_against_the_kernel():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    bk = LeanReplBackend(timeout_s=400)
    try:
        for p in m.REGISTRY:
            g = m.formalize(p, bk)
            assert g["elaborates"] and g["conjecture_is_prop"] and g["n_anchors"] >= 1, (p["id"], g)
            assert g["faithful"], (p["id"], g)
    finally:
        bk.close()

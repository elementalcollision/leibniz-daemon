"""Guard the SS-RS-GD refutation artifact (scripts/ss_rs_gd_lean.py). CI-safe checks are structural
(the Lean states the refutation core + the erratum); the real kernel verification (all headline theorems
elaborate with only the standard axioms) is a REPL-gated test. No trust surface touched."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("ss_rs_gd_lean", _ROOT / "scripts" / "ss_rs_gd_lean.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_states_the_refutation_core():
    m = _load()
    # the gap identity (1.8), the violation, and a concrete witness must be present
    for name in ["gap_identity", "ss_exceeds_rs", "violation_at_half"]:
        assert f"theorem {name}" in m.SRC


def test_states_the_erratum_and_the_vindication():
    m = _load()
    # the kernel-attested erratum on the paper's (1.7), and the SOS the scout doubted
    assert "paper_eq_1_7_false_at_half" in m.SRC
    assert "sos_cofactor" in m.SRC
    # the intended inequality (still holds) is also recorded
    assert "lamRS_ge_muRS_at_half" in m.SRC


def test_no_stray_sorry():
    m = _load()
    for banned in ["sorry", "admit", "native_decide"]:
        assert banned not in m.SRC, f"artifact must not contain {banned!r}"


def test_headline_list_covers_refutation_and_erratum():
    m = _load()
    assert "SSRSGD.ss_exceeds_rs" in m.HEADLINE
    assert "SSRSGD.paper_eq_1_7_false_at_half" in m.HEADLINE


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_verifies_all_headline_theorems():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    bk = LeanReplBackend(timeout_s=400)
    try:
        r = bk._run(m.full_source(), m.IMPORTS)
    finally:
        bk.close()
    msgs = (r or {}).get("messages", []) or []
    errs = [x for x in msgs if x.get("severity") == "error"]
    assert not errs, errs[:2]
    std = {"propext", "Classical.choice", "Quot.sound"}
    for name in m.HEADLINE:
        line = next((x.get("data", "") for x in msgs if name in (x.get("data") or "")
                     and "axioms" in (x.get("data") or "")), None)
        assert line is not None, f"no axiom line for {name}"
        am = m._AX.search(line)
        assert am is not None
        got = {a.strip() for a in am.group(1).split(",") if a.strip()}
        assert got <= std and got, f"{name}: non-standard axioms {got}"

"""Guard the independent verification of Bartoli-Durante-Grimaldi-Timpanella's (2025) low-degree ovoids of
Q+(7,q) (scripts/verify_ovoids_q7.py).

Exact GF(2^h) checks of Condition (3) are CI-safe; the Lean-kernel `decide` legs are Docker-gated. Tier audit;
report-only; no trust surface."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("ovoids", _ROOT / "scripts" / "verify_ovoids_q7.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_condition3_positive_and_negative():
    m = _load()
    r = m.checks()                                          # q = 2, 4, 8
    assert r["per_q"][2]["is_ovoid"] and r["per_q"][4]["is_ovoid"]     # Kantor ovoid at q=2,4
    assert not r["per_q"][8]["is_ovoid"]                                # NOT an ovoid at q=8
    assert r["per_q"][8]["witness"] == m.Q8_WITNESS
    assert r["q8_witness_form_zero"] and r["all_ok"]
    for q in (2, 4, 8):
        assert r["per_q"][q]["gf_sanity"], q               # GF(2^h) is a field (assoc + distrib + identity)


def test_gf_arithmetic_and_functions():
    m = _load()
    # GF(4): omega^2 = omega + 1 (omega=2 -> 3); GF(8): x^3 = x+1 (2*4 = 3)
    assert m.gmul(2, 2, 4) == 3
    assert m.gmul(2, 4, 8) == 3
    # char 2: add == sub == XOR; the form is symmetric-ish self-check on a known witness
    assert m.form((0, 0, 0), (0, 1, 3), 8) == 0            # the printed q=8 counterexample pair
    assert m.form((0, 0, 0), (0, 0, 1), 4) != 0            # a distinct pair at q=4 (ovoid) must be nonzero


@pytest.mark.skipif(os.environ.get("LEIBNIZ_OVOID_FULL") != "1",
                    reason="q=16 census is ~16.7M pairs (~75s); set LEIBNIZ_OVOID_FULL=1 to run")
def test_q16_is_an_ovoid_slow():
    m = _load()
    ov, wit = m.condition3(16)                              # ~16.7M pairs; the paper's third positive case
    assert ov and wit is None


def test_cert_wellformed_and_no_cheating():
    import re
    m = _load()
    src, names = m.build_lean_cert()
    assert names == ["ovoid_q2", "ovoid_q4", "ovoid_q8_fails"]
    assert src.count("by decide") == 3
    assert "condition3 2 7 4 = true" in src                 # q=4 positive
    assert "form 3 11 (0,0,0) (0,1,3) == 0" in src          # q=8 negative witness
    code = re.sub(r"/-.*?-/", " ", src, flags=re.DOTALL)
    assert "native_decide" not in code and "sorry" not in code


def test_live_kernel_legs():
    m = _load()
    try:
        from leibniz.backends.lean_repl import available
    except Exception:
        pytest.skip("lean_repl backend unavailable")
    if not available():
        pytest.skip("Docker + Lean 4.31 REPL image unavailable")
    src, _ = m.build_lean_cert()
    res = m.run_kernel(src)
    assert res["status"] == "checked" and res["all_verified"] is True
    for name, leg in res["legs"].items():
        assert "sorryAx" not in leg.get("axioms", ""), name

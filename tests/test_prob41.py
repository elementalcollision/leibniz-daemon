"""Guard the Problem 41 monomial-normality certificates (scripts/prob41_normality_lean.py). The reusable
`certify(a,b,c)` checker is exact-integer and CI-safe; the (4,5,7) kernel certificate (axiom-free `decide`) is
a REPL-gated test. No trust surface touched."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("prob41_normality_lean",
                                                  _ROOT / "scripts" / "prob41_normality_lean.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_four_five_seven_not_normal_with_expected_witness():
    m = _load()
    r = m.certify(4, 5, 7)
    assert r["normal"] is False
    assert r["witness"] == [2, 4, 5]            # x^2 y^4 z^5
    assert r["L"] == 140 and r["weights"] == [35, 28, 20]
    assert r["witness_wt"] == 282 and 282 >= 2 * r["L"]   # in closure(I^2)


def test_normal_triples_certify_normal():
    m = _load()
    for t in [(3, 3, 3), (2, 3, 5), (1, 1, 1), (4, 5, 6)]:
        assert m.certify(*t)["normal"] is True, t


def test_witness_really_excluded_from_I2():
    # Independently re-derive: no v ≤ (2,4,5) has 140 ≤ wt(v) ≤ 142 (so x^(2,4,5) ∉ I^2).
    L = 140
    hits = [(a, b, c) for a in range(3) for b in range(5) for c in range(6)
            if L <= 35 * a + 28 * b + 20 * c <= 282 - L]
    assert hits == []


def test_emitted_lean_cert_is_wellformed():
    m = _load()
    src = m.lean_cert(4, 5, 7, [2, 4, 5])
    assert "triple_4_5_7_not_normal" in src
    assert "280 ≤ wt 2 4 5" in src and ":= by decide" in src
    for banned in ["sorry", "native_decide", "admit"]:
        assert banned not in src


def test_artifact_source_carries_both_forms_and_no_sorry():
    m = _load()
    assert "four_five_seven_not_normal_collapsed" in m.SRC_457
    assert "four_five_seven_not_normal_direct" in m.SRC_457
    for banned in ["sorry", "native_decide", "admit"]:
        assert banned not in m.SRC_457


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_decides_axiom_free():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    bk = LeanReplBackend(timeout_s=400)
    try:
        src = m.SRC_457 + "\n" + "\n".join(f"#print axioms {n}" for n in m.HEADLINE) + "\n"
        r = bk._run(src, m.IMPORTS)
    finally:
        bk.close()
    msgs = (r or {}).get("messages", []) or []
    assert not [x for x in msgs if x.get("severity") == "error"]
    axiom_lines = [x.get("data", "") for x in msgs if "axiom" in (x.get("data") or "")]
    assert len(axiom_lines) == 2
    assert all("does not depend on any axioms" in ln for ln in axiom_lines)

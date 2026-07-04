"""Guard the independent verification of Ataka–Matsuoka (2026), Example 4.5 — closure(x⁷,y³,z²) has exactly 8
minimal generators and is NOT normal (scripts/verify_ataka_matsuoka.py + the Problem-41 instrument). The
exact-integer cross-checks against the paper are CI-safe; the axiom-free `decide` kernel leg is REPL-gated.
Tier audit, verification-amplification; no trust surface touched."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _verify():
    return _load("verify_am", "scripts/verify_ataka_matsuoka.py")


def _prob41():
    return _load("prob41", "scripts/prob41_normality_lean.py")


def test_closure_732_has_exactly_the_paper_eight_generators():
    # Ataka–Matsuoka Ex. 4.5: I = (x^7,y^3,z^2, x^5y, x^3y^2, x^4z, y^2z, x^2yz), μ(I) = 8.
    m = _prob41()
    gens = m.min_generators(7, 3, 2)
    assert len(gens) == 8
    assert set(gens) == {(7, 0, 0), (0, 3, 0), (0, 0, 2), (5, 1, 0), (3, 2, 0), (4, 0, 1), (0, 2, 1), (2, 1, 1)}


def test_closure_732_is_not_normal_with_paper_witness():
    m = _prob41()
    r = m.certify(7, 3, 2)
    assert r["normal"] is False
    assert r["witness"] == [6, 2, 1]                       # x^6 y^2 z, exactly the paper's witness
    assert r["L"] == 42 and r["weights"] == [6, 14, 21]
    assert r["witness_wt"] == 85 and 85 >= 2 * r["L"]      # wt = 85 ≥ 2L = 84, so in closure(I^2)


def test_witness_really_excluded_from_I2():
    # Independently re-derive: no v ≤ (6,2,1) has 42 ≤ wt(v) ≤ 85 − 42 = 43 (so x^(6,2,1) ∉ I^2).
    hits = [(a, b, c) for a in range(7) for b in range(3) for c in range(2)
            if 42 <= 6 * a + 14 * b + 21 * c <= 43]
    assert hits == []


def test_all_faithfulness_cross_checks_pass():
    v = _verify()
    _src, prov = v.build_certificate(v._prob41())
    assert all(prov["checks"].values()), prov["checks"]
    assert prov["generator_count"] == 8 and prov["witness"] == [6, 2, 1]


def test_generated_certificate_is_wellformed_and_clean():
    v = _verify()
    src, _prov = v.build_certificate(v._prob41())
    assert "eight_minimal_generators" in src
    assert "generators_are_paper_list" in src
    assert "not_normal_witness_x6y2z" in src
    assert "arXiv:2602.01782" in src and ":= by decide" in src
    for banned in ["sorry", "native_decide", "admit"]:
        assert banned not in src


def test_reference_is_apa_and_registered_in_domain():
    v = _verify()
    assert "Ataka, M., & Matsuoka, N. (2026)" in v.REF_AM["citation"]
    assert v.REF_AM["url"] == "https://arxiv.org/abs/2602.01782"
    dom = _load("cdomain", "scripts/counterexample_domain.py")
    reg = dom.registry()
    assert any(o.get("params") == {"a": 7, "b": 3, "c": 2} for o in reg)   # certified object in the corpus
    c = dom.certify({"family": "monomial_normal", "params": {"a": 7, "b": 3, "c": 2}})
    assert c["verdict"] == "not-normal" and any("Ataka" in r["citation"] for r in c["references"])


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_decides_axiom_free():
    v = _verify()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    src, _prov = v.build_certificate(v._prob41())
    run_src = src.split("import Mathlib.Tactic\n", 1)[1] + "\n" + "\n".join(
        f"#print axioms {n}" for n in v.HEADLINE) + "\n"
    bk = LeanReplBackend(timeout_s=500)
    try:
        r = bk._run(run_src, v.IMPORTS)
    finally:
        bk.close()
    msgs = (r or {}).get("messages", []) or []
    assert not [x for x in msgs if x.get("severity") == "error"]
    axiom_lines = [x.get("data", "") for x in msgs if "axiom" in (x.get("data") or "")]
    assert len(axiom_lines) == 3                                    # three headline theorems
    assert all("does not depend on any axioms" in ln for ln in axiom_lines)

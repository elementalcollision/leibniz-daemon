"""Guard the general monomial-ideal normality instrument (scripts/monomial_ideal_normality.py) and the
independent verification of Ataka–Matsuoka (2026) Example 4.7: 4.7(1) is normal (control), 4.7(2) is NOT
integrally closed (a kernel-checkable erratum). Exact-integer checks are CI-safe; the axiom-free `decide`
kernel leg is REPL-gated. Tier audit, verification-amplification; no trust surface touched."""
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


def _instr():
    return _load("min", "scripts/monomial_ideal_normality.py")


def _verify():
    return _load("verify47", "scripts/verify_ataka_matsuoka_47.py")


def test_instrument_agrees_with_corner_checker_on_pure_powers():
    # The general instrument, run on the CLOSURE of a corner ideal (its closure computed by the instrument
    # itself, not the corner code), must agree with the corner certify. Uses only pre-existing certify().
    m = _instr()
    p = _load("p41", "scripts/prob41_normality_lean.py")
    for a, b, c in [(4, 5, 7), (3, 3, 3), (7, 3, 2)]:
        closure_gens = m.closure_min_generators([(a, 0, 0), (0, b, 0), (0, 0, c)])
        assert m.is_normal(closure_gens)["normal"] == p.certify(a, b, c)["normal"], (a, b, c)


def test_47_1_is_normal():
    m = _instr()
    r = m.is_normal([(3, 0, 0), (0, 2, 0), (0, 0, 2), (1, 1, 0), (1, 0, 1), (0, 1, 1)])
    assert r["I_integrally_closed"] and r["I2_integrally_closed"] and r["normal"] is True


def test_47_2_is_not_integrally_closed_with_xz2_witness():
    m = _instr()
    G = [(3, 0, 0), (0, 3, 0), (0, 0, 3), (2, 1, 0), (1, 2, 0), (2, 0, 1), (0, 1, 1)]
    r = m.is_normal(G)
    assert r["I_integrally_closed"] is False
    assert r["closure_witness_I"] == [1, 0, 2]                 # xz²
    # airtight integral dependence: xz² ∉ I, (xz²)² = (2,0,4) ∈ I², so xz² is integral over I
    assert m.in_power((1, 0, 2), G, 1) is False
    assert m.in_power((2, 0, 4), G, 2) is True
    assert m.dependence_witness((1, 0, 2), G, 1) == 2


def test_erratum_math_is_exact():
    # (xz²)² = x²z⁴ = (x²z)·(z³): (2,0,1)+(0,0,3) = (2,0,4). Independent re-derivation.
    assert (2, 0, 1) != (0, 0, 3)
    assert tuple(a + b for a, b in zip((2, 0, 1), (0, 0, 3))) == (2, 0, 4)
    assert tuple(2 * x for x in (1, 0, 2)) == (2, 0, 4)


def test_all_cross_checks_pass_and_cert_wellformed():
    v = _verify()
    a = v.analyze(v._instr())
    assert all(a["checks"].values()), a["checks"]
    src = v._CERT
    assert "I2_not_integrally_closed" in src and "arXiv:2602.01782" in src and ":= by decide" in src
    for banned in ["sorry", "native_decide", "admit"]:
        assert banned not in src


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_decides_axiom_free():
    v = _verify()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    run_src = v._CERT.split("import Mathlib.Tactic\n", 1)[1] + "\n" + "\n".join(
        f"#print axioms {n}" for n in v.HEADLINE) + "\n"
    bk = LeanReplBackend(timeout_s=500)
    try:
        r = bk._run(run_src, v.IMPORTS)
    finally:
        bk.close()
    msgs = (r or {}).get("messages", []) or []
    assert not [x for x in msgs if x.get("severity") == "error"]
    axiom_lines = [x.get("data", "") for x in msgs if "axiom" in (x.get("data") or "")]
    assert len(axiom_lines) == 3
    assert all("does not depend on any axioms" in ln for ln in axiom_lines)

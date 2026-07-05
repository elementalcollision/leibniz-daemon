"""Guard the independent verification of Aliabadi's (2026) counterexample to the Brualdi–Friedland–Pothen
sparse-basis conjecture (scripts/verify_bfp_counterexample.py).

Exact-rational integer-instance checks + cert well-formedness are CI-safe; the Lean-kernel `decide` leg is
Docker-gated; the symbolic ℚ(a,…,l) leg is sympy-gated. Tier audit; report-only; no trust surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("bfp", _ROOT / "scripts" / "verify_bfp_counterexample.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_integer_instance_is_a_counterexample():
    m = _load()
    A, combos, X, d = m.build_instance()
    r = m.checks(A, combos, X, d)
    # rank-m matrix; four genuine elementary vectors; all BFP inequalities hold; yet linearly dependent.
    assert r["rankA"] == 4 and r["membership"] and r["zerosets"] and r["elementary"]
    assert r["bfp_inequalities"] and r["dependent"] and r["rankX"] == 3
    assert r["all_ok"] is True


def test_specialization_is_matroid_faithful():
    m = _load()
    assert m.matroid_faithful() is True            # 39 basis 4×4 minors match the generic case


def test_cert_wellformed_and_no_cheating():
    import re
    m = _load()
    src, name = m.build_lean_cert()
    assert "by decide" in src and f"#print axioms {name}" in src
    code = re.sub(r"/-.*?-/", " ", src, flags=re.DOTALL)   # strip Lean block/doc comments (they mention words)
    assert "native_decide" not in code and "sorry" not in code
    # the five load-bearing pieces are all present in the decided conjunction
    assert "dot (combos.getD s []) (Acols.getD t [])" in src      # (1) membership
    assert "Jl.getD s []).any" in src                             # (2) zero-sets
    assert "detN 4 (submat" in src and "detN 3 (submat" in src    # (3) elementary (rank minors)
    assert "interP P).length + P.length ≤ 4" in src               # (4) BFP inequalities
    assert "dot dvec col == 0" in src and "dvec.any" in src       # (5) dependence ⇒ not a basis


def test_symbolic_general_case():
    m = _load()
    sc = m.symbolic_check()
    if sc is None:
        pytest.skip("sympy unavailable")
    assert sc["all_ok"] is True                    # exact over ℚ(a,…,l): elementary + inequalities + dependent


def test_live_kernel_decides_no_cheating():
    m = _load()
    try:
        from leibniz.backends.lean_repl import available
    except Exception:
        pytest.skip("lean_repl backend unavailable")
    if not available():
        pytest.skip("Docker + Lean 4.31 REPL image unavailable")
    src, name = m.build_lean_cert()
    res = m.run_kernel(src, name)
    assert res["status"] == "checked"
    assert res["verified"] is True and res["no_cheating_axioms"] is True   # propext ok; no sorryAx/native_decide

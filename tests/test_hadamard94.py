"""Guard the independent verification of Szollosi's (2026) complex Hadamard matrix of order 94
(scripts/verify_hadamard94.py).

Exact integer checks (reconstruct the circulants, eq (1), the assembled H H* = 94 I) are CI-safe; the Lean-kernel
`decide` legs are Docker-gated. Tier audit; report-only; no trust surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("had94", _ROOT / "scripts" / "verify_hadamard94.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_both_examples_give_complex_hadamard_94():
    m = _load()
    r = m.checks()
    assert set(r["examples"]) == {"example1", "example2"} and r["all_ok"]
    for name, c in r["examples"].items():
        assert c["sigma_ok"] and c["normSigma_ok"] and c["peak_ok"], name   # published anchors
        assert c["A_symmetric"] and c["B_symmetric"], name
        assert c["eq1_188I"], name                                          # A A^T+B B^T+C C^T+D D^T = 188 I
        assert c["H_unimodular"] and c["HHstar_94I"], name                  # H H* = 94 I => complex Hadamard order 94


def test_exact_construction_details():
    m = _load()
    # circulant + back-diagonal sanity, and eq (1) really is the 188 I identity
    a = m._pm(m.EXAMPLES["example1"]["rows"]["a"])
    A = m._circ(a)
    assert A[0] == a and all(A[i][j] == a[(j - i) % m.P] for i in range(3) for j in range(3))
    R = m._backdiag(m.P)
    assert all(R[i][j] == (1 if i + j == m.P - 1 else 0) for i in range(m.P) for j in range(m.P))
    # the assembled H must be genuinely non-real (has +-i entries), else it is only a real Hadamard matrix
    c = m.check_example("example1")
    assert c["HHstar_94I"] and c["H_unimodular"]


def test_cert_wellformed_and_no_cheating():
    import re
    m = _load()
    src, names = m.build_lean_cert()
    assert names == ["had94_eq1_example1", "had94_sym_example1", "had94_eq1_example2",
                     "had94_sym_example2", "had94_control"]
    assert src.count("by decide") == 5
    assert "eq1 a1bad b1 c1 d1 = false" in src            # the negative control
    assert "autocorr" in src and "188" in src
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

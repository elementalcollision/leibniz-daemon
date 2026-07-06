"""Guard the independent verification of Cabello's (2025) simplest Kochen-Specker set
(scripts/verify_cabello_ks.py).

Exact Eisenstein-integer orthogonality + the backtracking KS-uncolorability search are CI-safe; the Lean-kernel
`decide` legs are Docker-gated. Tier audit; report-only; no trust surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("cabks", _ROOT / "scripts" / "verify_cabello_ks.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_ks_set_structure_and_uncolorability():
    m = _load()
    r = m.checks()
    assert r["n_rays"] == 33 and r["n_bases"] == 14 and r["all_bases_orthogonal"]
    assert r["ks_uncolorable"]                       # no {0,1} KS assignment exists
    assert r["control_13basis_colorable"]            # dropping a basis makes it colorable (discriminating)
    assert r["z3_unsat"] in (True, "z3-unavailable")
    assert r["ok"]


def test_eisenstein_arithmetic():
    m = _load()
    # w^2 = -1 - w ; w * w = w^2
    assert m.emul(m.W, m.W) == m.W2
    # conj(w) = w^2 ; and w is a unit of norm 1: <w|w> over one coordinate = conj(w)*w = w^2 * w = w^3 = 1
    assert m.emul(m.econj(m.W), m.W) == m.I1
    # every basis is genuinely Hermitian-orthogonal (the transcription self-check, incl. the x3 correction)
    for name, B in m.BASES.items():
        assert all(m.orth(B[i], B[j]) for i in range(3) for j in range(i + 1, 3)), name
    assert m.BASES["x3"][2] == (m.W2, m.NW, m.I1)    # the corrected third vector (w^2, -w, 1)


def test_cert_wellformed_and_no_cheating():
    import re
    m = _load()
    src, names = m.build_lean_cert()
    assert names == ["cabello_bases_orth", "cabello_uncolorable", "cabello_control"]
    assert src.count("by decide") == 3
    assert "solve rays bases [] [] 30 = false" in src        # uncolorability
    assert "solve rays basesDrop1 [] [] 30 = true" in src    # negative control
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

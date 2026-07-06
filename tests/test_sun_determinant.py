"""Guard the independent verification of Zhang & Yang's (2026) proof of Sun's determinant congruence
(scripts/verify_sun_determinant.py).

Exact integer determinant + divisibility checks are CI-safe; the Lean-kernel `decide` legs are Docker-gated.
Tier audit; report-only; no trust surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("sun", _ROOT / "scripts" / "verify_sun_determinant.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_composite_and_prime_congruence():
    m = _load()
    r = m.checks()
    assert all(r["composite_n2_divides"].values())          # n² | Dₙ(c,d) for every composite n, all c,d
    assert all(r["prime_sufficiency"].values())             # (d/p)=−1 ⟹ p² | Dₚ(c,d)
    # sharpness: for each prime, a residue d exists where p² does NOT divide (condition is not vacuous)
    assert all(s["witness_residue_d"] is not None for s in r["sharpness"].values())
    assert r["all_ok"] is True


def test_determinant_matches_known_values():
    m = _load()
    # spot values (fraction-free Bareiss == cofactor); D_4(1,2) = 1179648 = 16·73728
    assert m.D(4, 1, 2) == 1179648 and 1179648 % 16 == 0
    assert m.D(6, 1, 2) % 36 == 0
    assert m.D(5, 1, 2) % 25 == 0                            # (2/5) = −1


def test_cert_wellformed_and_no_cheating():
    import re
    m = _load()
    src, names = m.build_lean_cert()
    assert len(names) == 4 and src.count("by decide") == 4
    assert "detN" in src and "% 16" in src and "% 25" in src
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

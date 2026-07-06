"""Guard the independent verification of Bellah–Dunn–Naidu–Wells's (2025) Markoff (1,1,1) cage result
(scripts/verify_markoff_cage.py).

Exact integer checks (matrix order, 2-adic divisibility, Pisano cross-check) are CI-safe; the Lean-kernel
`decide` legs are Docker-gated. Tier audit; report-only; no trust surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("markoff", _ROOT / "scripts" / "verify_markoff_cage.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_theorem_2_10_and_pisano_for_primes():
    m = _load()
    r = m.checks()
    assert r["positive_ok"] and r["mersenne_ok"] and r["control_ok"] and r["all_ok"]
    for p, c in r["positive"].items():
        assert c["elliptic_x1"] and c["legendre_5"] == -1, p          # p ≡ ±2 mod 5 ⇒ x=1 elliptic
        assert c["two_pow_nu_divides_ord"], p                          # Theorem 2.10: 2^{ν₂(p+1)} | ord
        assert c["kernel_certifies_divisibility"], p                   # A^{p+1}=I ∧ A^{(p+1)/2}≠I
        assert c["ord_equals_pisano_over_2"], p                        # Prop 3.3: ord = π(p)/2


def test_mersenne_order_is_p_plus_1():
    m = _load()
    r = m.checks()
    for p, c in r["mersenne"].items():
        assert c["ord_equals_p_plus_1"], p                             # p+1 = 2ⁿ ⇒ ord = p+1 exactly
        assert c["nu2_p_plus_1"] == (p + 1).bit_length() - 1, p        # ν₂(2ⁿ) = n


def test_negative_control_hypothesis_is_load_bearing():
    m = _load()
    r = m.checks()
    for p, c in r["control"].items():                                  # p ≡ ±1 mod 5: x=1 hyperbolic
        assert not c["elliptic_x1"], p
        assert not c["A_pow_p_plus_1_is_I"], p                         # order does NOT divide p+1


def test_matrix_order_matches_direct_computation():
    m = _load()
    # cross-check the exact-order routine against a brute multiply-until-identity for a small prime
    A = (0, 1, (-1) % 47, 3 % 47)
    cur, d = A, 1
    while cur != m.I2:
        cur = m._mul(cur, A, 47)
        d += 1
    ordA, _ = m.matrix_order(47)
    assert ordA == d and ordA == m.pisano(47) // 2


def test_cert_wellformed_and_no_cheating():
    import re
    m = _load()
    src, names = m.build_lean_cert()
    assert names == ["markoff_div_small", "markoff_div_mersenne", "markoff_pisano", "markoff_control"]
    assert src.count("by decide") == 4
    assert "2147483647" in src                                         # the 2³¹−1 Mersenne leg
    assert "pisano" in src and "matOrder" in src                        # the second (Pisano) route
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

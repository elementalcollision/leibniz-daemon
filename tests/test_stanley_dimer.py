"""Guard the independent disproof of Stanley's 1985 dimer conjecture (scripts/verify_stanley_dimer.py).

Exact domino-tiling counts + exact Berlekamp–Massey + cert well-formedness are CI-safe; the Lean-kernel
`decide` leg (axiom-free) is Docker-gated. Tier audit; report-only; no trust surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("stanley", _ROOT / "scripts" / "verify_stanley_dimer.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_small_k_match_stanley_bound():
    m = _load()
    # Stanley's conjecture HOLDS below k=13: minimal order = 2^floor((k+1)/2).
    for k, want in ((2, 2), (3, 4), (4, 4), (5, 8), (6, 8)):
        assert m.bm_order(m.tiling_counts(k, 2 * want + 6)) == want
    # sanity: k=2 counts are Fibonacci; A_{2,13} = F_14 = 377
    assert m.tiling_counts(2, 13)[13] == 377


def test_k13_is_the_smallest_counterexample():
    m = _load()
    order = m.bm_order(m.tiling_counts(13, 264))       # exact tiling counts + exact BM
    assert order == 112 and order < 128                # 112 < 2^7 = 128  → conjecture FALSE
    assert 128 - order == 16                            # deficiency = deg(f₁₆), Guo–Tao's squared factor


def test_even_recurrence_and_cert_wellformed():
    import re
    m = _load()
    B, ci, L = m.even_recurrence()
    assert L == 56 and ci[0] == 1                       # monic order-56 annihilator of B_m = A_{13,2m}
    assert all(sum(ci[i] * B[mm - i] for i in range(len(ci))) == 0 for mm in range(L, len(B)))
    src, name = m.build_lean_cert()
    assert "by\n  decide" in src and f"#print axioms {name}" in src and "List.range 64" in src
    code = re.sub(r"/-.*?-/", " ", src, flags=re.DOTALL)   # strip Lean block/doc comments (they mention these words)
    assert "native_decide" not in code and "sorry" not in code   # no cheating tactics in actual proof text


def test_live_kernel_axiom_free():
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
    assert res["verified"] is True and res["axiom_free"] is True

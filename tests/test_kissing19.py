"""Guard the independent verification of Boon Suan Ho's (2026) record kissing bound k(19) >= 11948
(scripts/verify_kissing19.py).

Exact bit-arithmetic checks (reconstruct the code, minimum distance, subset, forbidden set) are CI-safe; the
Lean-kernel `decide` legs are Docker-gated — the five light legs run live, the heavy minimum-distance leg is
opt-in (LEIBNIZ_KISSING_FULL=1) since it takes several minutes. Tier audit; report-only; no trust surface."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("kissing", _ROOT / "scripts" / "verify_kissing19.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_construction_and_bound():
    m = _load()
    r = m.checks()
    assert r["dim_M"] == 6 and r["dim_K"] == 10 and r["dim_D"] == 12
    assert r["B_size"] == 320 and r["A_size"] == 1280 and r["A_subset_D"]
    assert r["s5_identity"]
    assert r["D_min_weight"] == 3 and r["n_forbidden"] == 21
    assert r["bound"] == 11948 == m.BASE + 1280
    assert r["ok"]


def test_minimum_distance_two_ways():
    m = _load()
    r = m.checks()
    assert r["min_distance_pairwise"] == 5                 # full 818560-pair census: min distance is exactly 5
    assert r["min_distance_forbidden_diff_ge5"]            # forbidden-difference test agrees (>= 5)


def test_table1_faithfulness():
    # the 21 weight-3/4 words of D must match the paper's Table 1 exactly (a mis-read coordinate would break it)
    m = _load()
    D = m._span(m.DGEN)
    S21 = sorted(x for x in D if m._pc(x) in (3, 4))
    assert sorted(m._w(t) for t in m.TABLE1) == S21
    assert m.checks()["table1_matches"]


def test_reconstruction_independent_of_data_file():
    # A is rebuilt purely from the generators; check the four cosets and the parity-check basis
    m = _load()
    A = m._build_A()
    assert len(A) == 1280 and A == sorted(set(A))
    H = m._dual_basis(m.DGEN)
    assert len(H) == 7
    D = m._span(m.DGEN)
    assert all(all(m._pc(h & x) % 2 == 0 for h in H) for x in D)     # H recognises exactly D


def test_cert_wellformed_and_no_cheating():
    import re
    m = _load()
    src, names = m.build_lean_cert()
    assert names == ["kissing_bound", "kissing_distinct", "kissing_subset_D", "kissing_forbidden_complete",
                     "kissing_mindist", "kissing_negcontrol"]
    assert src.count("by decide") == 6
    assert "10668 + A.length == 11948" in src and "memT tA" in src and "buildSpan gens" in src
    code = re.sub(r"/-.*?-/", " ", src, flags=re.DOTALL)
    assert "native_decide" not in code and "sorry" not in code


def test_live_kernel_light_legs():
    m = _load()
    try:
        from leibniz.backends.lean_repl import available
    except Exception:
        pytest.skip("lean_repl backend unavailable")
    if not available():
        pytest.skip("Docker + Lean 4.31 REPL image unavailable")
    src, _ = m.build_lean_cert()
    res = m.run_kernel(src, skip=("kissing_mindist",))     # the five light legs (< ~1 min total)
    assert res["status"] == "checked" and res["all_verified"] is True
    assert set(res["legs"]) == {"kissing_bound", "kissing_distinct", "kissing_subset_D",
                                "kissing_forbidden_complete", "kissing_negcontrol"}
    for name, leg in res["legs"].items():
        assert "sorryAx" not in leg.get("axioms", ""), name


@pytest.mark.skipif(os.environ.get("LEIBNIZ_KISSING_FULL") != "1",
                    reason="heavy minimum-distance kernel leg (~6 min); set LEIBNIZ_KISSING_FULL=1 to run")
def test_live_kernel_mindist_leg():
    m = _load()
    try:
        from leibniz.backends.lean_repl import available
    except Exception:
        pytest.skip("lean_repl backend unavailable")
    if not available():
        pytest.skip("Docker + Lean 4.31 REPL image unavailable")
    src, _ = m.build_lean_cert()
    res = m.run_kernel(src)                                 # all six legs, including minimum distance
    assert res["status"] == "checked" and res["all_verified"] is True
    assert res["legs"]["kissing_mindist"]["verified"] and "sorryAx" not in res["legs"]["kissing_mindist"]["axioms"]

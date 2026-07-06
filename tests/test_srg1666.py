"""Guard the independent AUDIT of Belousova-Makhnev-Tokbaeva (2026) "A strongly regular graph
with parameters (1666,105,0,7) does not exist" (scripts/verify_srg1666.py).

The exact-rational reconstruction (intersection numbers, Krein parameters, triple-intersection
solutions, the vacuity of the paper's contradiction, and the feasibility witnesses) is CI-safe;
the Lean-kernel `decide` legs are Docker-gated. Tier audit; report-only; no trust surface.

This is an audit finding, not an existence/non-existence claim: it certifies that the given proof
does not decide srg(1666,105,0,7) (the case is treated as OPEN)."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("srg1666", _ROOT / "scripts" / "verify_srg1666.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_reconstruction_and_typo_catch():
    m = _load()
    r = m.checks()
    # Lemmas 1-3 reproduce from the array (first principles), with the one typo caught
    assert r["lemma1_ok"]
    assert r["p2_33"] == 1461 and r["p2_33_typo_forced_to_1461"]     # paper printed 543
    assert r["lemma2_unique"] and r["lemma3_oneparam"]
    assert r["n_vertices"] == 3332


def test_contradiction_is_vacuous():
    m = _load()
    r = m.checks()
    # the paper's two mean-lambda routes are IDENTICALLY equal -> the claimed contradiction is spurious
    assert r["S1"] == r["S2"] == 1999388
    assert r["contradiction_vacuous"]
    assert r["row_identity"]                 # [222]_L2 + [224]_L2 = p^2_22 (1364+97=1461)
    assert r["paper_gap_from_104"]           # the paper's 104 (vs correct 98) manufactures the gap


def test_method_leaves_array_feasible():
    m = _load()
    r = m.checks()
    # all 8 Lemma-3 witnesses satisfy marginals + all zero-Krein equations + non-negativity
    assert r["lemma3_feasible_8"]
    assert r["lemma2_valid"]
    assert r["control_r1_8"]                  # r1=8 out of range -> invalid (discriminating control)
    assert r["num_zero_krein"] > 0
    assert r["ok"]


def test_cert_wellformed_and_no_cheating():
    m = _load()
    src, names = m.build_lean_cert()
    assert names == ["srg1666_row_identity", "srg1666_contradiction_vacuous", "srg1666_paper_gap_from_104",
                     "srg1666_lemma3_feasible", "srg1666_lemma2_feasible", "srg1666_control_r1_8"]
    assert src.count("by decide") == 6
    assert "1461*1460 - 98*1364 : Int) = 98*97 + 1461*1362" in src        # vacuity
    assert "validTbl w8 p2 p2 p2 Q3 zk = false" in src                    # negative control
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

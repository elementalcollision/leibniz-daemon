"""Guard the independent verification of Hetman's (2026) Steiner systems S(2,8,225) and S(2,9,289)
(scripts/verify_steiner_designs.py).

Exact finite-group difference-family + direct pair-coverage checks are CI-safe; the Lean-kernel `decide` legs
are Docker-gated. Tier audit; report-only; no trust surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("steiner", _ROOT / "scripts" / "verify_steiner_designs.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_all_ten_difference_families():
    m = _load()
    r = m.checks()
    assert r["n_S8_225"] == 6 and r["n_S9_289"] == 4        # six + four systems, as in the paper
    for name, d in r["difference_family"].items():
        assert d["ok"], name
        assert d["each_once"] and d["distinct"] == d["v"] - 1


def test_direct_development_is_steiner():
    m = _load()
    r = m.checks()
    # developing a representative of each parameter set: every pair in exactly one block
    for name in ("S8_225_A1", "S8_225_B1", "S9_289_1"):
        d = r["direct_development"][name]
        assert d["ok"] and d["pairs"] == d["expected_pairs"]
    assert r["direct_development"]["S9_289_1"]["n_blocks"] == 1156
    assert r["all_ok"] is True


def test_cert_wellformed_and_no_cheating():
    import re
    m = _load()
    src, names = m.build_lean_cert()
    assert names == ["steiner_S8_225", "steiner_S9_289"]
    assert src.count("by decide") == 2
    assert "isDiffFamily mods8 blocks8 224" in src and "isDiffFamily mods9 blocks9 288" in src
    assert "ds.Nodup" in src                                # distinctness of the differences
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

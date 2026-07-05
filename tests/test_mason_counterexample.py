"""Guard the independent verification of the counterexample to Mason's matroid log-concavity conjecture
(scripts/verify_mason_counterexample.py).

Exact connected-partition counting (validated against brute force) + cert well-formedness are CI-safe; the
Lean-kernel `decide` leg is Docker-gated. Tier audit; report-only; no trust surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("mason", _ROOT / "scripts" / "verify_mason_counterexample.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_counter_matches_bruteforce():
    m = _load()
    assert m.validate_formula() is True            # transfer counter == brute-force connected-partition count


def test_whitney_numbers_and_log_concavity():
    m = _load()
    r = m.checks()
    assert r["W75"] == 18551 and r["W74"] == 983775 and r["W73"] == 52954525
    assert r["matches_paper"] is True
    assert r["W74_sq"] == 967813250625 and r["W73_W75"] == 982359393275
    assert r["log_concavity_fails_at_74"] is True and r["deficit"] == 14546142650
    assert r["all_ok"] is True


def test_cert_wellformed_and_no_cheating():
    import re
    m = _load()
    src, names = m.build_lean_cert()
    assert names == ["mason_whitney_values", "mason_log_concavity_fails"]
    assert src.count("by decide") == 2
    assert "W3 * W3 < W4 * W2" in src                      # the log-concavity inequality (W_74² < W_73·W_75)
    assert "pmul (pmul gsame gsame) gsame" in src          # kernel assembles the 3 long paths itself
    code = re.sub(r"/-.*?-/", " ", src, flags=re.DOTALL)
    assert "native_decide" not in code and "sorry" not in code


def test_live_kernel_decides():
    m = _load()
    try:
        from leibniz.backends.lean_repl import available
    except Exception:
        pytest.skip("lean_repl backend unavailable")
    if not available():
        pytest.skip("Docker + Lean 4.31 REPL image unavailable")
    src, _ = m.build_lean_cert()
    res = m.run_kernel(src)
    assert res["status"] == "checked"
    assert res["verified"] is True and res["no_cheating"] is True

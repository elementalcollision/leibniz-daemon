"""Guard the independent verification of Kable–Mills–Wright's (2026) cap-set subgroups of finite fields
(scripts/verify_capset_subgroups.py).

Exact finite-field arithmetic is CI-safe; the Lean-kernel `decide` legs are Docker-gated. Tier audit;
report-only; no trust surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("capset", _ROOT / "scripts" / "verify_capset_subgroups.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_set_and_evenquads_caps():
    m = _load()
    r = m.checks()
    assert r["set_gf81"]["valid_field"] and r["set_gf81"]["size"] == 20 and r["set_gf81"]["is_cap_no3"]
    assert r["set_gf81_model2"]["size"] == 20 and r["set_gf81_model2"]["is_cap_no3"]   # model-independent
    assert r["evenquads_gf64"]["valid_field"] and r["evenquads_gf64"]["size"] == 9
    assert r["evenquads_gf64"]["is_cap_no4"]
    assert r["all_ok"] is True


def test_general_theorem_family():
    m = _load()
    g = m.checks()["general_theorem"]
    # (2^n - 1)-th powers in GF(2^{2n}) form a cap of size 2^n + 1
    for n in (2, 3, 4, 5):
        assert g[n]["size"] == 2 ** n + 1 and g[n]["size_ok"] and g[n]["is_cap_no4"]


def test_field_construction_and_cap_primitive():
    m = _load()
    # GF(81) fourth powers: a genuine multiplicative subgroup that is a cap by exact F_3 arithmetic
    valid, S, add, zero = m.power_subgroup(3, 4, m.IRRED[(3, 4)], 4)
    assert valid and len(S) == 20 and m.is_cap(S, add, zero, 3)
    # a hand check: the additive identity is absent (nonzero powers) and no 3 distinct sum to 0
    assert zero not in set(S)


def test_cert_wellformed_and_no_cheating():
    import re
    m = _load()
    src, names = m.build_lean_cert()
    assert names == ["capset_set81", "capset_eq64"]
    assert src.count("by decide") == 2
    assert "addm 3" in src and "addm 2" in src            # char-3 SET-cap and char-2 EvenQuads-cap
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

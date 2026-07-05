"""Guard the independent verification of Guo–Krattenthaler (2014), Phase 1 (scripts/guo_krattenthaler_divisibility.py):
the three all-n binomial divisibilities as certified instances + the Sun-conjecture non-divisibility witnesses.
Exact-integer checks are CI-safe; the axiom-clean `decide` kernel leg is REPL-gated. Tier audit; no trust surface."""
from __future__ import annotations

import importlib.util
import os
from math import comb
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "gk", _ROOT / "scripts" / "guo_krattenthaler_divisibility.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_gk_three_divisibilities_hold():
    # (6n−1)|C(12n,3n), (6n−1)|C(12n,4n), (66n−1)|C(330n,88n) — independently re-derived.
    for n in range(1, 13):
        assert comb(12 * n, 3 * n) % (6 * n - 1) == 0, n
        assert comb(12 * n, 4 * n) % (6 * n - 1) == 0, n
    assert comb(330, 88) % 65 == 0


def test_sun_witnesses_are_genuine_non_divisibilities():
    m = _load()
    v = m.verify()
    assert v["all_ok"] is True
    for row in v["sun_witnesses"]:
        a, b, w = row["a"], row["b"], row["witness_n"]
        assert row["qualifies"] is True                       # a has a prime factor not dividing b
        assert w is not None
        assert comb((a + b) * w, a * w) % (b * w + 1) != 0    # genuine non-divisibility


def test_catalan_contrast_always_divides():
    # The a=b=1 Catalan case always divides — the boundary of Sun's non-divisibility.
    for n in range(1, 40):
        assert comb(2 * n, n) % (n + 1) == 0


def test_certificate_wellformed_and_no_cheating():
    m = _load()
    v = m.verify()
    src, names = m.build_certificate(v)
    assert len(names) == 23
    assert "set_option maxRecDepth" in src
    assert "div_330_88_n1" in src and "sun_nondiv_a2_b1" in src
    assert "Nat.choose" in src and src.count(":= by decide") == 23
    for banned in ["sorry", "native_decide", "admit"]:
        assert banned not in src


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_decides_all_clean_axioms():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    src, names = m.build_certificate(m.verify())
    run_src = "".join(ln for ln in src.splitlines(keepends=True) if not ln.startswith("import "))
    run_src += "\n" + "\n".join(f"#print axioms {n}" for n in names) + "\n"
    bk = LeanReplBackend(timeout_s=600)
    try:
        r = bk._run(run_src, m.IMPORTS)
    finally:
        bk.close()
    msgs = (r or {}).get("messages", []) or []
    assert not [x for x in msgs if x.get("severity") == "error"]
    axiom_lines = [x.get("data", "") for x in msgs if "axiom" in (x.get("data") or "")]
    assert len(axiom_lines) == 23
    std = {"propext", "Classical.choice", "Quot.sound"}
    for ln in axiom_lines:
        if "does not depend on any axioms" in ln:
            continue
        toks = [t.strip() for t in ln.split("[", 1)[-1].rstrip("]").split(",") if t.strip()]
        assert all(t in std for t in toks), ln

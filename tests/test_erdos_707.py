"""Guard the independent verification of the finite core of Erdős Problem 707 (scripts/verify_erdos_707.py):
the Alexeev–Mixon / Niu counterexample Sidon sets and their non-extension to small-order perfect difference
sets. Exact checks are CI-safe; the axiom-clean `decide` kernel leg is REPL-gated. Tier audit; no trust surface."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("e707", _ROOT / "scripts" / "verify_erdos_707.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_all_four_sets_are_sidon_and_non_extending():
    m = _load()
    v = m.verify()
    assert v["all_ok"] is True
    for name, r in v["rows"].items():
        assert r["sidon"] is True                        # Sidon over ℤ
        assert r["extends_at"] == []                      # never extends (v ≤ 73)
        assert r["non_extending_orders"]                  # non-empty


def test_key_sets_match_the_papers():
    m = _load()
    assert m.KEY_SETS["A"][0] == [0, 1, 3, 11]            # Niu
    assert m.KEY_SETS["B"][0] == [0, 1, 4, 11]
    assert m.KEY_SETS["AM5"][0] == [1, 2, 4, 8, 13]       # Alexeev–Mixon (disproves Erdős 707)
    assert m.KEY_SETS["Hall"][0] == [1, 3, 9, 10, 13]


def test_pds_and_sidon_helpers_are_correct():
    m = _load()
    # A={0,1,3,11} mod 13 is NOT a PDS of order 4 (its differences collide) — the base non-extension.
    assert m._is_pds([0, 1, 3, 11], 13) is False
    # a genuine PDS of order 4: the Singer PDS {0,1,3,9} in ℤ_13 (differences 1..12 each once).
    assert m._is_pds([0, 1, 3, 9], 13) is True
    assert m.is_sidon([1, 2, 4, 8, 13]) is True


def test_certificate_wellformed_and_clean():
    m = _load()
    src, names = m.build_certificate()
    assert len(names) == 12                               # 4 sets × (sidon + 2 non-extension orders)
    assert "A_sidon" in src and "AM5_no_order5" in src and "def isPDS" in src
    assert "arXiv:2510.19804" in src and "arXiv:2604.25214" in src
    for banned in ["sorry", "native_decide", "admit"]:
        assert banned not in src


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_decides_all_clean_axioms():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    src, names = m.build_certificate()
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
    assert len(axiom_lines) == 12
    std = {"propext", "Classical.choice", "Quot.sound"}
    for ln in axiom_lines:
        if "does not depend on any axioms" in ln:
            continue
        toks = [t.strip() for t in ln.split("[", 1)[-1].rstrip("]").split(",") if t.strip()]
        assert all(t in std for t in toks), ln

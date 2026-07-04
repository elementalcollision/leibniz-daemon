"""Guard the Problem 41 normality census (scripts/prob41_census.py). The exact census + its structural
findings are CI-safe; the bundled axiom-free `decide` certificate for all non-normal triples is REPL-gated.
Tier audit, verification-amplification; no trust surface touched."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("prob41_census", _ROOT / "scripts" / "prob41_census.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_census_counts_and_minimal_non_normal():
    m = _load()
    rows = m.census(9)
    s = m.summarize(rows)
    assert s["total"] == 165 and s["n_not_normal"] == 11
    # the two smallest non-normal corner triples (sum 12), both smaller than Huneke–Swanson (4,5,7):
    assert s["minimal_not_normal"] == [[2, 3, 7], [3, 4, 5]]


def test_the_minimal_witness_is_the_ataka_matsuoka_example():
    # (2,3,7) is closure(x⁷,y³,z²) up to permutation — the Ataka–Matsuoka (2026) sharpness witness.
    m = _load()
    rows = {tuple(r["triple"]): r for r in m.census(9)}
    assert rows[(2, 3, 7)]["normal"] is False
    assert sorted((2, 3, 7)) == sorted((7, 3, 2))


def test_structural_patterns_hold_in_range():
    m = _load()
    s = m.summarize(m.census(9))
    assert s["all_non_normal_have_distinct_coords"] is True
    assert s["all_non_normal_have_a_ge_2"] is True
    assert s["n_pairwise_coprime"] == 10 and s["non_pairwise_coprime_examples"] == [[5, 6, 8]]


def test_famous_457_present_and_normal_small_cases():
    m = _load()
    rows = {tuple(r["triple"]): r for r in m.census(9)}
    assert rows[(4, 5, 7)]["normal"] is False                 # the textbook example (not minimal)
    for t in [(1, 1, 1), (2, 3, 4), (3, 3, 3), (2, 4, 6)]:
        assert rows[t]["normal"] is True, t


def test_bundled_certificate_is_wellformed_and_clean():
    m = _load()
    rows = m.census(9)
    src, names = m.build_certificate(rows)
    assert len(names) == 11
    assert "triple_2_3_7_not_normal" in src and "triple_3_4_5_not_normal" in src
    assert src.count(":= by decide") == 11
    for banned in ["sorry", "native_decide", "admit"]:
        assert banned not in src


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_decides_all_axiom_free():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    src, names = m.build_certificate(m.census(9))
    run_src = "".join(ln for ln in src.splitlines(keepends=True) if not ln.startswith("import "))
    run_src = run_src + "\n" + "\n".join(f"#print axioms {nm}" for nm in names) + "\n"
    bk = LeanReplBackend(timeout_s=600)
    try:
        r = bk._run(run_src, m.IMPORTS)
    finally:
        bk.close()
    msgs = (r or {}).get("messages", []) or []
    assert not [x for x in msgs if x.get("severity") == "error"]
    axiom_lines = [x.get("data", "") for x in msgs if "axiom" in (x.get("data") or "")]
    assert len(axiom_lines) == 11
    assert all("does not depend on any axioms" in ln for ln in axiom_lines)

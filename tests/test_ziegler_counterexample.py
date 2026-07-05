"""Guard the independent verification of Kaibel & Pokutta's (2026) counterexample to Ziegler's cross-polytope
conjecture (scripts/verify_ziegler_counterexample.py).

Exact-rational checks (dim, facet enumeration, closed pseudomanifold, not-centrally-symmetric) + cert
well-formedness are CI-safe; the Lean-kernel `decide` legs are Docker-gated (and slow). Tier audit; report-only;
no trust surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("ziegler", _ROOT / "scripts" / "verify_ziegler_counterexample.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_exact_rational_counterexample():
    m = _load()
    r = m.checks()
    # a simplicial 7-polytope with 2·7=14 vertices that is NOT centrally symmetric — disproving Ziegler.
    assert r["dim"] == 7
    assert r["n_facets"] == 136 and r["simplicial"] and r["aff_indep"]
    assert r["closed_pseudomanifold"] and r["n_ridges"] == 476       # every ridge in exactly 2 facets
    assert r["balanced"] and r["antipode_absent"] == [0, 4, 5, 9]
    assert r["not_centrally_symmetric"] and r["all_ok"] is True


def test_vertices_match_paper():
    m = _load()
    # 14 distinct 0/1 vectors in dimension 7 (Theorem 3.1)
    assert len(m.V) == 14 and len(set(map(tuple, m.V))) == 14
    assert all(len(v) == 7 and set(v) <= {0, 1} for v in m.V)


def test_cert_wellformed_and_no_cheating():
    import re
    m = _load()
    src, names = m.build_lean_cert()
    assert names == ["ziegler_dim_notsym", "ziegler_supporting", "ziegler_closed"]
    assert src.count("by decide") == 3
    for nm in names:
        assert f"#print axioms {nm}" in src
    code = re.sub(r"/-.*?-/", " ", src, flags=re.DOTALL)             # strip Lean comments (mention the words)
    assert "native_decide" not in code and "sorry" not in code
    # the three load-bearing legs are present
    assert "detN 8" in src                                            # dim 7 witness
    assert "1 - x" in src and "== 7" in src                          # antipodes + balanced
    assert "partner.getD" in src                                     # closed pseudomanifold


def test_live_kernel_legs():
    m = _load()
    try:
        from leibniz.backends.lean_repl import available
    except Exception:
        pytest.skip("lean_repl backend unavailable")
    if not available():
        pytest.skip("Docker + Lean 4.31 REPL image unavailable")
    src, names = m.build_lean_cert()
    # verify only the fast dim/not-symmetric leg here (the supporting/closed legs are ~40–60 s each).
    fast = [(nm, decl) for nm, decl in m._leg_decls(src) if nm == "ziegler_dim_notsym"]
    from leibniz.backends.lean_repl import LeanReplBackend
    body = "\n".join(ln for ln in fast[0][1].splitlines() if not ln.startswith("import "))
    res = LeanReplBackend(timeout_s=120)._run(body, ())
    assert isinstance(res, dict)
    errs = [x for x in res.get("messages", []) if x.get("severity") == "error"]
    ax = " ".join(str(x.get("data", "")) for x in res.get("messages", []))
    assert not errs and "sorryAx" not in ax and "native_decide" not in ax

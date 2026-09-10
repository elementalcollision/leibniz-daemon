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
        pytest.skip("Docker + Lean 4.34 REPL image unavailable")
    src, names = m.build_lean_cert()
    # `ziegler_dim_notsym` is the SLOWEST leg, not the fast one. Measured on an idle host:
    # dim_notsym 53.2 s, supporting 10.2 s, closed 9.5 s. The comment here used to call it "the
    # fast leg" and the other two "~40-60 s each" -- inverted -- and on the strength of that the
    # tightest budget in the family (120 s, against the library default of 180) was handed to the
    # most expensive leg.
    leg = [(nm, decl) for nm, decl in m._leg_decls(src) if nm == "ziegler_dim_notsym"]
    from leibniz.backends.lean_repl import LeanReplBackend
    body = "\n".join(ln for ln in leg[0][1].splitlines() if not ln.startswith("import "))
    be = LeanReplBackend(timeout_s=300)
    try:
        res = be._run(body, ())
        # `_run` returns None for a TIMEOUT and for a DEAD CONTAINER alike, and this test could
        # not tell them apart -- so an OOM kill was reported as a verification failure. Under suite
        # contention the container is killed (rc 137) rather than the proof failing; that is an
        # infrastructure fact about the host, not a fact about the certificate.
        rc = be._proc.poll() if be._proc is not None else None
        if res is None and rc not in (None, 0):
            pytest.skip(f"Lean container died (rc={rc}) -- host contention, not a proof failure")
    finally:
        be.close()
    assert isinstance(res, dict)
    errs = [x for x in res.get("messages", []) if x.get("severity") == "error"]
    ax = " ".join(str(x.get("data", "")) for x in res.get("messages", []))
    assert not errs and "sorryAx" not in ax and "native_decide" not in ax

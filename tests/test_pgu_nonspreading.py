"""Guard the independent verification of Bamberg–Giudici–Lansdown–Royle's Conjecture 4.1
(scripts/verify_pgu_nonspreading.py).

Exact GF(q²) checks of the n(κ)=n(−κ) solution-count symmetry are CI-safe; the Lean-kernel `decide` leg
(base case q=3) is Docker-gated. Tier audit; report-only; no trust surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("pgu", _ROOT / "scripts" / "verify_pgu_nonspreading.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_field_arithmetic_gf_q2():
    m = _load()
    for q in (3, 5, 7):
        F = m.Fq2(q)
        # X² = r  (X is the pair (0,1))
        assert F.mul((0, 1), (0, 1)) == (F.r % q, 0)
        for x in F.elems:
            assert F.frob(x) == F.powp(x, q)                 # Frobenius x^q = negate X-coefficient
            assert F.norm(x) == F.powp(x, q + 1)[0] and F.powp(x, q + 1)[1] == 0   # norm ∈ F_q


def test_conjecture_holds_small_primes():
    m = _load()
    for q in (3, 5):
        c = m.check_conjecture(q)
        assert c["symmetry_holds_for_nontrivial"], q       # n(κ)=n(−κ) for all non-trivial (s,u,w)
        assert c["origin_is_sole_exception"], q            # the trivial origin is the ONLY exception
        assert c["failing_suw_count"] == 1, q              # exactly one failing triple: (0,0,0)


def test_conjecture_holds_q7():
    m = _load()
    c = m.check_conjecture(7)                               # slower (larger field); still exact
    assert c["symmetry_holds_for_nontrivial"] and c["origin_is_sole_exception"]


def test_symmetry_is_specifically_negation():
    # for q ≥ 5 the symmetry is κ↦−κ, not "all counts equal": a tuple with n(1) ≠ n(2) must exist
    m = _load()
    for q in (5, 7):
        c = m.check_conjecture(q)
        ap = c["specificity_asymmetric_pair"]
        assert ap is not None and ap["n"][1] != ap["n"][2], q


def test_origin_actually_breaks_symmetry():
    # the negative control the kernel re-decides: at (0,0,0) the symmetry fails for some admissible b
    m = _load()
    F = m.Fq2(3)
    broke = False
    for b in m._valid_b(F):
        n = m.counts(F, b, F.zero, F.zero, F.zero)
        if any(n[k] != n[(3 - k) % 3] for k in range(1, 3)):
            broke = True
    assert broke


def test_cert_wellformed_and_no_cheating():
    import re
    m = _load()
    src, names = m.build_lean_cert()
    assert names == ["pgu_q3_symmetry", "pgu_q3_origin"]
    assert src.count("by decide") == 2
    assert "symmetryHolds 3 2 = true" in src and "originBreaks 3 2 = true" in src
    code = re.sub(r"/-.*?-/", " ", src, flags=re.DOTALL)
    assert "native_decide" not in code and "sorry" not in code


def test_live_kernel_leg():
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

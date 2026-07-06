"""Guard the independent verification of Csajbók–Héger's (2019) double blocking sets of size 3q−1 in PG(2,q)
(scripts/verify_double_blocking.py).

Exact GF(q) incidence checks — double blocking, minimality, and the paper's secant distribution — are CI-safe;
the Lean-kernel `decide` legs are Docker-gated. Tier audit; report-only; no trust surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("dbs", _ROOT / "scripts" / "verify_double_blocking.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_all_prime_cases_double_blocking_and_minimal():
    m = _load()
    r = m.checks()
    assert set(r["prime_cases"]) == {13, 19, 31, 37, 43}
    for q, c in r["prime_cases"].items():
        assert c["size"] == 3 * q - 1, q                # size 3q−1, smaller than the trivial 3q triangle
        assert c["n_lines"] == q * q + q + 1, q
        assert c["double_blocking"] and c["minimal"], q
        assert c["neg_control_not_double_blocking"], q  # deleting a point breaks double blocking
    assert r["all_ok"] is True


def test_published_secant_distributions_match():
    # Reproducing the paper's published nₜ (t ≥ 3) exactly is the faithfulness anchor: one mis-read point shifts it.
    m = _load()
    r = m.checks()
    for q, c in r["prime_cases"].items():
        assert c["dist_match"], q
        # double blocking is exactly "no 0- and no 1-secant"
        assert c["full_dist"].get(0, 0) == 0 and c["full_dist"].get(1, 0) == 0, q
        for t, n in c["published_dist"].items():
            assert c["full_dist"].get(t, 0) == n, (q, t)


def test_incidence_is_projective_and_wellformed():
    m = _load()
    # incidence is independent of the chosen homogeneous representative
    q = 13
    line, pt = (1, 2, 3), (4, 5, 1)
    base = m.incident(line, pt, q)
    assert m.incident(line, tuple((7 * c) % q for c in pt), q) == base          # scale the point
    assert m.incident(tuple((5 * c) % q for c in line), pt, q) == base          # scale the line
    assert len(m.all_lines(q)) == q * q + q + 1
    # every point of B is a canonical representative (leading non-zero coord = 1)
    B = m.build_B(q, m.SYSTEMS[q]["S"])
    for p in B:
        assert p == m.canon_point(p, q)


def test_cert_wellformed_and_no_cheating():
    import re
    m = _load()
    src, names = m.build_lean_cert()
    assert names == ["db13_blocking", "db13_minimal", "db13_control",
                     "db19_blocking", "db19_minimal", "db19_control"]
    assert src.count("by decide") == 6
    assert "= false := by decide" in src                       # the discriminating negative control
    assert "doubleBlocking 13 B13 lines13 = true" in src and "minimalDBS 19 B19 lines19 = true" in src
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
        assert "sorryAx" not in leg.get("axioms", ""), name    # no cheating; controls prove `= false` honestly

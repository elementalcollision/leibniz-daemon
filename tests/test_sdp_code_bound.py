"""Guard the code-SDP -> dual-cert -> kernel pipeline pre-validation (scripts/sdp_code_bound.py).

Free-CPU: the confusability-graph construction and the KNOWN-extension cross-check against the Delsarte LP
probe's OWN exact-integer certificate (never a bare assertion). The SDP solve needs cvxpy (operator-local,
like ortools); the certificate rounding is free-CPU once y is given; the kernel leg needs docker (the real
Lean 4.31 image) and is gated separately so this file still collects (skipping cleanly) in CI."""
from __future__ import annotations

import importlib.util
from fractions import Fraction as Fr
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_HAS_CVXPY = importlib.util.find_spec("cvxpy") is not None and importlib.util.find_spec("numpy") is not None
_needs_cvxpy = pytest.mark.skipif(not _HAS_CVXPY, reason="cvxpy/numpy are operator-local; SDP test skipped in CI")


def _load(mod, rel):
    import sys
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


sb = _load("sdp_code_bound", "scripts/sdp_code_bound.py")


def _lean_available() -> bool:
    try:
        from leibniz.backends.lean_cli import available
        return available()
    except Exception:
        return False


_needs_docker = pytest.mark.skipif(not _lean_available(), reason="docker/leibniz-lean image unavailable")


# ---- free-CPU: graph construction + the KNOWN-extension cross-check -------------------------------------

def test_confusability_graph_shape():
    N, edges = sb.confusability_graph(4, 2)
    assert N == 16  # 2^4 vertices
    # A(4,2) confusability graph: edge iff Hamming distance < 2, i.e. distance <= 1 (adjacent or identical
    # vertices only -- but i<j so distance>=1): exactly the hypercube graph Q4, which has N*n/2 edges.
    assert len(edges) == 16 * 4 // 2 == 32


def test_known_extension_matches_delsarte_lp_cert():
    """The three small cells added to KNOWN (needed because the kernel leg's matrix-dimension wall caps
    usable cells at n<=5) are cross-checked against the Delsarte LP probe's OWN exact-integer certificate,
    not just asserted."""
    for (n, d), expected in (((4, 2), 8), ((4, 4), 2), ((5, 2), 16)):
        sol = sb.dl.solve_dual_lp(n, d)
        assert sol is not None
        cert = sb.dl.rationalize_and_verify(n, d, sol[0])
        assert cert is not None
        p, bound, q, _D = cert
        ok, b, _ = sb.dl.verify_integer_cert(n, d, p, q)
        assert ok and b == bound == expected == sb.KNOWN[(n, d)]


# ---- cvxpy-gated: the SDP solve + exact rational certificate (no kernel) --------------------------------

@_needs_cvxpy
def test_theta_dual_reproduces_known_bound_a42():
    N, edges = sb.confusability_graph(4, 2)
    sol = sb.solve_theta_dual(N, edges)
    assert sol is not None
    t_float, _y = sol
    assert abs(t_float - 8.0) < 1e-4          # theta(G(4,2)) = 8 exactly, tight with A(4,2)=8


@_needs_cvxpy
def test_min_rational_cert_verifies_exactly_a44():
    """A(4,4)=2 is the smallest/simplest tight cell: confirms the untrusted-float -> exact-rational-cert
    chain produces a certificate the PYTHON exact re-check (verify_int_cert) accepts, and that it floors to
    the known value."""
    n, d = 4, 4
    N, edges = sb.confusability_graph(n, d)
    sol = sb.solve_theta_dual(N, edges)
    t_float, y_float = sol
    P = 10
    y_rat = [Fr(round(v * P), P) for v in y_float]
    got = sb.min_rational_cert(N, edges, y_rat, P)
    assert got is not None
    t, Zn, (Li, di, sc) = got
    assert sb.pm.verify_int_cert(Zn, Li, di, sc)      # exact re-check (the SOUND leg)
    assert int(t) == sb.KNOWN[(n, d)] == 2            # floor(t) reproduces A(4,4)=2


@_needs_cvxpy
def test_run_cell_verified_and_matches_known_without_kernel():
    row = sb.run_cell(4, 4, kernel=None)
    assert row["status"] == "verified"
    assert row["reproduces_known"] is True
    assert row["cert_bound"] == 2
    # SOUNDNESS INVARIANT: a verified cert is always a valid upper bound -> never strictly below known.
    assert row["cert_bound"] >= row["known"]


@_needs_cvxpy
def test_min_rational_cert_respects_max_bits_ceiling():
    """The compute-trap safety net: an artificially tiny max_bits must force min_rational_cert to report
    None rather than let bit growth run uncontrolled into Python's int-str conversion limit."""
    N, edges = sb.confusability_graph(4, 4)
    sol = sb.solve_theta_dual(N, edges)
    _t_float, y_float = sol
    y_rat = [Fr(round(v * 10), 10) for v in y_float]
    assert sb.min_rational_cert(N, edges, y_rat, 10, max_bits=1) is None


# ---- docker-gated: the real Lean 4.31 kernel (the actual deliverable) ------------------------------------

@_needs_cvxpy
@_needs_docker
def test_kernel_verifies_a44_and_rejects_bogus_cert():
    """End-to-end soundness on the real kernel: a genuine certificate for A(4,4)=2 verifies, and a corrupted
    (negative-diagonal) certificate is REJECTED. This is the actual trust-relevant assertion: an LLM/solver
    error cannot leak a false result past this check."""
    from leibniz.backends.lean_cli import LeanCliBackend
    bk = LeanCliBackend(timeout_s=180)

    n, d = 4, 4
    N, edges = sb.confusability_graph(n, d)
    sol = sb.solve_theta_dual(N, edges)
    t_float, y_float = sol
    P = 10
    y_rat = [Fr(round(v * P), P) for v in y_float]
    got = sb.min_rational_cert(N, edges, y_rat, P)
    assert got is not None
    t, Zn, (Li, di, sc) = got
    assert int(t) == 2

    good_src = "set_option maxHeartbeats 0\n" + sb.pm.render_ldlt_lean(Zn, Li, di, sc)
    assert bk.check_source(good_src) is True

    bogus_di = [x - 10 ** 9 for x in di]  # forces a negative diagonal entry -> ldltOK must be false
    bogus_src = "set_option maxHeartbeats 0\n" + sb.pm.render_ldlt_lean(Zn, Li, bogus_di, sc)
    assert bk.check_source(bogus_src) is False


@_needs_cvxpy
@_needs_docker
def test_main_pipeline_is_green():
    """Runs the full pipeline (all 3 cells, real kernel checks, bogus-cert control) end to end and asserts
    the GREEN gate -- the actual deliverable of this build."""
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = sb.main()
    assert rc == 0
    import json
    res = json.loads(sb.OUT.read_text())
    assert res["gate"] == "GREEN"
    assert res["reproduced_known"] == 3
    assert res["kernel_verified"] == 3
    assert res["below_known_count"] == 0
    assert res["bogus_cert_kernel_result"] is False
    assert res["sound"] is True
    for row in res["rows"]:
        if row.get("status") == "verified":
            assert row["cert_bound"] >= row["known"]   # soundness invariant, again, on the persisted JSON

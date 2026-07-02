"""Guard D2 (task #103) — the truncated-dual exact certification that resolved the A(22,10) anomaly
(scripts/terwilliger_anomaly.py). The trust-relevant assertions: the truncated build is a genuine RELAXATION
(so its dual certifies the full problem), the zero-block trivial LDLT certificate is exactly valid, and the
headline regression — A(22,10) <= 87 (Schrijver Table I) certifies exactly through the truncated dual.
cvxpy/sdpap are operator-local, so the solve-dependent tests SKIP cleanly in CI."""
from __future__ import annotations

import importlib.util
from fractions import Fraction as Fr
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_HAS = importlib.util.find_spec("cvxpy") is not None and importlib.util.find_spec("numpy") is not None
_needs = pytest.mark.skipif(not _HAS, reason="cvxpy/numpy are operator-local; SDP solve skipped in CI")
_HAS_SDPA = _HAS and importlib.util.find_spec("sdpap") is not None
_needs_sdpa = pytest.mark.skipif(
    not _HAS_SDPA, reason="sdpap (sdpa-multiprecision) is operator-local; anomaly cells skipped in CI")


def _load():
    spec = importlib.util.spec_from_file_location(
        "terwilliger_anomaly", _ROOT / "scripts" / "terwilliger_anomaly.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def ta():
    if not _HAS:                       # the module imports terwilliger_cert, which needs numpy at call time
        pytest.skip("cvxpy/numpy are operator-local")
    return _load()


@_needs
def test_zero_block_trivial_ldlt_cert_is_exact(ta):
    # A zero dual block gets (L=I, d=0, scale=1); the certificate identity L·diag(d)·Lᵀ == scale·M must hold
    # EXACTLY — this is what the Lean ldltOK checker recomputes.
    duals = {"Z": {0: [[Fr(0)] * 3 for _ in range(3)]}, "Zp": {0: [[Fr(1, 7), Fr(0), Fr(0)],
                                                                   [Fr(0), Fr(2, 7), Fr(0)],
                                                                   [Fr(0), Fr(0), Fr(3, 7)]]}}
    blocks = ta.psd_blocks_with_zeros(duals)
    assert [b["label"] for b in blocks] == ["M_0", "Mp_0"]
    for b in blocks:
        m = len(b["M"])
        L, d, s, M = b["L"], b["d"], b["scale"], b["M"]
        assert s > 0 and all(x >= 0 for x in d)
        ldl = [[sum(L[i][k] * d[k] * L[j][k] for k in range(m)) for j in range(m)] for i in range(m)]
        assert ldl == [[s * M[i][j] for j in range(m)] for i in range(m)]


@_needs
def test_truncation_is_a_relaxation(ta):
    # Dropping PSD blocks can only RAISE the optimum — the fact that makes a truncated dual a valid
    # full-problem certificate. Checked on a small cell with the deterministic default solver.
    ts = ta.ts
    full = ts.solve_primal(8, 4)["value"]
    k0 = ts.solve_primal(8, 4, k_max=0)["value"]
    assert k0 >= full - 1e-6


@_needs
def test_build_labeled_kmax_structure(ta):
    H = ta.build_labeled_kmax(8, 4, k_max=1)
    assert sorted(H["psd_h"]) == [(0, "M"), (0, "Mp"), (1, "M"), (1, "Mp")]
    # linear handles must match the full enumeration (they are what the exact LP re-optimizes)
    assert len(H["ii_h"]) == 3 * len(list(ta.td.valid_triples(8)))


@_needs_sdpa
def test_a22_10_certifies_table_I_87(ta):
    # THE D2 headline: the k_max=3 truncated dual certifies Schrijver's Table I value exactly —
    # the anomaly is resolved (the old <=88-only cert was a stalled-full-dual artifact, not a Table I error).
    r = ta.certify_lp_trunc(22, 10, 3, 87)
    assert r.get("certified") is True
    assert r["floor"] == 87
    assert r["floor"] >= 64                    # soundness: never below the known lower bound
    assert Fr(r["exact_bound"]) < 88           # strictly inside the old certificate


@_needs_sdpa
def test_a26_10_certifies_table_I_886(ta):
    # The other stall cell, same route: Table I's 886 certifies exactly (was: 948 float stall, no cert).
    r = ta.certify_lp_trunc(26, 10, 3, 886)
    assert r.get("certified") is True
    assert r["floor"] == 886
    assert r["floor"] >= 384

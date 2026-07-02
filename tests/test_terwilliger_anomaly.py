"""Guard D2 (task #103) — the truncated-dual exact certification that resolved the A(22,10) anomaly.
Post-#238 review the machinery lives in the SHARED modules (terwilliger_sdp.build_labeled(k_max=),
terwilliger_cert.extract_dual(k_max=), terwilliger_exact_lp.certify_lp(k_max=), cert_psd_blocks), so these
tests guard the library, not the thin driver. The trust-relevant assertions: the truncated build is a
genuine RELAXATION (so its dual certifies the full problem), the zero-block trivial LDLT certificate is
exactly valid (and a nonzero-singular block fails LOUDLY, never silently skipped), and the headline
regressions — A(22,10) <= 87 and A(26,10) <= 886 (Schrijver Table I) certify exactly through the truncated
dual, A(26,10) from the k_max=4 dual the shipped artifact's kernel leg attested (from_k_max=4 in
docs/results/terwilliger_anomaly.json). cvxpy/sdpap are operator-local, so solve-dependent tests SKIP in CI."""
from __future__ import annotations

import importlib.util
from fractions import Fraction as Fr
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_HAS = importlib.util.find_spec("cvxpy") is not None and importlib.util.find_spec("numpy") is not None
_needs = pytest.mark.skipif(not _HAS, reason="cvxpy/numpy are operator-local; SDP solve skipped in CI")
_HAS_SDPA = _HAS and importlib.util.find_spec("sdpap") is not None
_needs_sdpa = pytest.mark.skipif(
    not _HAS_SDPA, reason="sdpap (sdpa-multiprecision) is operator-local; anomaly cells skipped in CI")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def mods():
    if not _HAS:                       # terwilliger_cert needs numpy at call time
        pytest.skip("cvxpy/numpy are operator-local")
    ts = _load("terwilliger_sdp")
    tc = _load("terwilliger_cert")
    tlp = _load("terwilliger_exact_lp")
    return SimpleNamespace(ts=ts, tc=tc, tlp=tlp, td=tc.td)


@_needs
def test_zero_block_trivial_ldlt_cert_is_exact(mods):
    # A zero dual block (truncated-dual padding) gets (L=I, d=0, scale=1); the certificate identity
    # L·diag(d)·Lᵀ == scale·M must hold EXACTLY — this is what the Lean ldltOK checker recomputes.
    duals = {"Z": {0: [[Fr(0)] * 3 for _ in range(3)]}, "Zp": {0: [[Fr(1, 7), Fr(0), Fr(0)],
                                                                   [Fr(0), Fr(2, 7), Fr(0)],
                                                                   [Fr(0), Fr(0), Fr(3, 7)]]}}
    blocks = mods.tc.cert_psd_blocks(duals)
    assert [b["label"] for b in blocks] == ["M_0", "Mp_0"]
    for b in blocks:
        m = len(b["M"])
        L, d, s, M = b["L"], b["d"], b["scale"], b["M"]
        assert s > 0 and all(x >= 0 for x in d)
        ldl = [[sum(L[i][k] * d[k] * L[j][k] for k in range(m)) for j in range(m)] for i in range(m)]
        assert ldl == [[s * M[i][j] for j in range(m)] for i in range(m)]


@_needs
def test_nonzero_singular_block_fails_loudly(mods):
    # A NON-zero singular block must return None (loud failure), never be silently skipped: a skipped block
    # would leave the kernel attesting an incomplete block set while claiming the whole certificate.
    duals = {"Z": {0: [[Fr(1), Fr(1)], [Fr(1), Fr(1)]]}, "Zp": {}}
    assert mods.tc.cert_psd_blocks(duals) is None


@_needs
def test_truncation_is_a_relaxation(mods):
    # Dropping PSD blocks can only RAISE the optimum — the fact that makes a truncated dual a valid
    # full-problem certificate. Checked on a small cell with the deterministic default solver.
    full = mods.ts.solve_primal(8, 4)["value"]
    k0 = mods.ts.solve_primal(8, 4, k_max=0)["value"]
    assert k0 >= full - 1e-6


@_needs
def test_build_labeled_kmax_structure(mods):
    H = mods.ts.build_labeled(8, 4, k_max=1)
    assert sorted(H["psd_h"]) == [(0, "M"), (0, "Mp"), (1, "M"), (1, "Mp")]
    # linear handles must match the full enumeration (they are what the exact LP re-optimizes)
    assert len(H["ii_h"]) == 3 * len(list(mods.td.valid_triples(8)))
    # k_max=None keeps the full block families (byte-identical pre-k_max behavior)
    assert sorted(mods.ts.build_labeled(8, 4)["psd_h"]) == [(k, f) for k in range(5) for f in ("M", "Mp")]


@_needs
def test_certify_lp_kmax_zero_pads_small_cell(mods):
    # End-to-end through the SHARED k_max path on a fast cell: the truncated dual, zero-padded on the
    # dropped blocks, certifies the FULL problem (dual_check runs over every block, padding included).
    r = mods.tlp.certify_lp(8, 4, target=16, k_max=1)
    assert r.get("certified") is True
    assert r["floor"] == 16 and r["k_max"] == 1
    assert r["float_status"] == "optimal"      # the status gate lets only clean truncated solves through


@_needs_sdpa
def test_a22_10_certifies_table_I_87(mods):
    # THE D2 headline: the k_max=3 truncated dual certifies Schrijver's Table I value exactly —
    # the anomaly is resolved (the old <=88-only cert was a stalled-full-dual artifact, not a Table I error).
    r = mods.tlp.certify_lp(22, 10, target=87, precisions=(10 ** 14,), k_max=3)
    assert r.get("certified") is True
    assert r["floor"] == 87
    assert r["floor"] >= 64                    # soundness: never below the known lower bound
    assert Fr(r["exact_bound"]) < 88           # strictly inside the old certificate


@_needs_sdpa
def test_a26_10_certifies_table_I_886(mods):
    # The other stall cell, same route: Table I's 886 certifies exactly (was: 948 float stall, no cert).
    # k_max=4 matches the shipped artifact's kernel-attested certificate (from_k_max=4).
    r = mods.tlp.certify_lp(26, 10, target=886, precisions=(10 ** 14,), k_max=4)
    assert r.get("certified") is True
    assert r["floor"] == 886
    assert r["floor"] >= 384

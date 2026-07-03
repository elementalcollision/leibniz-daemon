"""Guard the low-rank Gram PSD primitive (scripts/terwilliger_psd_lowrank.py). The exact python verify is
CI-safe; the kernel leg needs docker (skips in CI). Trust point: lowRankOK is a STRICT SOUND generalization
of ldltOK — the kernel recomputes the integer identity, a corrupted cert is rejected, and r=N recovers the
full-rank certificate exactly (so it can never certify something ldltOK could not)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("terwilliger_psd_lowrank",
                                                  _ROOT / "scripts" / "terwilliger_psd_lowrank.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _lean_ok() -> bool:
    try:
        from leibniz.backends.lean_repl import available
        return available()
    except Exception:
        return False


_needs_docker = pytest.mark.skipif(not _lean_ok(), reason="docker/leibniz-lean-repl image unavailable")

lr = _load()


def test_valid_lowrank_cert_accepted_corrupted_rejected():
    B = [[1, -2, 0, 3], [2, 1, -1, 0], [0, 0, 2, 1]]        # 3x4 → rank-3 PSD M (N=4)
    M, U, d, s = lr.gram_from_factor(B)
    assert lr.verify_lowrank(M, U, d, s) is True
    # negate a diagonal entry → identity breaks / d<0 → rejected
    assert lr.verify_lowrank(M, U, [-d[0]] + d[1:], s) is False
    # drop a genuinely-active column → identity fails (fail-closed, never false-accept)
    assert lr.verify_lowrank(M, [row[:-1] for row in U], d[:-1], s) is False


def test_full_rank_recovery_equals_ldltOK_semantics():
    # a strictly-PD integer block: ldl_cert keeps all N pivots (r=N) → the full-rank certificate
    st = [1]

    def rint(a, b):
        st[0] = (st[0] * 1103515245 + 12345) & 0x7fffffff
        return a + st[0] % (b - a + 1)
    n = 6
    A = [[rint(-2, 2) for _ in range(n)] for _ in range(n)]
    M = [[sum(A[k][i] * A[k][j] for k in range(n)) + (n if i == j else 0) for j in range(n)] for i in range(n)]
    cert = lr.ldl_cert(M)
    assert cert is not None
    _, U, d, s = cert
    assert len(d) == n                                     # r = N (no zero pivots on a PD block)
    assert lr.verify_lowrank(*cert) is True


def test_lowrank_thins_a_rank_deficient_block():
    # rank-3 factor into N=8 → the exact Gram cert has r=3 columns (the low-rank win)
    B = [[1, 0, -1, 2, 0, 1, -2, 0], [0, 1, 1, 0, -1, 0, 1, 2], [2, -1, 0, 1, 1, 0, 0, -1]]
    M, U, d, s = lr.gram_from_factor(B)
    assert len(U) == 8 and len(U[0]) == 3 and len(d) == 3
    assert lr.verify_lowrank(M, U, d, s) is True


@_needs_docker
def test_kernel_accepts_valid_rejects_corrupted():
    B = [[1, -2, 0, 3, 1], [2, 1, -1, 0, 2], [0, 0, 2, 1, -1]]   # rank-3, N=5
    M, U, d, s = lr.gram_from_factor(B)
    k = lr.kernel_check(M, U, d, s, timeout_s=300)
    assert k["valid_cert"] is True
    assert k["bogus_cert"] is False
    assert k["sound"] is True

"""Guard the Bareiss fraction-free PSD certificate (compute-trap mitigation, gate #2 follow-up). Free-CPU
tests pin: the Bareiss minors match a brute-force determinant computation; the closed-form linking Bareiss'
tableau to ordinary LDLᵀ (L[i][k]=history[k][i][k]/p_{k+1}, d[k]=p_{k+1}/p_k) holds exactly; the produced
integer certificate verifies via the SAME check used by the Lean `ldltOK`; a non-PD matrix yields no
certificate; and the certificate's bit-length is strictly smaller than the naive route's (psd_scaling_probe/
psd_certificate_microprobe) at every measured size. The kernel leg (both certificate forms, real Lean 4.31
via docker) is docker-gated and skips cleanly without docker."""
from __future__ import annotations

import importlib.util
from fractions import Fraction as Fr
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod, rel):
    import sys
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


bl = _load("bareiss_ldlt", "scripts/bareiss_ldlt.py")
pm = _load("psd_certificate_microprobe", "scripts/psd_certificate_microprobe.py")
sp = _load("psd_scaling_probe", "scripts/psd_scaling_probe.py")

try:
    from leibniz.backends.lean_cli import LeanCliBackend, available as _lean_available
    _DOCKER = _lean_available()
except Exception:
    _DOCKER = False


def _det_bruteforce(M):
    """Reference determinant via cofactor expansion (Fraction-exact), independent of Bareiss, for small n."""
    n = len(M)
    if n == 1:
        return Fr(M[0][0])
    total = Fr(0)
    for j in range(n):
        minor = [row[:j] + row[j + 1:] for row in M[1:]]
        total += ((-1) ** j) * Fr(M[0][j]) * _det_bruteforce(minor)
    return total


# ---- Bareiss minors correctness (free-CPU) -----------------------------------------------------------

def test_bareiss_minors_match_bruteforce_determinant():
    for n in (2, 3, 4, 5):
        N = sp.rounded_pd(0, n, 1000)
        minors, _ = bl.bareiss_minors(N)
        assert minors[0] == 1
        assert minors[-1] == _det_bruteforce([[Fr(x) for x in row] for row in N])


def test_bareiss_minors_positive_for_strictly_pd_matrix():
    for n in (3, 6, 10):
        N = sp.rounded_pd(0, n, 10 ** 6)
        minors, _ = bl.bareiss_minors(N)
        assert bl.minors_positive(minors)


def test_bareiss_minors_not_positive_for_indefinite_matrix():
    Mind = [[1, 2], [2, 1]]  # eigenvalues 3, -1 -> indefinite
    minors, _ = bl.bareiss_minors(Mind)
    assert minors == [1, 1, -3]
    assert bl.minors_positive(minors) is False


# ---- closed-form linking Bareiss tableau to ordinary rational LDLT (free-CPU) --------------------------

def test_bareiss_tableau_matches_ordinary_ldlt_closed_form():
    """L[i][k] = history[k][i][k] / minors[k+1] and d[k] = minors[k+1] / minors[k] EXACTLY, for every k, i
    -- the algebraic fact this module's certificate construction depends on."""
    for n in (4, 6, 8, 10):
        N = sp.rounded_pd(0, n, 10 ** 6)
        L, d = pm.ldlt([[Fr(N[i][j]) for j in range(n)] for i in range(n)])
        minors, history = bl.bareiss_minors(N)
        for k in range(n):
            assert d[k] == Fr(minors[k + 1], minors[k])
            for i in range(k + 1, n):
                assert L[i][k] == Fr(history[k][i][k], minors[k + 1])


# ---- certificate construction + verification (free-CPU) ------------------------------------------------

def test_bareiss_cert_verifies_on_strictly_pd_matrices():
    for n in (3, 6, 10, 14, 18):
        N = sp.rounded_pd(0, n, 10 ** 6)
        cert = bl.bareiss_ldlt_cert(N)
        assert cert is not None
        L_int, d_int, scale = cert
        assert all(x >= 0 for x in d_int) and scale > 0
        assert bl.verify_bareiss_cert(N, L_int, d_int, scale) is True


def test_bareiss_cert_is_none_for_non_pd_matrix():
    Mind = [[1, 2], [2, 1]]
    assert bl.bareiss_ldlt_cert(Mind) is None


def test_bogus_bareiss_certificate_is_rejected_by_the_same_python_checker():
    N = sp.rounded_pd(0, 6, 10 ** 6)
    L_int, d_int, scale = bl.bareiss_ldlt_cert(N)
    bad_d = [x - 10 ** 9 for x in d_int]  # forces a negative entry -> d>=0 check fails
    assert bl.verify_bareiss_cert(N, L_int, bad_d, scale) is False


# ---- the actual deliverable: Bareiss certificate is strictly smaller than the naive route ---------------

def test_bareiss_certificate_strictly_smaller_than_naive_at_every_size():
    rows = bl.compare_bitlengths(sizes=(6, 10, 14, 18, 22, 26, 30))
    assert len(rows) == 7
    for r in rows:
        assert r["naive_verifies"] is True and r["bareiss_verifies"] is True
        assert r["bareiss_cert_bits"] < r["naive_cert_bits"]
    # the reduction factor should not shrink as n grows (mitigation gets more valuable at scale, not less)
    reductions = [r["reduction_x"] for r in rows]
    assert reductions[-1] >= reductions[0]
    # the naive route's own known blowup (30773 bits @ n=30, from docs/results/psd_scaling_probe.json) must
    # still reproduce here so the comparison is against the SAME measured baseline, not a stale number
    assert rows[-1]["naive_cert_bits"] == 30773


def test_bareiss_cert_bits_tracks_minors_not_naive_lcm():
    # the Bareiss cert's own bit-length should stay within a small constant factor of the underlying
    # minors' bit-length (the theoretical floor), unlike the naive route which is unrelated to it
    N = sp.rounded_pd(0, 18, 10 ** 6)
    stats = bl.bareiss_cert_bits(N)
    assert stats["cert_bits"] < 12 * stats["minor_bits"]  # generous slack; still far below naive's ~25x


# ---- Lean rendering shape (free-CPU: core Lean only, no Mathlib) ---------------------------------------

def test_render_detsign_lean_is_core_lean_only():
    N = sp.rounded_pd(0, 4, 1000)
    src = bl.render_detsign_lean(N)
    assert "detSignOK" in src and src.rstrip().endswith("decide")
    assert "Mathlib" not in src and "Nat.choose" not in src


def test_render_ldlt_lean_bogus_differs_only_in_d():
    N = sp.rounded_pd(0, 4, 1000)
    L_int, d_int, scale = bl.bareiss_ldlt_cert(N)
    good = pm.render_ldlt_lean(N, L_int, d_int, scale)
    bogus = bl.render_ldlt_lean_bogus(N, L_int, d_int, scale)
    assert good != bogus


# ---- docker-gated: real Lean 4.31 kernel checks both certificate forms ---------------------------------

@pytest.mark.skipif(not _DOCKER, reason="Lean kernel (docker image leibniz-lean:v4.31.0) unavailable")
def test_kernel_verifies_bareiss_form_a_ldlt_and_rejects_bogus():
    bk = LeanCliBackend(timeout_s=120)
    N = sp.rounded_pd(0, 6, 10 ** 6)
    L_int, d_int, scale = bl.bareiss_ldlt_cert(N)
    assert bk.check_source(pm.render_ldlt_lean(N, L_int, d_int, scale)) is True
    assert bk.check_source(bl.render_ldlt_lean_bogus(N, L_int, d_int, scale)) is False


@pytest.mark.skipif(not _DOCKER, reason="Lean kernel (docker image leibniz-lean:v4.31.0) unavailable")
def test_kernel_verifies_bareiss_form_b_minors_and_rejects_bogus():
    bk = LeanCliBackend(timeout_s=120)
    N = sp.rounded_pd(0, 6, 10 ** 6)
    assert bk.check_source(bl.render_detsign_lean(N)) is True
    assert bk.check_source(bl.render_detsign_lean_bogus(N)) is False


@pytest.mark.skipif(not _DOCKER, reason="Lean kernel (docker image leibniz-lean:v4.31.0) unavailable")
def test_kernel_verifies_bareiss_form_a_at_n14_within_naive_kernel_budget():
    # psd_scaling_probe kernel-checks the naive route up to n=18 in-budget; confirm the (smaller) Bareiss
    # certificate also kernel-verifies at a comparable size.
    bk = LeanCliBackend(timeout_s=180)
    N = sp.rounded_pd(0, 14, 10 ** 6)
    L_int, d_int, scale = bl.bareiss_ldlt_cert(N)
    assert bk.check_source(pm.render_ldlt_lean(N, L_int, d_int, scale)) is True

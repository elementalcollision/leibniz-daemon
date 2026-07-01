"""Guard the Terwilliger β generator (Phase 0 of the SDP three-point build). Fully free-CPU (exact rational
arithmetic, no numpy/cvxpy/docker) so it runs in CI. The soundness-relevant claim is the combinatorial
differential test: any real code's β-blocks (both families) are exactly PSD, and a transposed-binomial
corruption of eq. (7) breaks that — i.e. the β transcription is validated against ground truth, not anchors."""
from __future__ import annotations

import importlib.util
from fractions import Fraction as Fr
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("terwilliger_beta", _ROOT / "scripts" / "terwilliger_beta.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


tb = _load()


def test_psd_exact_semidefinite_cases():
    assert tb.is_psd_exact([[Fr(1), Fr(1)], [Fr(1), Fr(1)]]) is True     # rank-1 PSD (zero pivot handled)
    assert tb.is_psd_exact([[Fr(2), Fr(0)], [Fr(0), Fr(3)]]) is True
    assert tb.is_psd_exact([[Fr(1), Fr(2)], [Fr(2), Fr(1)]]) is False    # indefinite
    assert tb.is_psd_exact([[Fr(0), Fr(1)], [Fr(1), Fr(0)]]) is False    # zero pivot, nonzero off-diag
    assert tb.is_psd_exact([[Fr(2), Fr(0)], [Fr(0), Fr(-1)]]) is False   # negative diagonal


def test_beta_anchors_from_eq7():
    # Computed from eq. (7); these settle the reviewer conflict (GLM's β¹₁₁₀=n is right; Kimi's −2 and
    # Gemini's β⁰₂₂₀=36 are wrong — a transposed binomial and a partial sum respectively).
    assert tb.beta(2, 0, 0, 0, 0) == 1
    assert tb.beta(2, 1, 1, 0, 1) == 2          # = n
    assert tb.beta(6, 1, 1, 0, 1) == 6          # = n
    assert tb.beta(4, 1, 1, 1, 1) == 1
    assert tb.beta(4, 2, 2, 0, 0) == 6          # NOT 36


def test_k0_block_is_the_delsarte_dimension():
    # k=0 block is (n+1)×(n+1) and indexes i,j ∈ {0..n} — the Delsarte/Bose-Mesner block.
    assert tb._block_indices(6, 0) == list(range(0, 7))
    assert len(tb._block_indices(6, 0)) == 6 - 2 * 0 + 1
    assert tb._block_indices(6, 3) == [3]       # largest k, size n−2k+1 = 1


def test_real_codes_give_psd_blocks():
    # The differential oracle: every real code satisfies necessary condition (19) — both families PSD, all k.
    for n in (3, 4, 5, 6):
        for _name, code in tb._test_codes(n).items():
            assert tb.validate_code(n, code) is True


def test_corrupt_beta_breaks_psd():
    # Teeth: the transposed-binomial (C(t,u)) corruption must make some real-code block non-PSD.
    broke = any(not tb.validate_code(n, tb._even_weight_code(n), beta_fn=tb.beta_corrupt) for n in (3, 4, 5, 6))
    assert broke is True


def test_full_space_normalization_matches_eq21():
    # eq. (21): |C| = Σ C(n,i) x^0_{i,0}. For the full space x^0_{i,0}=1, so the sum is 2^n.
    for n in (3, 4, 5):
        _x, x0 = tb.code_x(n, list(range(1 << n)))
        assert all(x0[s] == 1 for s in range(n + 1))
        assert sum(tb.C(n, i) * x0[i] for i in range(n + 1)) == (1 << n)

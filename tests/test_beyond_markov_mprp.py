"""Guard T8-c — the Minimal Positive Realization separation (scripts/beyond_markov_mprp.py). CI-safe: the
exact-rational legs (the fooling-set certificate, the necklace-chain process audit, and the corrupted-control
predicates) run everywhere; the real-Lean-kernel leg is docker-gated and CI-skips. No trust surface touched."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("beyond_markov_mprp", _ROOT / "scripts" / "beyond_markov_mprp.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _lean_available() -> bool:
    try:
        from leibniz.backends.lean_cli import available
        return bool(available())
    except Exception:
        return False


def test_matrix_certificate_separation():
    m = _load()
    mc = m.matrix_cert()
    assert mc["rank_le3_dependency"] is True and mc["minor3_det"] == -1 and mc["rank_ge3"] is True
    assert mc["rank"] == 3                              # rank exactly 3 (dependency + nonzero 3×3 minor)
    assert mc["fooling_valid"] is True and mc["nonneg_rank_ge"] == 4   # nonneg-rank ≥ 4
    assert mc["separation"] is True                    # 4 > 3: certified positive-realization > linear gap


def test_process_is_a_valid_stationary_rational_chain():
    m = _load()
    pa = m.process_audit(Lmax=2)
    assert pa["stationary"] is True                    # πA = π
    assert pa["h2_scaled_is_M"] is True                # 8·H2 = M (length-2 Hankel block)
    assert pa["consistency"] is True                   # Σ_x P(ux) = P(u)
    assert pa["hankel_rank_stable_3"] is True and set(pa["hankel_ranks"].values()) == {3}
    assert pa["ok"] is True


def test_fooling_predicate_is_load_bearing():
    m = _load()
    # Fill a structural zero: the fooling predicate breaks AND the whole certificate collapses.
    bad = [r[:] for r in m.M4]
    bad[0][2] = 1
    assert m.fooling_ok(bad, m.FS_ROWS, m.FS_COLS) is False          # cross-product M[0,2]·M[1,0]=1≠0
    assert m.dep_ok(m.DEP, bad) is False                            # the rank-≤3 dependency is broken
    assert m.matrix_cert(bad)["separation"] is False               # no certified separation survives
    # All-ones J: a bogus size-4 fooling claim must be rejected.
    J = [[1, 1, 1, 1] for _ in range(4)]
    assert m.fooling_ok(J, m.FS_ROWS, m.FS_COLS) is False


def test_hmm_bridge_direction_sanity():
    # An explicit 4-term nonnegative factorization of M exists (columns × standard covectors) => nonneg-rank ≤ 4.
    m = _load()
    M = m.M4
    # M = sum_j col_j ⊗ e_j : reconstruct and compare
    recon = [[sum((M[i][j] if jj == j else 0) for j in range(4)) for jj in range(4)] for i in range(4)]
    assert recon == M                                  # trivial nonneg factorization, inner dim 4 (upper bound)


@pytest.mark.skipif(not _lean_available(), reason="Lean/docker unavailable; kernel leg is operator-local")
def test_kernel_certifies_separation_and_rejects_controls():
    m = _load()
    from leibniz.backends.lean_cli import LeanCliBackend
    bk = LeanCliBackend(timeout_s=120)
    assert bk.check_source(m.render_lean(m.M4, m._sub3(m.M4))) is True
    assert bk.check_source(m.render_control_fill()) is False        # filled zero -> rejected
    assert bk.check_source(m.render_control_allones()) is False     # all-ones bogus fooling -> rejected

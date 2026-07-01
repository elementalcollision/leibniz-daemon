"""Guard the Phase 1 mechanical dual (scripts/terwilliger_dual.py). Fully free-CPU (exact rational; no
solver/docker) so it runs in CI. The soundness-relevant claims: (1) the collected dual EXACTLY reproduces the
Lagrangian for all random points [emitter-consistency, no hand-derived sign survives]; (2) weak duality
c·x ≤ L holds for primal-feasible x and dual-feasible duals [sign-validity]; both with corrupt-controls that
must break; (3) the k=0 objective variables are exactly the Delsarte inner-distribution weights."""
from __future__ import annotations

import importlib.util
from fractions import Fraction as Fr
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("terwilliger_dual", _ROOT / "scripts" / "terwilliger_dual.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


td = _load()
CELLS = [(4, 2), (5, 2), (6, 2), (6, 4), (7, 4)]


def test_lagrangian_identity_holds_and_corruption_breaks_it():
    for (n, d) in CELLS:
        assert td.identity_holds(n, d) is True              # collected == Lagrangian for all random points
        assert td.identity_holds(n, d, corrupt=True) is False   # one flipped β sign is caught


def test_weak_duality_holds_and_corruption_breaks_it():
    for (n, d) in CELLS:
        assert td.weak_duality_holds(n, d) is True          # c·x ≤ L for feasible x, feasible duals
        assert td.corruption_detected_wd(n, d) is True      # a flipped α-sign breaks weak duality


def test_objective_variables_are_delsarte_weights():
    # A(6,4): even d, so weights are {0} ∪ {even i ≥ 4} = {0,4,6}.
    got = [k[1] for k in td.delsarte_objective_keys(6, 4)]
    assert got == [0, 4, 6]
    # A(5,2): even d=2 ⇒ even weights {0,2,4}.
    assert [k[1] for k in td.delsarte_objective_keys(5, 2)] == [0, 2, 4]


def test_block_sizes_match_terwilliger_reduction():
    # p_k = n − 2k + 1; largest block is the k=0 (n+1)×(n+1) — the dimension-wall escape.
    for (n, _d) in CELLS:
        blocks = [len(td.block_idx(n, k)) for k in range(n // 2 + 1)]
        assert blocks == [n - 2 * k + 1 for k in range(n // 2 + 1)]
        assert max(blocks) == n + 1


def test_dual_check_flags_nonstationary_and_counts_residuals():
    # All-zero duals: the objective coefficients survive as nonzero stationarity residuals ⇒ NOT feasible,
    # bound 0; zero matrices are PSD and zero multipliers are ≥0, so only the residuals fail.
    n, d = 5, 2
    res = td.dual_check(n, d, td._zero_duals(n, d))
    assert res["feasible"] is False
    assert res["psd_ok"] is True and res["nonneg_ok"] is True
    assert res["n_residuals_nonzero"] == len(td.delsarte_objective_keys(n, d))   # exactly the objective vars
    assert res["bound"] == 0


def test_xass_from_real_code_is_primal_feasible_shape():
    # Repetition code {0, 1^n} at n=4,d=2: x^0_{0,0}=1 and the distance-n variable x^0_{4,0} (key (0,4,4)) > 0.
    xass = td.xass_from_code(4, 2, [0, 0b1111])
    assert xass[(0, 0, 0)] == 1
    assert xass[(0, 4, 4)] > 0
    assert all(isinstance(v, Fr) for v in xass.values())

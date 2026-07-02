"""Guard F1 whole-certificate-in-kernel (scripts/terwilliger_kernel_full.py, task #100). The kernel checks
EVERY certificate obligation (beta vs eq.(7), stationarity from collected(), multiplier validity + nonneg,
the floored bound, PSD on the same literals) — one theorem per obligation, decide only. Solve legs need
cvxpy, kernel legs docker (operator-local; CI skips). The A(19,6) exit run + its four corrupted controls
live in the script's main() and docs/results/terwilliger_kernel_full.json."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_HAS = importlib.util.find_spec("cvxpy") is not None and importlib.util.find_spec("numpy") is not None
_needs = pytest.mark.skipif(not _HAS, reason="cvxpy/numpy are operator-local; solve legs skipped in CI")


def _load():
    spec = importlib.util.spec_from_file_location("terwilliger_kernel_full",
                                                  _ROOT / "scripts" / "terwilliger_kernel_full.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _lean_ok() -> bool:
    try:
        from leibniz.backends.lean_cli import available
        return available()
    except Exception:
        return False


_needs_docker = pytest.mark.skipif(not _lean_ok(), reason="docker/leibniz-lean image unavailable")

kf = _load()


def test_dense_beta_is_raw_eq7_over_the_full_domain():
    # the table carries eq.(7) verbatim INCLUDING impossible triples (the stationarity fold owns the
    # possible() guard, exactly like collected()) — so sliceOK pins table == eq.(7) with no carve-outs
    B = kf.dense_beta(6, 1)
    idx = kf.td.block_idx(6, 1)
    for a, i in enumerate(idx):
        for b, j in enumerate(idx):
            for t in range(min(i, j) + 1):
                assert B[a][b][t] == kf.td.beta(6, i, j, 1, t)


def test_corruption_modes_mutate_exactly_one_thing():
    b0 = [[[10 * a + b] for b in range(3)] for a in range(3)]                    # 3x3, one t-entry each
    data = {"B": [b0], "mult": {"a": [(0, 2, 2, 7)], "b1": [], "g": [(1, 3, 3, 9)]},
            "gsum": 9, "target": 8, "d": 2, "D": 5}
    d2, _ = kf.corrupt(data, [], "beta_entry")
    assert d2["B"][0][2][2][0] == data["B"][0][2][2][0] + 1
    d2, _ = kf.corrupt(data, [], "stationarity")
    assert d2["mult"]["g"][0][3] == 10 and d2["gsum"] == 10
    d2, _ = kf.corrupt(data, [], "negative_mult")
    assert d2["mult"]["a"][-1][3] == -5
    d2, _ = kf.corrupt(data, [], "bound_claim")
    assert d2["target"] == 7 and data["target"] == 8


@_needs
def test_build_data_single_denominator_and_preflight():
    tel = kf._load("terwilliger_exact_lp", "scripts/terwilliger_exact_lp.py")
    row = tel.certify_lp(4, 2, target=8, return_duals=True)
    assert row["certified"]
    data = kf.build_data(4, 2, row["duals"], 8)
    assert data["D"] > 0
    # the free-CPU mirror of the kernel obligations must agree with dual_check on the integerized cert
    assert kf.python_check(data)["feasible"] is True


@_needs
@_needs_docker
def test_kernel_full_a4_2_all_obligations_true():
    r = kf.kernel_full(4, 2, 8)
    assert isinstance(r, tuple)
    out = r[0]
    assert out["kernel_valid"] is True and out["preflight_feasible"] is True
    assert out["n_keys"] == 5 and out["n_beta_entries"] == 81


@_needs
@_needs_docker
@pytest.mark.parametrize("mode", kf.CONTROLS)
def test_kernel_full_a4_2_corrupted_controls_all_false(mode):
    from leibniz.backends.lean_cli import LeanCliBackend
    r = kf.kernel_full(4, 2, 8)
    assert isinstance(r, tuple)
    _, data, blocks, _ = r
    d2, b2 = kf.corrupt(data, blocks, mode)
    assert LeanCliBackend(timeout_s=600).check_source(kf.render(d2, b2)) is False

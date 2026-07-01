"""Guard the irrationality-margin test (revised SDP gate). The odd-cycle data is free-CPU; the SDP + margin
run needs cvxpy + numpy (operator-local, like ortools) and is gated. The kernel leg is docker-gated (in the
probe main())."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_HAS = importlib.util.find_spec("cvxpy") is not None and importlib.util.find_spec("numpy") is not None
_needs = pytest.mark.skipif(not _HAS, reason="cvxpy/numpy are operator-local; SDP margin test skipped in CI")


def _load(mod, rel):
    import sys
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


im = _load("irrationality_margin_test", "scripts/irrationality_margin_test.py")


def test_odd_cycle_data():
    n, edges, alpha, theta = im.odd_cycle(5)
    assert n == 5 and alpha == 2 and len(edges) == 5
    assert abs(theta - 5 ** 0.5) < 1e-9        # ϑ(C5) = √5, irrational


@_needs
def test_c5_certifies_alpha_with_small_tax():
    n, edges, alpha, theta = im.odd_cycle(5)
    row = im.run_cell(n, edges, alpha, theta, kernel=None)
    assert row["floors_to_alpha"] is True          # rational cert floors to α=2 despite ϑ=√5 irrational
    assert row["achievable_tax"] < 0.01            # the irrationality tax is small (wall surmountable)
    assert row["cert_bound"] >= theta              # sound: the certified bound is a valid upper bound on ϑ

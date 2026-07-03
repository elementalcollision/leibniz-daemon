"""Guard the decide-scaling probe (scripts/terwilliger_decide_probe.py). The source generators are CI-safe;
the kernel timing needs docker (skips in CI). The recorded finding: decide cost is ~O(term^2), so the
flat/proof-term PSD encoding is worse than the compact List-def form and the ~N=60 kernel-PSD ceiling is a
trust-model boundary, not an engineering gap."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("terwilliger_decide_probe",
                                                  _ROOT / "scripts" / "terwilliger_decide_probe.py")
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

p = _load()


def test_big_sum_generators_are_valid_true_theorems():
    # both encodings assert a TRUE arithmetic fact (the sum equals its value) — so a timeout is cost, not
    # falsehood; and the theorem is well-formed Lean
    for nat in (False, True):
        src = p.big_sum(50, nat=nat)
        assert "by decide" in src and ("Nat" if nat else "Int") in src
        assert src.count("*") == 50                            # K products


@_needs_docker
def test_probe_mechanism_kernel_verifies_a_small_flat_sum():
    # robust, fast guard of the harness: a small flat-sum theorem is a TRUE fact the kernel confirms.
    # (The superlinear O(term^2) finding is a wall-clock MEASUREMENT recorded in the results doc / JSON —
    # not asserted here, since timing ratios flake on container warmth.)
    from leibniz.backends.lean_repl import LeanReplBackend
    bk = LeanReplBackend(timeout_s=60)
    assert p._run(bk, p.big_sum(100, nat=False)) is True
    assert p._run(bk, p.big_sum(100, nat=True)) is True

"""Kernel smoke test for the soundness-critical render→kernel paths (docker-gated).

The amplification render→kernel paths (render_cwc_lean / render_covering_lean → the Lean 4.31 kernel) are
the load-bearing checks behind every audit-tier verdict, but they were exercised only by scripts run by
hand — CI (no docker) cannot run them. This committed smoke test runs them when docker + the Lean image
are present (the kernel-nightly lane / scripts/run_kernel_tests.sh), and SKIPS cleanly otherwise. It pins
both directions: a valid witness is KERNEL-VERIFIED, and a FALSE theorem is kernel-REJECTED (the kernel,
not just the untrusted pre-check, is the backstop).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent

try:
    from leibniz.backends.lean_cli import LeanCliBackend, available
    _OK = available()
except Exception:
    _OK = False

pytestmark = pytest.mark.skipif(not _OK, reason="Lean kernel (docker image) unavailable")


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# --- CWC render → kernel ------------------------------------------------------------------------
def test_cwc_valid_witness_is_kernel_verified():
    cli = _load("cwc_check_smoke", "scripts/cwc_check.py")
    fano = [(0, 1, 2), (0, 3, 4), (0, 5, 6), (1, 3, 5), (1, 4, 6), (2, 3, 6), (2, 4, 5)]
    r = cli.check(7, 4, 3, fano, run_kernel=True)
    assert r["kernel"] == "KERNEL-VERIFIED" and r["size"] == 7


def test_cwc_false_theorem_is_kernel_rejected():
    pb = _load("pb_smoke", "scripts/probe_beta_cwc_pilot.py")
    # build a deliberately FALSE validCWC theorem: two weight-3 words at distance 2 < d=4 claimed valid
    src = (pb._LEAN_HELPERS + "\n\ntheorem cwc_false :\n"
           "    validCWC [[0, 1, 2], [0, 1, 3]] 7 4 3 2 = true := by\n  decide\n")
    assert LeanCliBackend().check_source(src) is False


# --- covering render → kernel -------------------------------------------------------------------
def test_covering_valid_witness_is_kernel_verified():
    cli = _load("covering_check_smoke", "scripts/covering_check.py")
    sts9 = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (1, 5, 6), (2, 3, 7), (0, 5, 7), (1, 3, 8), (2, 4, 6)]
    r = cli.check(9, 3, 2, sts9, run_kernel=True)
    assert r["kernel"] == "KERNEL-VERIFIED" and r["size"] == 12


def test_covering_false_theorem_is_kernel_rejected():
    cv = _load("covering_verify_smoke", "scripts/covering_verify.py")
    # STS(9) minus one block, claimed as an 11-block covering: a pair is uncovered -> validCovering false
    bad = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8],
           [0, 4, 8], [1, 5, 6], [2, 3, 7], [0, 5, 7], [1, 3, 8]]
    lits = "[" + ", ".join("[" + ", ".join(map(str, b)) + "]" for b in bad) + "]"
    src = (cv._LEAN_HELPERS + "\n\ntheorem cov_false :\n"
           f"    validCovering {lits} 9 3 2 11 = true := by\n  decide\n")
    assert LeanCliBackend().check_source(src) is False

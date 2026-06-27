"""Probe β pilot — guard the constant-weight-code verifier (the trust-critical re-check).

This Python verifier is the stand-in for the eventual Lean kernel witness-check; if it is wrong,
every "matched/beat the record" claim is wrong. So pin it hard: it accepts a real design (Fano /
STS(7) = A(7,4,3)=7) and rejects the exact failure modes (too-close pair, wrong weight, duplicate,
out-of-range symbol). The search is untrusted and only needs to be checked by the verifier.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "probe_beta", Path(__file__).resolve().parent.parent / "scripts" / "probe_beta_cwc_pilot.py")
pb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pb)

# Fano plane / STS(7): 7 triples on {0..6}, pairwise intersecting in exactly 1 point => distance 4.
FANO = [frozenset(b) for b in
        [(0, 1, 2), (0, 3, 4), (0, 5, 6), (1, 3, 5), (1, 4, 6), (2, 3, 6), (2, 4, 5)]]


def test_fano_is_a_valid_7_4_3_code():
    ok, reason = pb.verify_cwc(FANO, n=7, d=4, w=3)
    assert ok, reason
    assert len(FANO) == 7


def test_rejects_too_close_pair():
    # two weight-3 words sharing 2 elements => distance 2(3-2)=2 < 4
    code = [frozenset({0, 1, 2}), frozenset({0, 1, 3})]
    ok, reason = pb.verify_cwc(code, n=4, d=4, w=3)
    assert not ok and "distance 2" in reason


def test_rejects_wrong_weight():
    ok, _ = pb.verify_cwc([frozenset({0, 1})], n=5, d=4, w=3)
    assert not ok


def test_rejects_out_of_range_symbol():
    ok, _ = pb.verify_cwc([frozenset({0, 1, 9})], n=5, d=4, w=3)
    assert not ok


def test_rejects_duplicates():
    ok, reason = pb.verify_cwc([frozenset({0, 1, 2}), frozenset({0, 1, 2})], n=5, d=4, w=3)
    assert not ok and "duplicate" in reason


def test_distance_threshold_is_exact():
    # disjoint triples on 6 points: distance 6 >= d for d up to 6
    code = [frozenset({0, 1, 2}), frozenset({3, 4, 5})]
    assert pb.verify_cwc(code, n=6, d=6, w=3)[0] is True
    # but they fail d=7 (max distance between two weight-3 words is 6)
    assert pb.verify_cwc(code, n=6, d=7, w=3)[0] is False


def test_search_reaches_known_optima_and_is_verified():
    # the trust-critical contract: whatever search returns, the verifier validates it
    for (n, d, w), (best, _prov) in pb.ORACLE.items():
        code = pb.search_cwc(n, d, w, best)
        ok, reason = pb.verify_cwc(code, n, d, w)
        assert ok, f"A({n},{d},{w}): search returned an INVALID code: {reason}"
        assert len(code) >= best, f"A({n},{d},{w}): only reached {len(code)}/{best}"


def test_search_is_deterministic():
    a = pb.search_cwc(7, 4, 3, 7)
    b = pb.search_cwc(7, 4, 3, 7)
    assert {frozenset(c) for c in a} == {frozenset(c) for c in b}   # seeded LCG => reproducible

"""Guard the covering-design audit assets (ADR 0043, Track B1) — the 2nd amplification domain.

Mirrors test_cwc_check: the verifier must (1) accept a valid covering and reject an incomplete one,
(2) refuse to render a false theorem, (3) report the right novelty verdict from the AUTOMATED LJCR
oracle (improvement = STRICTLY FEWER blocks), and (4) never promulgate. Kernel-free (no docker) so it
runs in CI — the real kernel re-check is exercised by the live B1 demo run / the committed corpus.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


cv = _load("covering_verify", "scripts/covering_verify.py")
ora = _load("covering_table_oracle", "scripts/covering_table_oracle.py")
cli = _load("covering_check", "scripts/covering_check.py")

# STS(9): the 12 lines of AG(2,3) — an optimal C(9,3,2) covering (every pair in exactly one triple).
STS9 = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (1, 5, 6), (2, 3, 7), (0, 5, 7), (1, 3, 8), (2, 4, 6)]


def test_verify_accepts_valid_covering():
    ok, reason = cv.verify_covering([frozenset(b) for b in STS9], 9, 3, 2)
    assert ok, reason


def test_verify_rejects_incomplete_covering():
    ok, reason = cv.verify_covering([frozenset(b) for b in STS9[:-1]], 9, 3, 2)  # drop a block
    assert not ok and "not covered" in reason


def test_verify_rejects_bad_block():
    bad = STS9[:-1] + [(0, 1, 9)]  # 9 not in [0,9)
    ok, reason = cv.verify_covering([frozenset(b) for b in bad], 9, 3, 2)
    assert not ok and "k-subset" in reason


def test_render_refuses_false_theorem():
    import pytest
    with pytest.raises(ValueError):
        cv.render_covering_lean(9, 3, 2, STS9[:-1])  # incomplete -> must refuse


def test_render_emits_decidable_theorem():
    src = cv.render_covering_lean(9, 3, 2, STS9)
    assert "validCovering" in src and "cov_9_3_2_le_12" in src and ":= by\n  decide" in src
    # completeness-by-construction: the checker GENERATES the t-subsets (combs), never trusts the witness
    assert "combs t (List.range v)" in src


def test_oracle_records_and_improvement_direction():
    snap = ora.load_snapshot()[0]
    assert ora.best_known(9, 3, 2, snap) == 12               # matches STS(9)
    assert ora.is_improvement(9, 3, 2, 11, snap) is True     # FEWER blocks beats the record
    assert ora.is_improvement(9, 3, 2, 12, snap) is False    # equalling is not beating
    assert ora.is_improvement(9, 3, 2, 13, snap) is False    # more blocks is worse
    assert ora.is_improvement(999, 7, 4, 5, snap) is False   # untabulated -> not claimable


def test_check_no_kernel_equals_record():
    r = cli.check(9, 3, 2, STS9, run_kernel=False)
    assert r["verify_ok"] is True and r["size"] == 12
    assert r["best_known"] == 12 and "equals record" in r["novelty"]
    assert r["kernel"] == "not run (--no-kernel)"            # audit-tier; no verification claim


def test_check_invalid_witness_status():
    r = cli.check(9, 3, 2, STS9[:-1], run_kernel=False)
    assert r["verify_ok"] is False and cli._exit_status(r) == 1


def test_parse_blocks_round_trips():
    assert cli.parse_blocks("0,1,2;3,4,5") == [(0, 1, 2), (3, 4, 5)]

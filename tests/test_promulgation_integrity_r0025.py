"""ADR 0025: promulgation integrity.

Two fixes prompted by a calibration that promulgated 32 ring-decidable polynomial
identities with no stored proof:
  1. ring/nlinarith join the non-triviality decision procedures, so ring-trivial
     identities are quarantined as TRIVIAL instead of promulgated.
  2. The runtime persists `proof_src`, so a promulgated law carries its kernel-checked
     proof for audit/publication (was dropped -> the ledger showed "(none)").
"""
from __future__ import annotations

import sqlite3

import pytest

from leibniz.backends import lean_cli, lean_repl
from leibniz.propositio import Demonstratio, Enuntiatio, Expressio, Propositio
from leibniz.runtime import PersistentRuntime
from leibniz.types import ClaimType, FinishReason


# --- non-triviality bar (CI-safe: just the tactic set) -----------------------

def test_ring_class_tactics_in_both_backends():
    for tactics in (lean_cli.DEFAULT_TRIVIAL_TACTICS, lean_repl.DEFAULT_TRIVIAL_TACTICS):
        assert "ring" in tactics       # closes the polynomial identities that escaped
        assert "nlinarith" in tactics  # nonlinear-arith inequalities too


def test_backends_keep_the_triviality_set_in_sync():
    # drift here would let a statement be "trivial" under one backend but not the other.
    assert lean_cli.DEFAULT_TRIVIAL_TACTICS == lean_repl.DEFAULT_TRIVIAL_TACTICS


# --- proof persistence (CI-safe: tmp SQLite) ---------------------------------

def _proven(statement: str, proof: str) -> Propositio:
    p = Propositio(
        enuntiatio=Enuntiatio(statement=statement, claim_type=ClaimType.INVARIANT,
                              falsifiable_claim="nope"),
        expressio=Expressio(theorem_src=f"theorem t : {statement}", normalized_hash="h"),
        demonstratio=Demonstratio(proof_obligation="t", proof_src=proof,
                                  kernel_verified=True, qed="Q.E.D."),
    )
    p.finish_reason = FinishReason.PROMULGATED
    return p


def test_proof_src_round_trips(tmp_path):
    db = tmp_path / "m.db"
    with PersistentRuntime(db_path=db) as rt:
        rt.remember(_proven("a + b = b + a", "by ring"))
    with PersistentRuntime(db_path=db) as rt2:
        got = rt2.recall_recent(1)[0]
        assert got.demonstratio is not None
        assert got.demonstratio.kernel_verified is True
        assert got.demonstratio.proof_src == "by ring"  # the proof survives, not "(none)"


def test_migrates_pre_0025_db_without_proof_src(tmp_path):
    # a DB written before ADR 0025 has no proof_src column; opening it must migrate
    # (ALTER TABLE) and keep old rows readable, not crash.
    db = tmp_path / "old.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE memory (pid TEXT PRIMARY KEY, born REAL, ts REAL, statement TEXT, "
        "claim_type TEXT, falsifiable_claim TEXT, domain TEXT, theorem_src TEXT, "
        "normalized_hash TEXT, kernel_verified INTEGER, qed TEXT, finish_reason TEXT, parents TEXT)"
    )
    con.execute(
        "INSERT INTO memory (pid, born, ts, statement, claim_type, kernel_verified, qed) "
        "VALUES ('p1', 1.0, 1.0, 'legacy law', 'invariant', 1, 'Q.E.D.')"
    )
    con.commit()
    con.close()

    with PersistentRuntime(db_path=db) as rt:
        recalled = {p.pid: p for p in rt.recall_recent(10)}
        assert "p1" in recalled                                   # legacy row survives migration
        assert recalled["p1"].demonstratio.proof_src is None      # no proof was stored back then
        rt.remember(_proven("new law", "by nlinarith"))           # new writes carry the proof
    with PersistentRuntime(db_path=db) as rt2:
        by_stmt = {p.enuntiatio.statement: p for p in rt2.recall_recent(10)}
        assert by_stmt["new law"].demonstratio.proof_src == "by nlinarith"


# --- the exact escaped pattern, end-to-end through the real kernel (gated) ----

@pytest.mark.skipif(not lean_repl.available(), reason="lean REPL image not available")
def test_ring_trivial_identity_is_now_flagged_trivial():
    be = lean_repl.LeanReplBackend()
    # (m+3)(m+5)+1 = (m+4)^2 — a ring-closable identity of exactly the kind the
    # pre-0025 gate promulgated. It must now read as TRIVIAL.
    expr = Expressio(theorem_src="theorem t (m : Nat) : (m + 3) * (m + 5) + 1 = (m + 4)^2",
                     imports=("Mathlib.Tactic",))
    try:
        assert be.closed_by_decision_procedure(expr) is True
    finally:
        be.close()

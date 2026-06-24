"""ADR 0033 Slice 1: instance-tag + write-barrier on the runtime ledger.

A UAT run must never write the PROD ledger. Each candidate row is stamped with its instance,
and a PersistentRuntime refuses to open a DB already claimed by a DIFFERENT tagged instance
(fail closed). Legacy untagged rows (pre-ADR-0033) are exempt. CI-safe, pure SQLite — and
deliberately NOT in test_invariants.py, which stays byte-identical (the trust floor is frozen;
this is additive isolation, not a trust-edge change).
"""
from __future__ import annotations

import sqlite3

import pytest

from leibniz.propositio import Enuntiatio, Propositio
from leibniz.runtime import PersistentRuntime
from leibniz.types import ClaimType


def _prop(stmt: str = "s") -> Propositio:
    return Propositio(enuntiatio=Enuntiatio(
        statement=stmt, claim_type=ClaimType.INVARIANT, falsifiable_claim="f"))


def test_instance_defaults_to_dev_and_honors_env(monkeypatch):
    monkeypatch.delenv("LEIBNIZ_INSTANCE", raising=False)
    assert PersistentRuntime(db_path=":memory:").instance == "dev"
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "UAT")
    assert PersistentRuntime(db_path=":memory:").instance == "uat"   # normalized


def test_remember_stamps_the_instance(monkeypatch, tmp_path):
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "prod")
    rt = PersistentRuntime(db_path=str(tmp_path / "m.db"))
    rt.remember(_prop())
    rows = rt._db().execute("SELECT instance FROM memory").fetchall()
    rt.close()
    assert rows and all(r[0] == "prod" for r in rows)


def test_write_barrier_refuses_a_cross_instance_ledger(monkeypatch, tmp_path):
    db = str(tmp_path / "m.db")
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "prod")
    p = PersistentRuntime(db_path=db)
    p.remember(_prop("claimed-by-prod"))
    p.close()
    # a UAT runtime pointed at the SAME db must fail closed
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "uat")
    u = PersistentRuntime(db_path=db)
    with pytest.raises(RuntimeError, match="write-barrier"):
        u.remember(_prop("would-contaminate-prod"))


def test_same_instance_can_reopen(monkeypatch, tmp_path):
    db = str(tmp_path / "m.db")
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "prod")
    PersistentRuntime(db_path=db).remember(_prop("a"))
    p2 = PersistentRuntime(db_path=db)        # same instance -> allowed
    p2.remember(_prop("b"))
    assert len(p2.recall_recent(10)) == 2
    p2.close()


def test_legacy_untagged_db_is_exempt(monkeypatch, tmp_path):
    # a pre-ADR-0033 DB (no `instance` column / NULL rows) must remain openable by any instance
    db = str(tmp_path / "legacy.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE memory (pid TEXT PRIMARY KEY, born REAL, ts REAL, statement TEXT, "
                "claim_type TEXT, falsifiable_claim TEXT, domain TEXT, theorem_src TEXT, "
                "normalized_hash TEXT, kernel_verified INTEGER, qed TEXT, proof_src TEXT, "
                "finish_reason TEXT, parents TEXT)")
    con.execute("INSERT INTO memory (pid, claim_type) VALUES ('legacy', 'invariant')")
    con.commit()
    con.close()
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "uat")
    rt = PersistentRuntime(db_path=db)
    rt.remember(_prop("new"))                 # migration adds the column; NULL legacy row exempt
    insts = {r[0] for r in rt._db().execute("SELECT instance FROM memory").fetchall()}
    rt.close()
    assert insts == {None, "uat"}             # legacy stays NULL; the new row is tagged

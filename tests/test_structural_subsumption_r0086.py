"""ADR 0086 — persist claim_domain, and detect subsumption STRUCTURALLY.

An earlier attempt asked Z3 whether a held law's property IMPLIES a candidate's. That is vacuous
between theorems: every held law is true on its domain, so `not(candidate)` is unsatisfiable on
its own and the premise contributes nothing. It flagged 10 of 29 held laws — including the
strongest — on the strength of nothing. These tests pin the syntactic replacement, and the
vacuity that motivated it.
"""
from __future__ import annotations

import sqlite3

from leibniz.structural import subsumes

BOX = "a >= 0 and b >= 0"
HELD = ("(max(a,b) - min(a,b)) * (a + b) == max(a,b)^2 - min(a,b)^2 "
        "and max(a,b) * min(a,b) == a*b")
CONJUNCT = "(max(a,b) - min(a,b)) * (a + b) == max(a,b)^2 - min(a,b)^2"
COMMUTED = "max(a,b)^2 - min(a,b)^2 == (max(a,b) - min(a,b)) * (a + b)"


def test_a_conjunct_of_a_held_law_is_subsumed():
    assert subsumes(BOX, HELD, BOX, CONJUNCT) is True


def test_the_commuted_spelling_is_still_caught():
    """THE observed case: the daemon wrote the same equality the other way round. Without
    commutative normalisation the check misses exactly what it exists for."""
    assert subsumes(BOX, HELD, BOX, COMMUTED) is True


def test_subsumption_is_asymmetric():
    assert subsumes(BOX, CONJUNCT, BOX, HELD) is False      # the stronger law is not redundant


def test_an_unrelated_law_is_never_flagged():
    assert subsumes(BOX, HELD, BOX, "(a^2 + b^2) % 4 != 3") is False


def test_identical_claims_are_not_this_checks_job():
    assert subsumes(BOX, HELD, BOX, HELD) is False          # contains_equivalent handles those


def test_a_different_domain_blocks_subsumption():
    """Nothing is assumed about domains that were never compared — the flaw in the first draft,
    where CorpusEntry had no claim_domain and the held law's was silently assumed equal."""
    assert subsumes(BOX, HELD, "a >= 5 and b >= 0", CONJUNCT) is False
    assert subsumes(BOX, HELD, None, CONJUNCT) is False


def test_an_extra_conjunct_defeats_subsumption():
    assert subsumes(BOX, HELD, BOX, CONJUNCT + " and a + b >= 1") is False


def test_unparseable_or_empty_input_is_never_a_match():
    for bad in ("", None, "while True: pass", "(((("):
        assert subsumes(BOX, HELD, BOX, bad) is False
        assert subsumes(BOX, bad, BOX, CONJUNCT) is False


def test_claim_domain_is_persisted_and_migrates(tmp_path):
    """A pre-ADR-0086 database must gain the column without losing rows."""
    from leibniz.runtime import PersistentRuntime
    db = str(tmp_path / "m.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE memory (pid TEXT PRIMARY KEY, born REAL, ts REAL, statement TEXT, "
                "claim_type TEXT, falsifiable_claim TEXT, domain TEXT, theorem_src TEXT, "
                "normalized_hash TEXT, kernel_verified INTEGER, qed TEXT, proof_src TEXT, "
                "finish_reason TEXT, parents TEXT, instance TEXT, claim_property TEXT, "
                "seed_origin TEXT)")   # the exact pre-ADR-0086 schema
    con.execute("INSERT INTO memory (pid, born) VALUES ('old', 1.0)")
    con.commit()
    con.close()
    PersistentRuntime(db_path=db)._db()   # the connection is lazy; migration runs on first use
    con = sqlite3.connect(db)
    cols = {r[1] for r in con.execute("PRAGMA table_info(memory)")}
    rows = con.execute("SELECT count(*) FROM memory").fetchone()[0]
    con.close()
    assert "claim_domain" in cols and rows == 1


def test_the_real_ledger_pair_is_caught():
    """The live case that motivated this: f73da540 is a commuted conjunct of 5cad1e53."""
    try:
        con = sqlite3.connect("file:/Users/dave/Claude_Primary/leibniz/.leibniz/memory.db?mode=ro",
                              uri=True)
        q = "SELECT claim_property FROM memory WHERE pid=?"
        held = con.execute(q, ("5cad1e53eb1d",)).fetchone()
        cand = con.execute(q, ("f73da540a8c7",)).fetchone()
        con.close()
    except Exception:
        import pytest
        pytest.skip("live ledger unavailable")
    if not (held and cand):
        import pytest
        pytest.skip("ledger rows absent")
    assert subsumes(BOX, held[0], BOX, cand[0]) is True

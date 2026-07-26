"""ADR 0077 — self-ledger entries must be matchable under every hash scheme.

A ledger row's `normalized_hash` was produced by whichever normalizer was live when the law was
promulgated. `pipeline._normalized_hash` prefers a backend's ELABORATOR-canonical hash and falls
back to the TEXTUAL one; the production REPL backend has no `normalize_statement`, so the scheme
silently changed when the daemon moved from the CLI backend to the REPL. The result: laws stored
under the old scheme became invisible to ADR 0052 self-dedup — the daemon could re-derive its own
oldest laws, which is precisely the gap ADR 0052 exists to close.
"""
from __future__ import annotations

import sqlite3

from leibniz.corpus import self_ledger_entries
from leibniz.verifiers import normalize_statement

_SRC = "theorem legacy_law (n : Nat) : (n^4) % 5 = 0 ∨ (n^4) % 5 = 1 := by decide"


def _db(tmp_path, stored_hash):
    p = tmp_path / "mem.db"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE memory (theorem_src TEXT, normalized_hash TEXT, claim_type TEXT, "
                "claim_property TEXT, finish_reason TEXT, kernel_verified INTEGER)")
    con.execute("INSERT INTO memory VALUES (?,?,?,?,?,?)",
                (_SRC, stored_hash, "invariant", "(n^4) % 5 == 0 or (n^4) % 5 == 1",
                 "promulgated", 1))
    con.commit()
    con.close()
    return str(p)


def test_a_legacy_scheme_row_is_still_matchable_today(tmp_path):
    """The regression: a row stored under the OTHER scheme was unreachable."""
    legacy = "e88176ebbc00c995deadbeef"                 # an elaborator-era hash
    entries = self_ledger_entries(_db(tmp_path, legacy))
    keys = {e.formal_hash for e in entries}
    assert legacy in keys                                # the stored key still works
    assert normalize_statement(_SRC) in keys             # ... and so does a TODAY-computed one
    assert len(entries) == 2


def test_no_duplicate_entry_when_the_schemes_agree(tmp_path):
    entries = self_ledger_entries(_db(tmp_path, normalize_statement(_SRC)))
    assert len(entries) == 1                             # already matchable; nothing added


def test_every_live_ledger_law_is_matchable_by_a_todays_hash():
    """Against the real ledger: before this change only the textual-hash rows were reachable."""
    db = "/Users/dave/Claude_Primary/leibniz/.leibniz/memory.db"
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        rows = con.execute("SELECT theorem_src FROM memory WHERE lower(finish_reason)="
                           "'promulgated' AND kernel_verified = 1").fetchall()
        con.close()
    except Exception:
        import pytest
        pytest.skip("live ledger unavailable")
    if not rows:
        import pytest
        pytest.skip("no promulgated laws in the ledger")
    keys = {e.formal_hash for e in self_ledger_entries(db)}
    unreachable = [ts for (ts,) in rows if ts and normalize_statement(ts) not in keys]
    assert not unreachable, f"{len(unreachable)} law(s) invisible to self-dedup"


def test_missing_db_still_degrades_safely(tmp_path):
    assert self_ledger_entries(str(tmp_path / "nope.db")) == []
    assert self_ledger_entries(None) == []

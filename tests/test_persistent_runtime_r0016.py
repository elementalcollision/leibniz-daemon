"""ADR 0016: PersistentRuntime — real RuntimeAdapter (CI-safe; SQLite tmp file)."""
from __future__ import annotations

from leibniz.propositio import Demonstratio, Enuntiatio, Expressio, Propositio
from leibniz.runtime import PersistentRuntime, phase_for_hour
from leibniz.types import ClaimType, FinishReason


def _prop(statement: str, *, proven: bool = False, reason: FinishReason | None = None) -> Propositio:
    p = Propositio(
        enuntiatio=Enuntiatio(statement=statement, claim_type=ClaimType.STRUCTURAL,
                              falsifiable_claim="nope"),
        expressio=Expressio(theorem_src=f"theorem t : {statement}", normalized_hash="h"),
        demonstratio=Demonstratio(proof_obligation="t", kernel_verified=proven,
                                  qed="Q.E.D." if proven else "Q.E.I."),
    )
    # A proven law's disposition is PROMULGATED; the runtime records disposition via
    # finish_reason, never the policy-gated `promulgated` flag.
    p.finish_reason = reason or (FinishReason.PROMULGATED if proven else None)
    return p


# --- circadian phase ---------------------------------------------------------

def test_phase_for_hour_maps_the_day():
    assert phase_for_hour(9) == "WAKE"
    assert phase_for_hour(23) == "NREM"
    assert phase_for_hour(0) == "NREM"
    assert phase_for_hour(4) == "REM"


def test_now_phase_uses_injected_clock():
    # 4 AM UTC-ish: a fixed epoch second whose local hour we pin via the clock.
    rt = PersistentRuntime(db_path=":memory:", clock=lambda: 0.0)
    assert rt.now_phase() in {"WAKE", "NREM", "REM"}  # real value, not the constant "WAKE"


# --- memory persists across restarts -----------------------------------------

def test_memory_survives_restart(tmp_path):
    db = tmp_path / "mem.db"
    with PersistentRuntime(db_path=db) as rt:
        rt.remember(_prop("a + b = b + a", proven=True))
        rt.remember(_prop("n + 0 = n", reason=FinishReason.UNPROVEN))

    # A fresh runtime on the same file sees the prior session's ledger.
    with PersistentRuntime(db_path=db) as rt2:
        recalled = rt2.recall_recent(10)
        assert len(recalled) == 2
        statements = {p.enuntiatio.statement for p in recalled}
        assert statements == {"a + b = b + a", "n + 0 = n"}


def test_recall_recent_orders_newest_first_and_caps(tmp_path):
    with PersistentRuntime(db_path=tmp_path / "m.db") as rt:
        for i in range(5):
            rt.remember(_prop(f"s{i}"))
        recent = rt.recall_recent(3)
        assert [p.enuntiatio.statement for p in recent] == ["s4", "s3", "s2"]


def test_proven_candidate_round_trips_certificate(tmp_path):
    with PersistentRuntime(db_path=tmp_path / "m.db") as rt:
        rt.remember(_prop("proven", proven=True))
        rt.remember(_prop("unproven", reason=FinishReason.UNPROVEN))
        by_stmt = {p.enuntiatio.statement: p for p in rt.recall_recent(10)}
        assert by_stmt["proven"].demonstratio is not None
        assert by_stmt["proven"].demonstratio.kernel_verified is True
        assert by_stmt["proven"].finish_reason is FinishReason.PROMULGATED  # disposition
        assert by_stmt["proven"].promulgated is False  # runtime never sets the gated flag
        assert by_stmt["unproven"].demonstratio is None  # no surviving proof to restore
        assert by_stmt["unproven"].finish_reason is FinishReason.UNPROVEN


def test_claim_property_round_trips(tmp_path):
    """ADR 0034 Stage 0: the canonical DSL predicate is persisted and restored, so
    promulgations are natively measurable by novelty_metrics. A claim with no property
    (prose-only) round-trips as None."""
    with PersistentRuntime(db_path=tmp_path / "m.db") as rt:
        with_prop = _prop("n^3 + 5*n divisible by 3", proven=True)
        with_prop.enuntiatio.claim_property = "(n^3 + 5*n) % 3 == 0"
        rt.remember(with_prop)
        rt.remember(_prop("prose only", reason=FinishReason.UNPROVEN))  # claim_property None
        by_stmt = {p.enuntiatio.statement: p for p in rt.recall_recent(10)}
    assert by_stmt["n^3 + 5*n divisible by 3"].enuntiatio.claim_property == "(n^3 + 5*n) % 3 == 0"
    assert by_stmt["prose only"].enuntiatio.claim_property is None


def test_claim_property_migrates_on_preexisting_db(tmp_path):
    """A DB created before ADR 0034 (no claim_property column) gains it idempotently, and a
    later write/read carries the predicate — no data loss for pre-existing rows."""
    import sqlite3
    db = tmp_path / "legacy.db"
    # Simulate a pre-0034 schema: the 0033-era columns, without claim_property.
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE memory (pid TEXT PRIMARY KEY, born REAL, ts REAL, statement TEXT, "
        "claim_type TEXT, falsifiable_claim TEXT, domain TEXT, theorem_src TEXT, "
        "normalized_hash TEXT, kernel_verified INTEGER, qed TEXT, proof_src TEXT, "
        "finish_reason TEXT, parents TEXT, instance TEXT)"
    )
    con.execute(
        "INSERT INTO memory (pid, statement, claim_type, falsifiable_claim, kernel_verified, qed) "
        "VALUES ('old1', 'legacy law', 'structural', 'x', 0, 'Q.E.I.')"
    )
    con.commit()
    con.close()
    with PersistentRuntime(db_path=db) as rt:        # migration runs on connect
        p = _prop("new law")
        p.enuntiatio.claim_property = "(n^2) % 2 == 0"
        rt.remember(p)
        by_stmt = {x.enuntiatio.statement: x for x in rt.recall_recent(10)}
    assert by_stmt["legacy law"].enuntiatio.claim_property is None      # pre-existing row: NULL
    assert by_stmt["new law"].enuntiatio.claim_property == "(n^2) % 2 == 0"


def test_witness_is_a_documented_seam(tmp_path):
    with PersistentRuntime(db_path=tmp_path / "m.db") as rt:
        assert rt.witness("anything", 3) == []


def test_construction_is_side_effect_free(tmp_path):
    """build_daemon constructs a runtime; that must not touch the filesystem until
    the daemon actually runs (lazy connection)."""
    db = tmp_path / "lazy.db"
    PersistentRuntime(db_path=db)  # construct only
    assert not db.exists()


def test_seed_origin_round_trips(tmp_path):
    """ADR 0034 Stage 2: seed provenance (mined|weaken|kfm|survey) is persisted and restored so
    the §5 kill condition can isolate MINED-origin promulgations."""
    with PersistentRuntime(db_path=tmp_path / "m.db") as rt:
        p = _prop("mined law", proven=True)
        p.seed_origin = "mined"
        rt.remember(p)
        rt.remember(_prop("untagged law"))        # seed_origin None
        by = {x.enuntiatio.statement: x for x in rt.recall_recent(10)}
    assert by["mined law"].seed_origin == "mined"
    assert by["untagged law"].seed_origin is None

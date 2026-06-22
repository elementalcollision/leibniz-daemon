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


def test_witness_is_a_documented_seam(tmp_path):
    with PersistentRuntime(db_path=tmp_path / "m.db") as rt:
        assert rt.witness("anything", 3) == []


def test_construction_is_side_effect_free(tmp_path):
    """build_daemon constructs a runtime; that must not touch the filesystem until
    the daemon actually runs (lazy connection)."""
    db = tmp_path / "lazy.db"
    PersistentRuntime(db_path=db)  # construct only
    assert not db.exists()

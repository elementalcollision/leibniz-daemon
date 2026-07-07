"""ADR 0052: novelty against the daemon's own ledger — seed the novelty corpus with the daemon's
promulgated laws so it stops rediscovering itself. The gate stays kill-only (soundness-safe) and
matches by formal_hash (so distinct statements are never false-KNOWN)."""
from __future__ import annotations

import sqlite3

from leibniz.corpus import CorpusBackend, self_ledger_entries
from leibniz.gates.novelty import NoveltyGate
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.runtime import _SCHEMA
from leibniz.types import ClaimSignature, ClaimType, FinishReason, Verdict


def _seed_db(path, *, promulgated_hash="hashA", unproven_hash="hashB"):
    con = sqlite3.connect(path)
    con.execute(_SCHEMA)
    # a PROMULGATED, kernel-verified law -> should seed the ledger
    con.execute(
        "INSERT INTO memory (pid, born, ts, statement, claim_type, theorem_src, normalized_hash, "
        "kernel_verified, qed, finish_reason) VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("p1", 0.0, 1.0, "n^4%5", "invariant", "theorem law_a (n:Nat) : n^4%5=0",
         promulgated_hash, 1, "Q.E.D.", "promulgated"),
    )
    # an UNPROVEN prior attempt -> must NOT seed the ledger (stay re-attemptable)
    con.execute(
        "INSERT INTO memory (pid, born, ts, statement, claim_type, theorem_src, normalized_hash, "
        "kernel_verified, qed, finish_reason) VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("p2", 0.0, 2.0, "hard", "invariant", "theorem law_b : Hard", unproven_hash, 0, "Q.E.I.", "unproven"),
    )
    con.commit()
    con.close()


def test_self_ledger_loads_only_promulgated(tmp_path):
    db = str(tmp_path / "mem.db")
    _seed_db(db)
    entries = self_ledger_entries(db)
    hashes = {e.formal_hash for e in entries}
    assert hashes == {"hashA"}                      # promulgated only; unproven excluded
    e = entries[0]
    assert e.name.startswith("ledger:") and e.formal_hash == "hashA"


def test_self_ledger_failsafe():
    assert self_ledger_entries(None) == []
    assert self_ledger_entries("/no/such/path/x.db") == []   # read-only, missing -> [] (not an error)


def test_seeded_corpus_matches_rediscovery_but_not_distinct(tmp_path):
    db = str(tmp_path / "mem.db")
    _seed_db(db)
    corpus = CorpusBackend(list(self_ledger_entries(db)))  # empty external corpus + self-ledger
    # a re-conjecture with the SAME canonical hash is KNOWN
    assert corpus.contains_equivalent(ClaimSignature(
        subject="x", relation="r", claim_type=ClaimType.INVARIANT, formal_hash="hashA"))
    # a genuinely DISTINCT statement (different hash) is NOT false-KNOWN
    assert not corpus.contains_equivalent(ClaimSignature(
        subject="x", relation="r", claim_type=ClaimType.INVARIANT, formal_hash="different"))


class _FakeLeanNonTrivial:
    """is_trivial -> False, so the gate proceeds to the corpus check."""
    def closed_by_decision_procedure(self, expr): return False


def _prop(formal_hash):
    p = Propositio(
        enuntiatio=Enuntiatio(statement="s", claim_type=ClaimType.INVARIANT, falsifiable_claim="f"),
        expressio=Expressio(theorem_src="theorem t : P", normalized_hash=formal_hash),
    )
    p.signature = ClaimSignature(subject="x", relation="r", claim_type=ClaimType.INVARIANT,
                                 formal_hash=formal_hash)
    return p


def test_novelty_gate_quarantines_own_prior_law(tmp_path):
    from leibniz.verifiers import LeanVerifier
    db = str(tmp_path / "mem.db")
    _seed_db(db, promulgated_hash="hashA")
    corpus = CorpusBackend(list(self_ledger_entries(db)))
    gate = NoveltyGate(corpus, LeanVerifier(_FakeLeanNonTrivial()))

    # re-conjecturing the daemon's own promulgated law -> KNOWN (quarantined)
    redisc = _prop("hashA")
    ev = gate.check(redisc)
    assert ev.verdict is Verdict.FAIL
    assert redisc.finish_reason is FinishReason.KNOWN

    # a distinct law -> passes novelty
    fresh = _prop("brand_new_hash")
    ev2 = gate.check(fresh)
    assert ev2.verdict is Verdict.PASS

"""ADR 0072 — Newton folio exchange tests. CI-safe: temp sqlite DB, temp exchange dir, no LLM,
no network. What we pin down: folio shape (Newton frontmatter vocabulary, verified stays false,
Lean block, runnable audit), the failed-audit tripwire (a claim/theorem disagreement is REFUSED,
never shipped), manifest dedup, and the heartbeat gating."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz import newton_exchange as nx  # noqa: E402

_ROW = {
    "pid": "dab2022069c9", "born": 1784900000.0,
    "statement": "The sum of two squares is never congruent to 3 modulo 4.",
    "theorem_src": "theorem residue_law_8a475b40329d : ∀ (a b : ℤ), (0 ≤ a) → (0 ≤ b) → "
                   "((a ≥ 0) ∧ (b ≥ 0)) → ((Int.emod ((a ^ (2 : ℕ)) + (b ^ (2 : ℕ))) 4) ≠ 3)",
    "proof_src": "by\n  intro a b _ _ _\n  omega_nat",
    "claim_property": "(a^2 + b^2) % 4 != 3",
    "domain": "number_theory",
}


def test_audit_source_is_selfcontained_and_correct():
    src = nx.audit_source("(a^2 + b^2) % 4 != 3", ["a", "b"])
    ns: dict = {}
    exec(src, ns)
    assert ns["audit"](12) is True                        # the classical mod-4 obstruction holds
    bad: dict = {}
    exec(nx.audit_source("a % 2 == 0", ["a"]), bad)
    assert bad["audit"](4) is False                       # a false claim fails its own audit


def test_law_folio_shape_and_honesty():
    fname, text = nx.law_folio(_ROW)
    assert fname == "leibniz_dab2022069c9.md"
    assert "propositio_id: leibniz_dab2022069c9" in text
    assert "verified: false" in text                      # Newton's stamp is Newton's to make
    assert "source_mode: federated_leibniz" in text
    assert "kernel_verified: true" in text and "Lean 4.31" in text
    assert "```lean" in text and "residue_law_8a475b40329d" in text and "omega_nat" in text
    assert "## Auditio mechanica" in text and "def audit(bound: int = 64)" in text
    assert "LLMs propose; only mechanical checkers" in text


def test_folio_refuses_claim_theorem_disagreement():
    lying = dict(_ROW, claim_property="(a^2 + b^2) % 4 == 3")   # audit fails everywhere
    assert nx.law_folio(lying) is None                    # the tripwire: never ship a falsehood
    assert nx.law_folio(dict(_ROW, claim_property="")) is None
    assert nx.law_folio(dict(_ROW, claim_property="while True: pass")) is None  # not a DSL claim


def _seed_db(path: Path, rows) -> None:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE memory (pid TEXT PRIMARY KEY, born REAL, statement TEXT, "
                "theorem_src TEXT, proof_src TEXT, claim_property TEXT, domain TEXT, "
                "finish_reason TEXT, kernel_verified INTEGER)")
    for r in rows:
        con.execute("INSERT INTO memory VALUES (?,?,?,?,?,?,?,?,?)", r)
    con.commit()
    con.close()


def test_export_new_writes_dedups_and_counts_refusals(tmp_path):
    db = tmp_path / "mem.db"
    _seed_db(db, [
        ("dab2022069c9", 1784900000.0, "s", _ROW["theorem_src"], "by x",
         "(a^2 + b^2) % 4 != 3", "number_theory", "promulgated", 1),
        ("badbadbadbad", 1784900001.0, "s", "theorem bad : True", "by y",
         "a % 2 == 0", "number_theory", "promulgated", 1),        # false claim → refused
        ("eeee3333ffff", 1784900002.0, "s", "theorem q : True", "by z",
         "(a^2) % 2 == 0", "number_theory", "refuted", 0)])       # quarantined → never queried
    out = tmp_path / "exchange"
    res = nx.export_new(db, out)
    assert res == {"exported": 1, "refused": 1, "total": 1}
    assert (out / "leibniz_dab2022069c9.md").exists()
    manifest = json.loads((out / "manifest.json").read_text())
    assert set(manifest) == {"dab2022069c9"}
    again = nx.export_new(db, out)                        # manifest dedup: nothing re-exported
    assert again == {"exported": 0, "refused": 1, "total": 1}


def test_export_new_survives_missing_db(tmp_path):
    res = nx.export_new(tmp_path / "nope.db", tmp_path / "exchange")
    assert res == {"exported": 0, "refused": 0, "total": 0}


def test_heartbeat_runs_exchange_only_when_enabled(tmp_path, monkeypatch):
    from scripts import heartbeat
    db = tmp_path / "mem.db"
    _seed_db(db, [("dab2022069c9", 1784900000.0, "s", _ROW["theorem_src"], "by x",
                   "(a^2 + b^2) % 4 != 3", "number_theory", "promulgated", 1)])
    monkeypatch.setenv("LEIBNIZ_HEARTBEAT_HOME", str(tmp_path))
    monkeypatch.setenv("LEIBNIZ_RUNTIME_DB", str(db))
    monkeypatch.setenv("LEIBNIZ_NEWTON_EXCHANGE_DIR", str(tmp_path / "exchange"))
    monkeypatch.setattr(heartbeat, "preflight", lambda: ([], []))
    monkeypatch.setattr(heartbeat, "lean_containers", lambda: 0)
    monkeypatch.setattr(heartbeat, "beat", lambda cycles: {
        "ts": "t", "cycles": [], "anomalies": [],
        "cross_stats_delta": {"checked": 0, "agree": 0, "cvc5_unknown": 0, "disagree": 0},
        "duration_s": 0.1})
    monkeypatch.delenv("LEIBNIZ_NEWTON_EXCHANGE", raising=False)
    assert heartbeat.main() == 0
    entry = json.loads((tmp_path / "journal.jsonl").read_text().splitlines()[-1])
    assert "newton_exchange" not in entry                 # off by default
    monkeypatch.setenv("LEIBNIZ_NEWTON_EXCHANGE", "1")
    assert heartbeat.main() == 0
    entry = json.loads((tmp_path / "journal.jsonl").read_text().splitlines()[-1])
    assert entry["newton_exchange"] == {"exported": 1, "refused": 0, "total": 1}
    assert (tmp_path / "exchange" / "leibniz_dab2022069c9.md").exists()

"""ADR 0068 — heartbeat unit tests. CI-safe: no Docker, no launchd, no LLM; everything that would
touch the outside world is monkeypatched. What we pin down: journal append shape, review-queue
rendering from a real (temp) sqlite DB, the anomaly detector's rules, preflight abort wiring, and
alarm logging."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import heartbeat  # noqa: E402


def test_journal_appends_jsonl(tmp_path):
    p1 = heartbeat.write_journal({"ts": "t1", "cycles": []}, home=tmp_path)
    p2 = heartbeat.write_journal({"ts": "t2", "cycles": [{"seeds": 2}]}, home=tmp_path)
    assert p1 == p2 == tmp_path / "journal.jsonl"
    lines = p1.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["ts"] == "t1"
    assert json.loads(lines[1])["cycles"][0]["seeds"] == 2


def _seed_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE memory (pid TEXT PRIMARY KEY, born REAL, theorem_src TEXT, "
                "finish_reason TEXT, kernel_verified INTEGER)")
    con.executemany(
        "INSERT INTO memory VALUES (?, ?, ?, ?, ?)",
        [("aaaa1111bbbb", 1783000000.0, "theorem held_one : 1 = 1 := rfl", "promulgated", 1),
         ("cccc2222dddd", 1783100000.0, "theorem held_two : 2 = 2 := rfl", "PROMULGATED", 1),
         ("eeee3333ffff", 1783200000.0, "theorem quarantined : 3 = 3 := rfl", "refuted", 0),
         ("9999aaaa0000", 1783300000.0, "theorem unverified : 4 = 4 := rfl", "promulgated", 0)])
    con.commit()
    con.close()


def test_review_queue_lists_only_promulgated_kernel_verified(tmp_path):
    db = tmp_path / "mem.db"
    _seed_db(db)
    p = heartbeat.write_review_queue(db, home=tmp_path)
    text = p.read_text()
    assert "aaaa1111" in text and "cccc2222" in text          # both spellings of promulgated
    assert "eeee3333" not in text                              # quarantined never queued
    assert "9999aaaa" not in text                              # not kernel-verified → not a law
    assert "ADR 0033" in text                                  # the held-for-operator framing
    assert text.index("cccc2222") < text.index("aaaa1111")     # newest first


def test_review_queue_survives_missing_db(tmp_path):
    p = heartbeat.write_review_queue(tmp_path / "nope.db", home=tmp_path)
    assert "(no held promulgations)" in p.read_text()


def test_detect_anomalies_rules():
    clean = {"cycles": [{"seeds": 2, "by_reason": {}}], "cross_stats_delta": {"disagree": 0}, "anomalies": []}
    assert heartbeat.detect_anomalies(clean, containers_after=0) == []
    disagree = {**clean, "cross_stats_delta": {"disagree": 1}}
    assert any("DISAGREEMENT" in a for a in heartbeat.detect_anomalies(disagree, 0))
    errored = {**clean, "cycles": [{"seeds": 2, "by_reason": {"errored": 3}}]}
    assert any("errored" in a for a in heartbeat.detect_anomalies(errored, 0))
    assert any("container" in a for a in heartbeat.detect_anomalies(clean, containers_after=2))
    zero = {**clean, "cycles": [{"seeds": 0, "by_reason": {}}, {"seeds": 0, "by_reason": {}}]}
    assert any("0 seeds" in a for a in heartbeat.detect_anomalies(zero, 0))
    crashed = {**clean, "anomalies": ["cycle 1 errored: RuntimeError: boom"]}
    assert "cycle 1 errored: RuntimeError: boom" in heartbeat.detect_anomalies(crashed, 0)


def test_wait_containers_drained_gives_grace(monkeypatch):
    counts = iter([2, 1, 0])
    monkeypatch.setattr(heartbeat, "lean_containers", lambda: next(counts))
    monkeypatch.setattr(heartbeat.time, "sleep", lambda s: None)
    assert heartbeat.wait_containers_drained(timeout_s=60, poll_s=1) == 0
    monkeypatch.setattr(heartbeat, "lean_containers", lambda: 3)   # a genuine leak still reports
    assert heartbeat.wait_containers_drained(timeout_s=0) == 3


def test_alarm_writes_log(tmp_path, monkeypatch):
    monkeypatch.setattr(heartbeat.subprocess, "run", lambda *a, **k: None)  # no real osascript
    heartbeat.alarm(["first thing", "second thing"], home=tmp_path)
    text = (tmp_path / "alarms.log").read_text()
    assert "first thing" in text and "second thing" in text
    heartbeat.alarm([], home=tmp_path)                         # no-op on empty
    assert text == (tmp_path / "alarms.log").read_text()


def test_main_aborts_on_preflight(tmp_path, monkeypatch):
    monkeypatch.setenv("LEIBNIZ_HEARTBEAT_HOME", str(tmp_path))
    monkeypatch.setattr(heartbeat, "preflight", lambda: (["docker daemon unreachable"], ["note"]))
    monkeypatch.setattr(heartbeat.subprocess, "run", lambda *a, **k: None)
    assert heartbeat.main() == 2
    entry = json.loads((tmp_path / "journal.jsonl").read_text().splitlines()[-1])
    assert entry["aborted"] is True and entry["preflight"] == ["docker daemon unreachable"]
    assert "ABORTED" in (tmp_path / "alarms.log").read_text()


def test_main_clean_and_anomalous_paths(tmp_path, monkeypatch):
    db = tmp_path / "mem.db"
    _seed_db(db)
    monkeypatch.setenv("LEIBNIZ_HEARTBEAT_HOME", str(tmp_path))
    monkeypatch.setenv("LEIBNIZ_RUNTIME_DB", str(db))
    monkeypatch.setattr(heartbeat, "preflight", lambda: ([], []))
    monkeypatch.setattr(heartbeat, "lean_containers", lambda: 0)
    good = {"ts": "t", "cycles": [{"seeds": 1, "conjectured": 1, "reached_proof": 1,
                                  "promulgated": 1, "by_reason": {}}],
            "anomalies": [], "cross_stats_delta": {"checked": 1, "agree": 1, "cvc5_unknown": 0, "disagree": 0},
            "duration_s": 0.1}
    monkeypatch.setattr(heartbeat, "beat", lambda cycles: dict(good))
    assert heartbeat.main() == 0
    assert (tmp_path / "review_queue.md").exists()
    bad = dict(good, cross_stats_delta={"checked": 1, "agree": 0, "cvc5_unknown": 0, "disagree": 1})
    monkeypatch.setattr(heartbeat, "beat", lambda cycles: dict(bad))
    monkeypatch.setattr(heartbeat.subprocess, "run", lambda *a, **k: None)
    assert heartbeat.main() == 3
    last = json.loads((tmp_path / "journal.jsonl").read_text().splitlines()[-1])
    assert any("DISAGREEMENT" in a for a in last["anomalies"])

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


# === ADR 0069 (Phase β): the beat turns the FULL steering loop =================

import types  # noqa: E402


def _stub_assembly(monkeypatch, daemon):
    """Install a fake leibniz.assembly so beat() runs core-only in CI (no providers/z3)."""
    mod = types.ModuleType("leibniz.assembly")
    mod.build_daemon = lambda frontier_limit, analogy_limit: daemon
    monkeypatch.setitem(sys.modules, "leibniz.assembly", mod)


def _report(**kw):
    d = {"seeds": 2, "conjectured": 2, "reached_proof": 1, "promulgated": 0, "by_reason": {}}
    d.update(kw)
    return types.SimpleNamespace(**d)


def test_beat_uses_run_cycles_and_journals_steering(monkeypatch):
    # Isolate the process-global REPL registry: close_all() legitimately closes backends spawned
    # by EARLIER tests in the same process, so without this the count is whatever the rest of the
    # suite happened to leave open (measured: 25 in a full run) and the assertion below is
    # order-dependent. Isolating it makes the assertion mean what it says.
    from leibniz.backends import lean_repl
    monkeypatch.setattr(lean_repl, "_LIVE", [])
    calls = {}

    class _Daemon:
        notebook = types.SimpleNamespace(genre_kill=["== modular claims modulo 2"],
                                         dry_kill=["== modular claims modulo 5"],
                                         too_hard=["a", "b"])
        frontier = types.SimpleNamespace(target=0.41)

        def run_cycles(self, n):
            calls["n"] = n
            return [_report(), _report(promulgated=1, by_reason={"promulgated": 1})]

        def circadian_cycle(self):  # the Phase α path must NOT be taken any more
            raise AssertionError("beat must turn run_cycles, not bare circadian_cycle")

    _stub_assembly(monkeypatch, _Daemon())
    entry = heartbeat.beat(cycles=2)
    assert calls["n"] == 2
    assert [c["promulgated"] for c in entry["cycles"]] == [0, 1]
    assert entry["steering"]["dry_kill"] == ["== modular claims modulo 5"]
    assert entry["steering"]["genre_kill"] == ["== modular claims modulo 2"]
    assert entry["steering"]["too_hard"] == 2
    assert entry["steering"]["band_target"] == 0.41
    assert entry["anomalies"] == []
    assert entry["backends_closed"] == 0               # stub daemon spawned no real REPL backends


def test_beat_captures_a_mid_run_crash_as_anomaly(monkeypatch):
    class _Daemon:
        notebook = None
        frontier = None

        def run_cycles(self, n):
            raise RuntimeError("kernel wedged")

    _stub_assembly(monkeypatch, _Daemon())
    entry = heartbeat.beat(cycles=2)
    assert any("kernel wedged" in a for a in entry["anomalies"])
    assert entry["cycles"] and "error" in entry["cycles"][0]
    assert entry["steering"] == {"genre_kill": [], "dry_kill": [], "too_hard": 0,
                                 "band_target": None}


def test_main_runs_feed_only_when_enabled(tmp_path, monkeypatch):
    db = tmp_path / "mem.db"
    _seed_db(db)
    monkeypatch.setenv("LEIBNIZ_HEARTBEAT_HOME", str(tmp_path))
    monkeypatch.setenv("LEIBNIZ_RUNTIME_DB", str(db))
    monkeypatch.setattr(heartbeat, "preflight", lambda: ([], []))
    monkeypatch.setattr(heartbeat, "lean_containers", lambda: 0)
    good = {"ts": "t", "cycles": [], "anomalies": [],
            "cross_stats_delta": {"checked": 0, "agree": 0, "cvc5_unknown": 0, "disagree": 0},
            "duration_s": 0.1}
    monkeypatch.setattr(heartbeat, "beat", lambda cycles: dict(good))
    monkeypatch.delenv("LEIBNIZ_ARXIV_FEED", raising=False)
    assert heartbeat.main() == 0
    entry = json.loads((tmp_path / "journal.jsonl").read_text().splitlines()[-1])
    assert "arxiv_feed" not in entry                            # off by default
    monkeypatch.setenv("LEIBNIZ_ARXIV_FEED", "1")
    feed_mod = types.ModuleType("leibniz.arxiv_feed")
    feed_mod.run_feed = lambda home: {"fetched": 7, "queued": 2}
    monkeypatch.setitem(sys.modules, "leibniz.arxiv_feed", feed_mod)
    assert heartbeat.main() == 0
    entry = json.loads((tmp_path / "journal.jsonl").read_text().splitlines()[-1])
    assert entry["arxiv_feed"] == {"fetched": 7, "queued": 2}


def test_main_feed_failure_is_a_note_not_an_abort(tmp_path, monkeypatch):
    db = tmp_path / "mem.db"
    _seed_db(db)
    monkeypatch.setenv("LEIBNIZ_HEARTBEAT_HOME", str(tmp_path))
    monkeypatch.setenv("LEIBNIZ_RUNTIME_DB", str(db))
    monkeypatch.setenv("LEIBNIZ_ARXIV_FEED", "1")
    monkeypatch.setattr(heartbeat, "preflight", lambda: ([], []))
    monkeypatch.setattr(heartbeat, "lean_containers", lambda: 0)
    monkeypatch.setattr(heartbeat, "beat", lambda cycles: {
        "ts": "t", "cycles": [], "anomalies": [],
        "cross_stats_delta": {"checked": 0, "agree": 0, "cvc5_unknown": 0, "disagree": 0},
        "duration_s": 0.1})
    feed_mod = types.ModuleType("leibniz.arxiv_feed")

    def _boom(home):
        raise OSError("arxiv unreachable")
    feed_mod.run_feed = _boom
    monkeypatch.setitem(sys.modules, "leibniz.arxiv_feed", feed_mod)
    assert heartbeat.main() == 0                                # a feed failure never pages
    entry = json.loads((tmp_path / "journal.jsonl").read_text().splitlines()[-1])
    assert "arxiv unreachable" in entry["arxiv_feed"]["error"]


def test_beat_pins_the_notebook_to_the_canonical_home(monkeypatch, tmp_path):
    """ADR 0073: the notebook must resolve under LEIBNIZ_HEARTBEAT_HOME, not beside the throwaway
    sync worktree (where it was disjoint from the band + ledger and one `git clean` from gone)."""
    monkeypatch.setenv("LEIBNIZ_HEARTBEAT_HOME", str(tmp_path))
    monkeypatch.delenv("LEIBNIZ_NOTEBOOK_PATH", raising=False)

    class _Daemon:
        notebook = None
        frontier = None

        def run_cycles(self, n):
            return []

    _stub_assembly(monkeypatch, _Daemon())
    heartbeat.beat(cycles=1)
    assert heartbeat.os.environ["LEIBNIZ_NOTEBOOK_PATH"] == str(tmp_path / "notebook.json")


def test_beat_does_not_override_an_explicit_notebook_path(monkeypatch, tmp_path):
    monkeypatch.setenv("LEIBNIZ_HEARTBEAT_HOME", str(tmp_path))
    monkeypatch.setenv("LEIBNIZ_NOTEBOOK_PATH", "/custom/nb.json")

    class _Daemon:
        notebook = None
        frontier = None

        def run_cycles(self, n):
            return []

    _stub_assembly(monkeypatch, _Daemon())
    heartbeat.beat(cycles=1)
    assert heartbeat.os.environ["LEIBNIZ_NOTEBOOK_PATH"] == "/custom/nb.json"  # setdefault, not clobber


# === ADR 0082: drift detection — the daemon converging on a bad equilibrium ==

def _journal(tmp_path, bands):
    p = tmp_path / "journal.jsonl"
    with p.open("w") as f:
        for b in bands:
            f.write(json.dumps({"ts": "t", "steering": {"band_target": b, "genre_kill": [],
                                                        "too_hard": 0}}) + "\n")
    return {"steering": {"band_target": bands[-1], "genre_kill": [], "too_hard": 0}}


def test_a_band_that_never_moves_is_flagged(tmp_path):
    entry = _journal(tmp_path, [0.15, 0.15, 0.15, 0.15])
    msgs = heartbeat.detect_equilibria(entry, tmp_path)
    assert any("pinned" in m for m in msgs)


def test_a_band_that_is_moving_is_not_flagged(tmp_path):
    # the live case after ADR 0080 fired: 0.15 -> 0.57 -> homing back down
    entry = _journal(tmp_path, [0.15, 0.15, 0.57, 0.502])
    assert not any("pinned" in m for m in heartbeat.detect_equilibria(entry, tmp_path))


def test_a_saturated_notebook_with_no_genre_retired_is_flagged(tmp_path):
    entry = _journal(tmp_path, [0.3, 0.4, 0.5, 0.6])
    entry["steering"]["too_hard"] = 12
    assert any("too_hard at capacity" in m for m in heartbeat.detect_equilibria(entry, tmp_path))
    entry["steering"]["genre_kill"] = ["== modular claims (any modulus)"]
    assert not any("too_hard" in m for m in heartbeat.detect_equilibria(entry, tmp_path))


def test_output_and_feed_backlogs_are_surfaced(tmp_path):
    entry = _journal(tmp_path, [0.3, 0.4, 0.5, 0.6])
    (tmp_path / "review_queue.md").write_text("\n".join(f"- `x{i}` law" for i in range(31)))
    (tmp_path / "amplification_queue.jsonl").write_text("\n".join(["{}"] * 6))
    entry["arxiv_feed"] = {"fetched": 80, "queued": 1}
    msgs = heartbeat.detect_equilibria(entry, tmp_path)
    assert any("held for the operator" in m for m in msgs)
    assert any("unconsumed" in m for m in msgs)


def test_drift_never_changes_the_exit_code_on_its_own(tmp_path, monkeypatch):
    db = tmp_path / "mem.db"
    _seed_db(db)
    monkeypatch.setenv("LEIBNIZ_HEARTBEAT_HOME", str(tmp_path))
    monkeypatch.setenv("LEIBNIZ_RUNTIME_DB", str(db))
    monkeypatch.setattr(heartbeat, "preflight", lambda: ([], []))
    monkeypatch.setattr(heartbeat, "lean_containers", lambda: 0)
    monkeypatch.setattr(heartbeat, "detect_equilibria", lambda e, h=None, look_back=3: ["drifting"])
    monkeypatch.setattr(heartbeat, "beat", lambda cycles: {
        "ts": "t", "cycles": [], "anomalies": [],
        "cross_stats_delta": {"checked": 0, "agree": 0, "cvc5_unknown": 0, "disagree": 0},
        "duration_s": 0.1})
    monkeypatch.setattr(heartbeat.subprocess, "run", lambda *a, **k: None)
    assert heartbeat.main() == 0                       # drift alone is advisory, not rc=3
    entry = json.loads((tmp_path / "journal.jsonl").read_text().splitlines()[-1])
    assert entry["equilibria"] == ["drifting"]
    assert "DRIFT: drifting" in (tmp_path / "alarms.log").read_text()


def test_a_missing_journal_degrades_silently(tmp_path):
    assert heartbeat.detect_equilibria({"steering": {}}, tmp_path) == []


# === ADR 0087: subsumption annotations in the review queue ===================

_BOX = "a >= 0 and b >= 0"
_HELD_CP = ("(max(a,b) - min(a,b)) * (a + b) == max(a,b)^2 - min(a,b)^2 "
            "and max(a,b) * min(a,b) == a*b")
_WEAK_CP = "max(a,b)^2 - min(a,b)^2 == (max(a,b) - min(a,b)) * (a + b)"


def _contract_db(path, *, with_domain=True):
    """A ledger holding the real live pair: a law and a weaker one contained in it."""
    con = sqlite3.connect(path)
    cols = ("pid TEXT PRIMARY KEY, born REAL, theorem_src TEXT, claim_property TEXT, "
            "finish_reason TEXT, kernel_verified INTEGER"
            + (", claim_domain TEXT" if with_domain else ""))
    con.execute(f"CREATE TABLE memory ({cols})")
    rows = [("held0001", 1.0, "theorem held : True", _HELD_CP, "promulgated", 1),
            ("weak0001", 2.0, "theorem weak : True", _WEAK_CP, "promulgated", 1)]
    if with_domain:
        con.executemany("INSERT INTO memory VALUES (?,?,?,?,?,?,?)",
                        [r + (_BOX,) for r in rows])
    else:
        con.executemany("INSERT INTO memory VALUES (?,?,?,?,?,?)", rows)
    con.commit()
    con.close()
    return str(path)


def test_a_contained_law_is_flagged_not_dropped(tmp_path):
    db = _contract_db(tmp_path / "m.db")
    text = heartbeat.write_review_queue(db, tmp_path).read_text()
    assert text.count("- `") == 2                    # BOTH laws still listed — advisory only
    assert "contained in `held0001`" in text         # the weaker one is flagged
    # match on the ENTRY, not the annotation: the weak line mentions `held0001` inside its flag
    weak_line = next(ln for ln in text.splitlines() if ln.startswith("- `weak0001`"))
    held_line = next(ln for ln in text.splitlines() if ln.startswith("- `held0001`"))
    assert "contained in" in weak_line and "contained in" not in held_line   # asymmetric


def test_a_pre_migration_database_still_gets_its_queue(tmp_path):
    """THE regression this nearly shipped: folding claim_domain into the main query made a
    pre-ADR-0086 database throw, the existing `except` swallowed it, and the operator's entire
    review queue came back EMPTY. A missing column must cost an annotation, never the queue."""
    db = _contract_db(tmp_path / "old.db", with_domain=False)
    text = heartbeat.write_review_queue(db, tmp_path).read_text()
    assert text.count("- `") == 2                    # queue intact
    assert "contained in" not in text                # simply no annotations

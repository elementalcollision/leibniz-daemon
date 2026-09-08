"""ADR 0092 — a hung beat must not be silent.

The journal entry is written at the END of a beat, so a beat that hangs writes nothing: no entry,
no anomaly, no alarm. It is indistinguishable from a night the schedule has not reached yet.
Observed live on 2026-09-08: the 01:30 beat ran 6h57m holding two Lean containers while the last
journal entry was still dated 2026-09-06 — 55 hours of silence that nothing was watching. The
journal also records a 26931 s (7.5 h) beat that completed, and `detect_anomalies` never looked at
duration, so even the one that DID journal raised nothing.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("hb", _ROOT / "scripts" / "heartbeat.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _entry(ts: str) -> str:
    return json.dumps({"ts": ts, "cycles": []}) + "\n"


def _stamp(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- the outside view: past beats went missing --------------------------------------------------

def test_stale_journal_alarms_when_beats_stop_journalling(tmp_path):
    m = _load()
    (tmp_path / "journal.jsonl").write_text(_entry(_stamp(72)))
    out = m.stale_journal_alarm(tmp_path, max_age_h=48)
    assert out and "STALE JOURNAL" in out[0] and "72" in out[0].split("in ")[1][:4]


def test_stale_journal_is_silent_when_recent(tmp_path):
    m = _load()
    (tmp_path / "journal.jsonl").write_text(_entry(_stamp(3)))
    assert m.stale_journal_alarm(tmp_path, max_age_h=48) == []


def test_a_daemon_that_never_ran_is_not_a_daemon_that_broke(tmp_path):
    """No journal at all must be silent: a fresh install has not failed."""
    m = _load()
    assert m.stale_journal_alarm(tmp_path, max_age_h=48) == []


def test_stale_check_reads_the_LAST_entry_not_the_first(tmp_path):
    m = _load()
    (tmp_path / "journal.jsonl").write_text(_entry(_stamp(500)) + _entry(_stamp(1)))
    assert m.stale_journal_alarm(tmp_path, max_age_h=48) == []


def test_malformed_journal_lines_do_not_break_the_check(tmp_path):
    """The check must never itself be the thing that fails a beat."""
    m = _load()
    (tmp_path / "journal.jsonl").write_text("{not json\n" + _entry(_stamp(1)) + "\n")
    assert m.stale_journal_alarm(tmp_path, max_age_h=48) == []


# --- duration is now inspected ------------------------------------------------------------------

def test_detect_anomalies_flags_a_slow_beat():
    m = _load()
    out = m.detect_anomalies({"duration_s": m.BEAT_MAX_S / 2 + 1, "cycles": [{"seeds": 1}]}, 0)
    assert any("SLOW BEAT" in a for a in out)


def test_detect_anomalies_is_quiet_on_a_normal_beat():
    """Production median is 404 s. A healthy beat must stay silent or the alarm is noise."""
    m = _load()
    out = m.detect_anomalies({"duration_s": 404.0, "cycles": [{"seeds": 1}]}, 0)
    assert not any("SLOW BEAT" in a for a in out)


def test_the_historical_7_5_hour_beat_would_now_alarm():
    """26931 s is in the journal, completed, and raised nothing at the time."""
    m = _load()
    out = m.detect_anomalies({"duration_s": 26930.8, "cycles": [{"seeds": 1}]}, 0)
    assert any("SLOW BEAT" in a for a in out)


def test_timed_out_entry_is_itself_an_anomaly():
    m = _load()
    out = m.detect_anomalies({"timed_out": True, "limit_s": 3600, "cycles": []}, 0)
    assert any("ceiling" in a for a in out)


# --- the watchdog ------------------------------------------------------------------------------

def test_watchdog_disarms_cleanly(tmp_path):
    """The common path: the beat finishes, the watchdog must not fire or leave a thread running."""
    m = _load()
    disarm = m._arm_watchdog(tmp_path, cycles=2, limit_s=30)
    disarm()
    assert not (tmp_path / "journal.jsonl").exists()


def test_watchdog_can_be_disabled(tmp_path):
    """limit_s <= 0 is the operator-supervised escape hatch."""
    m = _load()
    disarm = m._arm_watchdog(tmp_path, cycles=2, limit_s=0)
    disarm()
    assert not (tmp_path / "journal.jsonl").exists()


def test_watchdog_JOURNALS_before_it_kills(tmp_path):
    """THE point of the ADR. A watchdog that killed silently would fix the resource leak and keep
    the blind spot: the operator would still see no entry. Run in a subprocess because the
    watchdog calls os._exit."""
    script = f'''
import importlib.util, sys, time
spec = importlib.util.spec_from_file_location("hb", {str(_ROOT / "scripts" / "heartbeat.py")!r})
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from pathlib import Path
m._arm_watchdog(Path({str(tmp_path)!r}), cycles=2, limit_s=1)
time.sleep(30)          # simulate a wedged beat
'''
    r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=60)
    assert r.returncode == 3, f"expected the watchdog's exit code, got {r.returncode}"
    p = tmp_path / "journal.jsonl"
    assert p.exists(), "the watchdog killed the beat without journalling — the blind spot remains"
    entry = json.loads(p.read_text().strip().splitlines()[-1])
    assert entry["timed_out"] is True and entry["limit_s"] == 1
    assert any("TIMED OUT" in a for a in entry["anomalies"])
    assert (tmp_path / "alarms.log").exists()

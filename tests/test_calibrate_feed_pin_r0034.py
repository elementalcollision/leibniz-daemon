"""ADR 0034 A/B: the calibrate harness must let LEIBNIZ_FEED_PATH PIN the seed feed.

A valid A/B (arm A tonight, arm B tomorrow) requires identical seeds on both days. The live
arxiv feed at .../latest/ regenerates, so run_organic_ab.sh snapshots it once and points both
arms at the snapshot via LEIBNIZ_FEED_PATH. This guards that override so a future refactor can't
silently un-pin the feed and confound the comparison. Module-level import only — no network, no
Lean, no LLM (calibrate's heavy deps load inside main()).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_PATH = Path(__file__).resolve().parent.parent / "scripts" / "calibrate_discovery.py"


def _load_calibrate():
    spec = importlib.util.spec_from_file_location("calibrate_discovery", _PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_feed_path_env_pins_the_feed(monkeypatch):
    monkeypatch.setenv("LEIBNIZ_FEED_PATH", "/tmp/pinned/leibniz_snapshot.json")
    assert str(_load_calibrate()._FEED) == "/tmp/pinned/leibniz_snapshot.json"


def test_feed_path_defaults_to_live_latest_when_unset(monkeypatch):
    monkeypatch.delenv("LEIBNIZ_FEED_PATH", raising=False)
    assert str(_load_calibrate()._FEED).endswith("latest/leibniz.json")

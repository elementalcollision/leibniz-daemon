"""Regression: the frontier SEED corpus and the frontier BAND state are distinct files with
distinct env vars — and the band can never overwrite the seed corpus.

The 2026-07-09 live-run finding: `LEIBNIZ_FRONTIER_PATH` was read by BOTH Leonardo's seed corpus
(`corpus/frontier.json`, domain → seed lists) and the ADR 0019 FrontierController persistence —
and the controller's default even pointed AT the seed corpus, so every cycle's `frontier.save`
clobbered it (and a band-pointed env var zeroed discovery seeds). Now: `LEIBNIZ_FRONTIER_PATH` =
seeds only; `LEIBNIZ_FRONTIER_STATE` = band only (default `.leibniz/frontier.json`); and
`FrontierController.save` refuses to overwrite a non-band file.
"""
from __future__ import annotations

import json

import pytest

from leibniz.discovery import _DEFAULT_FRONTIER_STATE, FrontierController
from leibniz.leonardo import _DEFAULT_FRONTIER as SEED_DEFAULT
from leibniz.leonardo import _frontier_path as seed_path


def test_defaults_are_distinct_files():
    assert str(SEED_DEFAULT).endswith("corpus/frontier.json")
    assert str(_DEFAULT_FRONTIER_STATE).endswith(".leibniz/frontier.json")
    assert str(SEED_DEFAULT) != str(_DEFAULT_FRONTIER_STATE)


def test_env_vars_are_independent(monkeypatch):
    import importlib
    import os

    import leibniz.assembly as asm
    # LEIBNIZ_FRONTIER_PATH moves ONLY the seed corpus
    monkeypatch.setenv("LEIBNIZ_FRONTIER_PATH", "/tmp/seeds-only.json")
    monkeypatch.delenv("LEIBNIZ_FRONTIER_STATE", raising=False)
    assert str(seed_path()) == "/tmp/seeds-only.json"
    band = os.environ.get("LEIBNIZ_FRONTIER_STATE") or str(asm._DEFAULT_FRONTIER_STATE)
    assert band == str(_DEFAULT_FRONTIER_STATE)          # the band path did NOT move
    # LEIBNIZ_FRONTIER_STATE moves ONLY the band
    monkeypatch.delenv("LEIBNIZ_FRONTIER_PATH", raising=False)
    monkeypatch.setenv("LEIBNIZ_FRONTIER_STATE", "/tmp/band-only.json")
    assert str(seed_path()) == str(SEED_DEFAULT)         # the seed path did NOT move
    importlib.reload  # (no reload needed — both reads are call-time)


def test_save_refuses_to_clobber_a_seed_corpus_shaped_file(tmp_path):
    seedish = tmp_path / "frontier.json"
    seedish.write_text(json.dumps({"arithmetic": ["seed one", "seed two"]}))
    with pytest.raises(ValueError, match="non-band"):
        FrontierController().save(seedish)
    assert json.loads(seedish.read_text()) == {"arithmetic": ["seed one", "seed two"]}  # untouched


def test_save_works_on_fresh_band_and_garbage_paths(tmp_path):
    fc = FrontierController()
    band = tmp_path / "sub" / "band.json"
    fc.save(band)                                        # fresh path (parent created)
    fc.save(band)                                        # re-save over real band state
    assert "target" in json.loads(band.read_text())
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{{{not json")
    fc.save(corrupt)                                     # corrupt file = cold-start contract → overwrite
    assert "target" in json.loads(corrupt.read_text())


def test_band_roundtrip_via_load():
    fc = FrontierController.load(_DEFAULT_FRONTIER_STATE)   # missing/fresh → defaults, never a crash
    assert 0.0 <= fc.target <= 1.0

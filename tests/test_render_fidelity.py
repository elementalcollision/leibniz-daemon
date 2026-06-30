"""Render-fidelity lock (validation plan Tier 0, R0.1).

The published audit artifacts (the Calculemus audit annex + the plain corpus table) must be a faithful
render of the committed kernel-checked corpus JSON. Without this lock, a hand-edit to a markdown — or a
corpus edit that is never re-rendered — drifts the published ledger from the kernel verdicts silently.
This pins `render == committed .md` byte-for-byte as a regression: it is GREEN today and turns RED on any
unrendered JSON edit or any direct markdown edit.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_RESULTS = _ROOT / "docs" / "results"


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


amp = _load("amplify", "scripts/amplify.py")


def _corpus() -> list[dict]:
    return json.loads((_RESULTS / "amplification_corpus.json").read_text())


def test_plain_corpus_markdown_matches_render():
    corpus = _corpus()
    committed = (_RESULTS / "amplification_corpus.md").read_text()
    assert amp.render_corpus(corpus) == committed, (
        "amplification_corpus.md is not a faithful render of amplification_corpus.json — "
        "re-render it (amplify.render_corpus) instead of hand-editing the markdown")


def test_reading_room_markdown_matches_render():
    corpus = _corpus()
    committed = (_RESULTS / "amplification_reading_room.md").read_text()
    assert amp.render_reading_room(corpus) == committed, (
        "amplification_reading_room.md is not a faithful render of amplification_corpus.json — "
        "re-render it (amplify.render_reading_room) instead of hand-editing the markdown")


def test_no_unverified_row_is_counted_verified():
    # the display-side soundness gate: only the literal 'KERNEL-VERIFIED' string counts as verified.
    corpus = _corpus()
    for r in corpus:
        if str(r.get("kernel", "")) != "KERNEL-VERIFIED":
            assert not amp._verified(r)

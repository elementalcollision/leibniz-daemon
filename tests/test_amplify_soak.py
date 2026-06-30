"""Guard the amplify batch soak + the merge_corpus precondition (validation plan Tier 0, R0.7)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(mod_name, m)
    spec.loader.exec_module(m)
    return m


amp = _load("amplify", "scripts/amplify.py")
soak = _load("amplify_soak", "scripts/amplify_soak.py")


def test_merge_corpus_rejects_new_row_missing_required_field():
    good = {"domain": "covering", "cell": "C(7,3,2)", "size": 7, "witness_sha": "abc", "witness": []}
    # baseline: a complete row merges fine
    assert amp.merge_corpus([], [good]) == [good]
    # a new row missing 'size' is a hard precondition violation with a CLEAR error (not raw KeyError)
    bad = {"domain": "covering", "cell": "C(7,3,2)", "witness_sha": "abc"}
    with pytest.raises(ValueError, match="missing required field"):
        amp.merge_corpus([], [bad])


def test_merge_corpus_tolerates_older_existing_rows():
    older = {"domain": "covering", "cell": "C(7,3,2)"}   # no size -> skipped as existing, not fatal
    good = {"domain": "cwc", "cell": "A(13,6,5)", "size": 18, "witness_sha": "z", "witness": []}
    out = amp.merge_corpus([older], [good])
    assert out == [good]


def test_soak_durability_properties_hold():
    feed = soak.build_feed(target=300)
    res = soak.run_soak(feed)
    assert res["covers_feed_length"]
    assert res["unique_keys"]
    assert res["idempotent"]
    assert res["order_independent"]
    assert res["false_witnesses_audited"] >= 1            # the feed contains false witnesses
    assert res["false_witnesses_verified"] == 0           # ...none counted verified (no kernel anyway)
    assert res["witness_sha_collisions"] == 0


def test_soak_does_not_touch_committed_corpus():
    # build_feed + run_soak are pure (no file writes); only main() writes, and only to amplify_soak.json
    committed = _ROOT / "docs" / "results" / "amplification_corpus.json"
    before = committed.read_text()
    soak.run_soak(soak.build_feed(target=120))
    assert committed.read_text() == before

"""ADR 0069 — arXiv amplification feed tests. CI-safe: no network (fetch is exercised via a
monkeypatched urlopen over a canned Atom document). What we pin down: the finite-core scorer
fires on amplification-shaped abstracts and stays silent on generic ones; Atom parsing;
queue dedup + rendering + the seen-set cap; and that queued entries are framed as TARGETS."""
from __future__ import annotations

import io
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz import arxiv_feed  # noqa: E402

# The shape of the daemon's proven amplifications: srg non-existence (Belousova–Makhnev–
# Tokbaeva), a KS-set refutation (Cabello), a Hadamard census. All must queue.
_SRG = ("On the non-existence of a strongly regular graph",
        "We prove that no strongly regular graph with parameters srg(1666, 105, 0, 21) exists. "
        "The proof is computer-assisted and an exhaustive search certificate is provided.")
_GENERIC = ("Asymptotics of nonlinear parabolic flows",
            "We study long-time behaviour of weak solutions under mild regularity assumptions.")

_ATOM_DOC = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2607.01234v2</id>
    <title>{_SRG[0]}</title>
    <summary>{_SRG[1]}</summary>
    <published>{datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}</published>
    <category term="math.CO"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2607.09999v1</id>
    <title>{_GENERIC[0]}</title>
    <summary>{_GENERIC[1]}</summary>
    <published>2020-01-01T00:00:00Z</published>
    <category term="math.AP"/>
  </entry>
</feed>"""


def test_scorer_fires_on_amplification_shapes_only():
    score, labels = arxiv_feed.finite_core_score(*_SRG)
    assert score >= arxiv_feed.QUEUE_THRESHOLD
    assert "non-existence claim" in labels and "exhaustive/computer search" in labels
    assert arxiv_feed.finite_core_score(*_GENERIC)[0] < arxiv_feed.QUEUE_THRESHOLD
    ks = arxiv_feed.finite_core_score(
        "A smaller Kochen-Specker set", "We exhibit a Kochen-Specker set of 14 bases with an "
        "explicit certificate, verified by computer.")
    assert ks[0] >= arxiv_feed.QUEUE_THRESHOLD


def test_parse_atom_extracts_versionless_ids():
    entries = arxiv_feed.parse_atom(_ATOM_DOC.encode())
    assert [e["id"] for e in entries] == ["2607.01234", "2607.09999"]
    assert entries[0]["link"] == "https://arxiv.org/abs/2607.01234"
    assert entries[0]["categories"] == ["math.CO"]
    assert arxiv_feed.parse_atom(b"not xml at all") == []


def test_fetch_recent_filters_by_date(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, timeout=0, context=None: io.BytesIO(_ATOM_DOC.encode()))
    fresh = arxiv_feed.fetch_recent(days=4)
    assert [e["id"] for e in fresh] == ["2607.01234"]          # the 2020 entry is stale


def test_update_queue_dedups_scores_and_renders(tmp_path):
    entries = arxiv_feed.parse_atom(_ATOM_DOC.encode())
    out = arxiv_feed.update_queue(entries, tmp_path)
    assert out == {"fetched": 2, "queued": 1}                  # generic abstract not queued
    again = arxiv_feed.update_queue(entries, tmp_path)
    assert again == {"fetched": 2, "queued": 0}                # seen-set dedup
    rows = [json.loads(x) for x in (tmp_path / "amplification_queue.jsonl").read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["id"] == "2607.01234" and rows[0]["score"] >= 3
    md = (tmp_path / "amplification_queue.md").read_text()
    assert "TARGETS, not" in md and "2607.01234" in md         # framed as targets, never results
    assert "ADR 0033" in md                                    # publish act stays the operator's
    seen = json.loads((tmp_path / "seen_arxiv.json").read_text())
    assert set(seen) == {"2607.01234", "2607.09999"}


def test_seen_set_is_bounded(tmp_path):
    (tmp_path / "seen_arxiv.json").write_text(
        json.dumps([f"{i:010d}" for i in range(arxiv_feed._SEEN_CAP + 50)]))
    arxiv_feed.update_queue([], tmp_path)
    assert len(json.loads((tmp_path / "seen_arxiv.json").read_text())) <= arxiv_feed._SEEN_CAP

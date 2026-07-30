"""ADR 0084 — extract the STATED finite-core parameters of a queued paper.

Deterministic regex over the paper's own words. The load-bearing property is ANTI-FABRICATION:
every extracted parameter carries the verbatim span it was read from, so a number that is not
literally in the source can never appear. It reports what the paper SAYS; it verifies nothing.
"""
from __future__ import annotations

import json

from leibniz.arxiv_feed import extract_core_parameters as extract
from leibniz.arxiv_feed import queued_targets
from leibniz.seed_intake import construction_task, seed_steering
from leibniz.seeds import SeedKind

# the daemon's OWN amplifications, as they read in an abstract
REAL = [
    ("On the non-existence of a strongly regular graph",
     "We prove that no srg(1666, 105, 0, 21) exists.", "srg_parameters", [1666, 105, 0, 21]),
    ("A smaller Kochen-Specker set",
     "We exhibit a KS set of 14 bases in dimension three.", "basis_count", [14]),
    ("Complex Hadamard matrices", "We construct one of order 94.", "order", [94]),
]


def test_it_extracts_the_shapes_the_daemon_actually_amplifies():
    for title, summary, kind, values in REAL:
        got = extract(title, summary)
        assert any(p["kind"] == kind and p["values"] == values for p in got), (title, got)


def test_every_extracted_value_is_literally_in_the_source():
    """ANTI-FABRICATION. The same discipline seeds.py applies to FLOOR values via proof_of_use."""
    for title, summary, _, _ in REAL:
        source = " ".join(f"{title}\n{summary}".split())
        for p in extract(title, summary):
            assert p["span"] in source                      # the span is verbatim
            for v in p["values"]:
                assert str(v) in source                     # and so is every number


def test_a_number_not_present_is_never_invented():
    got = extract("A paper about srg(16, 6, 2, 2)", "")
    assert got and got[0]["values"] == [16, 6, 2, 2]
    assert all(99999 not in p["values"] for p in got)


def test_no_numbers_means_no_parameters():
    assert extract("Asymptotics of nonlinear parabolic flows",
                   "We study long-time behaviour under mild assumptions.") == []
    assert extract("", "") == []


def test_extraction_never_infers_or_computes():
    """It reports stated values only — no arithmetic, no derived quantities."""
    got = extract("A 3 x 4 matrix", "")
    vals = [v for p in got for v in p["values"]]
    assert 12 not in vals                                   # 3*4 is never produced


def _queue(tmp_path, **over):
    row = {"id": "2607.00001", "title": "On the non-existence of a strongly regular graph",
           "summary": "We prove that no srg(1666, 105, 0, 21) exists.",
           "link": "https://arxiv.org/abs/2607.00001", "score": 4,
           "signals": ["non-existence claim"], "queued_at": "2026-07-28"}
    row.update(over)
    (tmp_path / "amplification_queue.jsonl").write_text(json.dumps(row))
    return tmp_path


def test_parameters_ride_on_the_target_seed_and_change_nothing_else(tmp_path):
    seeds = queued_targets(_queue(tmp_path))
    assert len(seeds) == 1
    s = seeds[0]
    assert s.kind is SeedKind.TARGET                        # still only a proposer hint
    assert construction_task(s) is None                     # still can never run code
    assert s.payload["core_parameters"][0]["values"] == [1666, 105, 0, 21]


def test_the_steering_block_shows_parameters_and_stays_untrusted(tmp_path):
    block = seed_steering(queued_targets(_queue(tmp_path)))
    assert "srg_parameters=(1666, 105, 0, 21)" in block
    assert "stated:" in block                               # framed as what the paper CLAIMS
    assert "UNTRUSTED" in block and "the gates still decide" in block


def test_a_row_without_a_summary_still_works(tmp_path):
    """Rows queued before ADR 0084 have no `summary`; extraction falls back to the title."""
    seeds = queued_targets(_queue(tmp_path, summary=None,
                                  title="Non-existence of srg(1666, 105, 0, 21)"))
    assert seeds[0].payload["core_parameters"][0]["values"] == [1666, 105, 0, 21]

"""ADR 0083 — queued arXiv targets steer the conjecturer, and nothing else.

The feed has been queueing amplification targets nightly since ADR 0069 and NOTHING consumed
them. They now enter the CONJECTURE prompt as VALIDATED TARGET seeds via the ADR 0041 Phase-4
intake, which is proposal-side by construction: a TARGET seed gates nothing and decides nothing.
These tests pin that boundary, not just the plumbing.
"""
from __future__ import annotations

import json

from leibniz.arxiv_feed import queued_targets
from leibniz.discovery import steer
from leibniz.seed_intake import admissible_targets, construction_task, seed_steering
from leibniz.seeds import SeedKind, SeedStatus


def _queue(tmp_path, *rows):
    (tmp_path / "amplification_queue.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows))
    return tmp_path


def _row(i, score=3, title=None):
    return {"id": f"2607.{i:05d}", "title": title or f"paper {i}", "link": f"https://arxiv.org/abs/{i}",
            "score": score, "signals": ["non-existence claim"], "queued_at": f"2026-07-2{i%9}"}


def test_queued_rows_become_validated_target_seeds(tmp_path):
    seeds = queued_targets(_queue(tmp_path, _row(1), _row(2)))
    assert len(seeds) == 2
    for s in seeds:
        assert s.kind is SeedKind.TARGET and s.status is SeedStatus.VALIDATED
        assert s.provenance.source_id.startswith("2607.")     # traceable to the source
        assert s.proof_of_use                                  # anti-fabrication link
    assert admissible_targets(seeds) == seeds


def test_a_target_seed_can_never_become_a_sandbox_job(tmp_path):
    """A TARGET is a hint. Only a CONSTRUCTION seed may run code, and these never are."""
    for s in queued_targets(_queue(tmp_path, _row(1))):
        assert construction_task(s) is None


def test_the_steering_block_declares_itself_untrusted(tmp_path):
    block = seed_steering(queued_targets(_queue(tmp_path, _row(1, title="A non-existence proof"))))
    assert "UNTRUSTED" in block and "the gates still decide" in block
    assert "A non-existence proof" in block


def test_steer_appends_targets_without_disturbing_the_seed(tmp_path):
    block = seed_steering(queued_targets(_queue(tmp_path, _row(1))))
    out = steer("my seed", None, None, block)
    assert out.endswith("Seed: my seed")                       # the seed stays last
    assert "UNTRUSTED" in out
    assert steer("my seed", None, None, "") == "my seed"       # empty -> unchanged (cold start)


def test_the_prompt_cannot_be_flooded_by_a_growing_queue(tmp_path):
    seeds = queued_targets(_queue(tmp_path, *[_row(i) for i in range(20)]), cap=6)
    assert len(seeds) == 6


def test_highest_scoring_targets_come_first(tmp_path):
    seeds = queued_targets(_queue(tmp_path, _row(1, score=2), _row(2, score=9), _row(3, score=5)))
    assert [s.provenance.source_id for s in seeds][0].endswith("00002")


def test_a_missing_or_malformed_queue_yields_nothing(tmp_path):
    assert queued_targets(tmp_path) == []                      # no file
    (tmp_path / "amplification_queue.jsonl").write_text("not json\n{}\n")
    assert queued_targets(tmp_path) == []                      # unusable rows dropped

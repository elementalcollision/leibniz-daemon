"""D6: the Leonardo SURVEY adapter (ADR 0007) — analogy from the Forge, curated
frontier. CI-safe with fixture folios; no live Leonardo dependency."""
from __future__ import annotations

import json

from leibniz.leonardo import LeonardoForgeAdapter


def _make_forge(tmp_path):
    codex = tmp_path / "Codex"
    codex.mkdir()
    (codex / "0001_della_vista.en.md").write_text(
        '---\ndomain: optics\nfolio_ref: "f.0001"\n---\n'
        "The eye is the window of the soul, measuring light and shadow.\n"
    )
    (codex / "0002_del_moto.en.md").write_text(
        "---\ndomain: mechanics\n---\nMotion is the cause of all life; observe the flow of water.\n"
    )
    return tmp_path


def _frontier(tmp_path):
    f = tmp_path / "frontier.json"
    f.write_text(json.dumps({"analysis_of_algorithms": ["sorting bound", "matrix mult exponent"]}))
    return f


def test_survey_frontier_returns_curated_seeds(tmp_path):
    a = LeonardoForgeAdapter(forge_path=tmp_path, frontier_path=_frontier(tmp_path))
    seeds = a.survey_frontier("analysis_of_algorithms")
    assert "sorting bound" in seeds
    assert len(seeds) == 2


def test_survey_frontier_unknown_domain_is_empty(tmp_path):
    a = LeonardoForgeAdapter(forge_path=tmp_path, frontier_path=_frontier(tmp_path))
    assert a.survey_frontier("nonexistent_domain") == []


def test_cross_domain_analogies_from_forge(tmp_path):
    a = LeonardoForgeAdapter(forge_path=_make_forge(tmp_path), frontier_path=_frontier(tmp_path), max_analogies=2)
    out = a.cross_domain_analogies("comparison sort")
    assert len(out) == 2
    assert all(s.startswith("analogy[") for s in out)
    assert any(("optics" in s or "mechanics" in s) for s in out)


def test_cross_domain_analogies_is_deterministic(tmp_path):
    a = LeonardoForgeAdapter(forge_path=_make_forge(tmp_path), frontier_path=_frontier(tmp_path))
    assert a.cross_domain_analogies("X") == a.cross_domain_analogies("X")


def test_missing_forge_returns_empty(tmp_path):
    a = LeonardoForgeAdapter(forge_path=tmp_path / "nope", frontier_path=_frontier(tmp_path))
    assert a.cross_domain_analogies("x") == []


def test_committed_curated_frontier_loads():
    # the committed corpus/frontier.json carries the domain seeds
    seeds = LeonardoForgeAdapter().survey_frontier("analysis_of_algorithms")
    assert any("sorting" in s.lower() for s in seeds)

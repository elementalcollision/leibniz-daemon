"""R3: the known-results corpus matches by structural hash (CI-safe, no Lean).

Uses the committed corpus (hashes precomputed by scripts/build_corpus.py).
"""
from __future__ import annotations

from leibniz.corpus import CorpusBackend
from leibniz.types import ClaimSignature, ClaimType


def _corpus() -> CorpusBackend:
    return CorpusBackend.from_json()


def _sig(formal_hash: str, claim_type=ClaimType.COMPLEXITY_BOUND,
         subject="comparison_sort", relation="lower_bound") -> ClaimSignature:
    return ClaimSignature(claim_type=claim_type, subject=subject,
                          relation=relation, formal_hash=formal_hash)


def test_corpus_contains_the_comparison_sort_bound():
    assert "comparison_sort_lower_bound" in {e.name for e in _corpus().entries}


def test_known_result_recognized_by_structural_hash():
    c = _corpus()
    known_hash = next(e.formal_hash for e in c.entries
                      if e.name == "comparison_sort_lower_bound")
    assert c.contains_equivalent(_sig(known_hash)) is True


def test_novel_hash_is_not_known():
    assert _corpus().contains_equivalent(_sig("deadbeefdeadbeef")) is False


def test_empty_hash_never_matches():
    # A candidate we could not normalize is treated as novel, never silently KNOWN.
    assert _corpus().contains_equivalent(_sig("")) is False


def test_nearest_ranks_exact_structural_match_first():
    c = _corpus()
    known_hash = next(e.formal_hash for e in c.entries
                      if e.name == "comparison_sort_lower_bound")
    neighbours = c.nearest(_sig(known_hash))
    assert neighbours
    assert neighbours[0] == ("comparison_sort_lower_bound", 1.0)

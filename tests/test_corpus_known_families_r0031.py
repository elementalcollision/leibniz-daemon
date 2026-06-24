"""ADR 0031 Layer 1: the rebuilt corpus contains the elementary-number-theory families the
organic run rediscovered, so a re-conjecture of a canonical form is caught KNOWN by the exact
elaborator-hash. (Layer 2's decision-procedure equivalence was retracted as unsound — see the
ADR; novelty stays on exact-hash + non-triviality.)
"""
from __future__ import annotations

from leibniz.corpus import CorpusBackend


def test_corpus_contains_the_number_theory_families():
    corpus = CorpusBackend.from_json()
    by_name = {e.name: e for e in corpus.entries}
    for name in ("fermat_little_3", "fermat_little_5", "fermat_little_7",
                 "cube_residue_mod_six", "four_consec_div_24", "even_pair_div_eight"):
        assert name in by_name, f"{name} missing from rebuilt corpus"
        assert by_name[name].formal_hash           # Layer 1: structural hash present


def test_corpus_hashes_match_the_organic_run_canonical_promulgations():
    # the seeded canonical forms hash to exactly what the organic run promulgated, so a
    # re-conjecture now hits KNOWN by exact hash (sanity that build_corpus is consistent).
    by_name = {e.name: e.formal_hash for e in CorpusBackend.from_json().entries}
    assert by_name["fermat_little_5"] == "481f97bc10ad5ee7"
    assert by_name["fermat_little_7"] == "a559a9d18c401b89"
    assert by_name["cube_residue_mod_six"] == "e1d9d53277a3378c"

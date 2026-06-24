"""ADR 0031 activation: the rebuilt corpus catches the families the organic run rediscovered.

The organic panel run promulgated Fermat's little theorem (p=3,5,7) and elementary
divisibilities as "novel". With the elementary-number-theory entries now in the corpus
(Layer 1) and decision-procedure equivalence (Layer 2), those are caught KNOWN — by exact
hash for the canonical forms, by equivalence for restatements.
"""
from __future__ import annotations

import pytest

from leibniz.backends.smt_z3 import available as z3_available
from leibniz.corpus import CorpusBackend


def test_corpus_contains_the_number_theory_families_with_predicates():
    corpus = CorpusBackend.from_json()
    by_name = {e.name: e for e in corpus.entries}
    for name in ("fermat_little_3", "fermat_little_5", "fermat_little_7",
                 "cube_residue_mod_six", "four_consec_div_24", "even_pair_div_eight"):
        assert name in by_name, f"{name} missing from rebuilt corpus"
        e = by_name[name]
        assert e.formal_hash                       # Layer 1: structural hash present
        assert e.claim_property                    # Layer 2: DSL predicate present


@pytest.mark.z3
@pytest.mark.skipif(not z3_available(), reason="z3-solver (verify extra) not installed")
def test_real_corpus_catches_a_fermat_restatement_by_equivalence():
    from leibniz.backends.smt_z3 import Z3Backend
    corpus = CorpusBackend.from_json()
    # a RESTATEMENT whose hash differs from any entry, but which is box-equivalent to Fermat-5
    match = corpus.equivalent_known("n >= 0", "(n^5 + 4*n) % 5 == 0", Z3Backend(),
                                    claim_type="invariant")
    assert match == "fermat_little_5"

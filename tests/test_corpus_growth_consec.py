"""Corpus growth: consecutive-product / sum-of-squares families the daemon kept rediscovering.

organic3/organic4 repeatedly promulgated pedestrian restatements of textbook divisibilities
(n(n+1)(2n+1)÷6, four-consecutive ÷8/÷4) that the 48-entry corpus did not know, so the novelty
gate let them through as false-NOVEL. These three KNOWN facts close that gap. CI-safe (no Lean):
structural matching needs only claim_property -> congruence_signature.

Soundness: each added fact is true + textbook, and distinct polynomials/moduli get distinct
signatures, so this can only demote restatements of these exact facts — never a different
discovery (no false-KNOWN). The build_corpus.py source list and corpus/known_results.json carry
the same entries (regenerated together).
"""
from __future__ import annotations

from leibniz.corpus import CorpusBackend

_NEW = {"sumsq_numerator_div_six", "four_consec_div_eight", "four_consec_div_four"}


def test_new_entries_present():
    names = {e.name for e in CorpusBackend.from_json().entries}
    assert _NEW <= names


def test_genre_now_caught_tight_loose_and_vacuous_offset():
    cb = CorpusBackend.from_json()
    # n(n+1)(2n+1) ÷ 6 (organic3 #0) — tight, loose-membership, and formally-vacuous offset (#13)
    assert cb.structural_known("n * (n + 1) * (2 * n + 1) % 6 == 0") == "sumsq_numerator_div_six"
    assert cb.structural_known("n*(n+1)*(2*n+1) % 6 in {0}") == "sumsq_numerator_div_six"
    assert cb.structural_known("(n*(n+1)*(2*n+1) + 6*n*(n+1)) % 6 == 0") == "sumsq_numerator_div_six"
    # four consecutive ÷ 8 (organic3 #4) — tight and loose-membership (#9: actual residues {0})
    assert cb.structural_known("n*(n+1)*(n+2)*(n+3) % 8 == 0") == "four_consec_div_eight"
    assert cb.structural_known("n*(n+1)*(n+2)*(n+3) % 8 in {0,4}") == "four_consec_div_eight"
    assert cb.structural_known("n*(n+1)*(n+2)*(n+3) % 4 == 0") == "four_consec_div_four"


def test_no_false_known_distinct_polynomials_stay_novel():
    cb = CorpusBackend.from_json()
    # genuinely different facts must NOT match the new entries
    assert cb.structural_known("n*(n+1)*(n+2) % 8 == 0") is None          # 3-consec ≠ 4-consec at mod 8
    assert cb.structural_known("n*(n+1)*(2*n+1) % 12 == 0") is None       # same poly, different modulus
    assert cb.structural_known("n*(n+1)*(2*n+1)*(3*n+1) % 6 == 0") is None  # a different polynomial


def test_new_entries_occupy_unique_signatures():
    from leibniz.structural import congruence_signature as sig
    cb = CorpusBackend.from_json()
    by_sig: dict = {}
    for e in cb.entries:
        if e.claim_property:
            s = sig(e.claim_property)
            if s is not None:
                by_sig.setdefault(s, []).append(e.name)
    # Each NEW entry must occupy a signature shared with NOTHING else — a collision would mean a
    # genuinely-different congruence gets wrongly demoted as this known (false-KNOWN). (Pre-existing
    # same-fact aliases like fermat_little_2 / two_consec_div_two are fine; the new ones must not
    # join any such group.)
    for name in _NEW:
        group = next(names for names in by_sig.values() if name in names)
        assert group == [name], f"{name} shares a signature with {group}"

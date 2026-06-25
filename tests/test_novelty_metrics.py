"""ADR 0034 Stage 0: the read-only novelty metric (CI-safe; pure, no Z3/Lean/LLM).

The metric is instrumentation, not a gate. These tests pin its arithmetic (distance axes,
coverage, clustering, nearest-neighbour) on SYNTHETIC inputs with known signatures, and assert
the Prohibition-1 property that the module exposes NO accept/reject surface. The real corpus is
touched only for structure-invariant smoke checks (no hardcoded counts — the corpus grows).
"""
from __future__ import annotations

import inspect

from leibniz import novelty_metrics as nm

# Known signatures (see structural.py): same congruence, different phrasing -> same signature.
EVEN_SQ = "(n^2) % 2 == 0"
EVEN_CUBE = "(n^3) % 2 == 0"
SQ_MOD3 = "(n^2) % 3 == 0"
FERMAT_A = "(n^5 + 4*n) % 5 == 0"      # n^5 ≡ n (mod 5)
FERMAT_B = "n^5 % 5 == n % 5"          # same congruence, different phrasing
PROSE = "the sky is structurally blue"  # not a congruence -> None signature


# --- distance ---------------------------------------------------------------

def _sig(p):
    return nm.congruence_signature(p)


def test_distance_identity_zero_and_symmetric():
    a = _sig(EVEN_SQ)
    assert nm.signature_distance(a, a) == 0.0
    b = _sig(SQ_MOD3)
    assert nm.signature_distance(a, b) == nm.signature_distance(b, a)


def test_distance_in_unit_interval():
    sigs = [_sig(p) for p in (EVEN_SQ, EVEN_CUBE, SQ_MOD3, FERMAT_A)]
    for a in sigs:
        for b in sigs:
            d = nm.signature_distance(a, b)
            assert 0.0 <= d <= 1.0


def test_distance_axes_modulus_vs_shape():
    # differ only in modulus -> 1/5 of the axes -> 0.2
    assert nm.signature_distance(_sig(EVEN_SQ), _sig(SQ_MOD3)) == 0.2
    # differ in shape AND coefficients -> 2/5 -> 0.4 (shape counts more than a coeff-only change)
    assert nm.signature_distance(_sig(EVEN_SQ), _sig(EVEN_CUBE)) == 0.4


def test_distance_zero_iff_same_congruence_across_phrasings():
    # the canonicaliser folds two phrasings of n^5 ≡ n (mod 5) onto one signature -> distance 0
    assert _sig(FERMAT_A) == _sig(FERMAT_B)
    assert nm.signature_distance(_sig(FERMAT_A), _sig(FERMAT_B)) == 0.0
    # a genuinely different congruence is strictly positive
    assert nm.signature_distance(_sig(FERMAT_A), _sig(EVEN_SQ)) > 0.0


# --- profile ----------------------------------------------------------------

def test_coverage_counts_none_in_denominator():
    prof = nm.profile([EVEN_SQ, SQ_MOD3, PROSE, None])
    assert prof["n_total"] == 4
    assert prof["n_covered"] == 2          # the two real congruences
    assert prof["coverage"] == 0.5          # None / prose are in the denominator, not covered


def test_clusters_and_zero_nearest_for_duplicate_signature():
    # EVEN_SQ and FERMAT_B-phrased-as-EVEN are distinct; add a true duplicate of EVEN_SQ.
    prof = nm.profile([EVEN_SQ, "(n^2) % 2 == 0", SQ_MOD3])
    assert prof["distinct_clusters"] == 2          # the two EVEN_SQ collapse to one signature
    assert prof["nearest_distances"][0] == 0.0     # the duplicates are at distance 0
    assert prof["distance_summary"]["min"] == 0.0


def test_reference_set_is_used_for_nearest_neighbour():
    # a single subject whose only neighbour lives in `reference`
    prof = nm.profile([EVEN_SQ], reference=[SQ_MOD3])
    assert prof["isolated"] == 0
    assert prof["nearest_distances"] == [0.2]      # distance to the reference entry


def test_isolated_point_has_no_neighbour():
    prof = nm.profile([EVEN_SQ])                    # no others, no reference
    assert prof["isolated"] == 1
    assert prof["nearest_distances"] == []
    assert prof["distance_summary"] == {}


def test_empty_input_is_safe():
    prof = nm.profile([])
    assert prof["n_total"] == 0 and prof["coverage"] == 0.0
    assert prof["distinct_clusters"] == 0 and prof["nearest_distances"] == []


# --- Prohibition 1: measurement only, no gate surface (ADR 0034 §6) ---------

def test_module_exposes_no_accept_reject_surface():
    banned = ("accept", "reject", "quarantine", "drop", "filter", "gate", "decide",
              "prune", "promote", "demote", "is_novel", "should")
    names = [n for n, _ in inspect.getmembers(nm, callable) if not n.startswith("_")]
    offenders = [n for n in names if any(b in n.lower() for b in banned)]
    assert offenders == [], f"novelty_metrics must decide nothing; found {offenders}"


def test_profile_returns_plain_data_no_verdict_keys():
    prof = nm.profile([EVEN_SQ, SQ_MOD3])
    assert set(prof) == {
        "n_total", "n_covered", "coverage", "distinct_clusters",
        "nearest_distances", "distance_summary", "isolated",
    }  # data only; no pass/fail/verdict/accept key


# --- real corpus: structural invariants only (no hardcoded, growth-sensitive counts) -------

def test_corpus_profile_structural_invariants():
    from leibniz.corpus import CorpusBackend
    props = [e.claim_property for e in CorpusBackend.from_json().entries if e.claim_property]
    prof = nm.profile(props)
    assert prof["n_total"] > 0
    assert 0.0 < prof["coverage"] <= 1.0
    assert prof["distinct_clusters"] <= prof["n_covered"] <= prof["n_total"]
    assert all(0.0 <= d <= 1.0 for d in prof["nearest_distances"])

"""ADR 0013 §2: provenance on the faithfulness/novelty edges (CI-safe).

A non-JUDGED edge may not carry a judge producer (a judged verdict mislabeled
mechanical); the gates now stamp producers so this is enforced structurally.
"""
from __future__ import annotations

import pytest

from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.trust import (
    FAITHFULNESS_EDGE,
    JUDGE_PRODUCER,
    NOVELTY_EDGE,
    TrustPolicy,
    TrustViolation,
)
from leibniz.types import ClaimSignature, ClaimType, EdgeEvidence, TrustTier, Verdict


# --- validate_edge generalization --------------------------------------------

def test_mechanical_edge_with_judge_producer_is_rejected():
    with pytest.raises(TrustViolation):
        TrustPolicy().validate_edge(
            EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS, producer=JUDGE_PRODUCER)
        )


def test_judged_edge_with_judge_producer_is_allowed():
    TrustPolicy().validate_edge(
        EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.JUDGED, Verdict.PASS, producer=JUDGE_PRODUCER)
    )  # the one legitimate place a judge appears — must not raise


def test_mechanical_edge_with_non_judge_producer_is_fine():
    TrustPolicy().validate_edge(
        EdgeEvidence(NOVELTY_EDGE, TrustTier.MECHANICAL, Verdict.PASS, producer="CorpusBackend")
    )


# --- the gates actually stamp producers --------------------------------------

class _NoWitnessSMT:
    class backend:
        @staticmethod
        def find_gaming_witness(statement, negated_claim, bound):
            return None


def _prop(claim_type):
    return Propositio(
        enuntiatio=Enuntiatio(statement="x", claim_type=claim_type, falsifiable_claim="y"),
        expressio=Expressio(theorem_src="theorem t : P"),
    )


def test_faithfulness_defer_edge_is_stamped_non_judge():
    from leibniz.gates.faithfulness import FaithfulnessGate
    ev = FaithfulnessGate(smt=_NoWitnessSMT(), probes={}, judge=None).check(_prop(ClaimType.COMPLEXITY_BOUND))
    assert ev.verdict is Verdict.DEFER
    assert ev.producer == "FaithfulnessGate"
    TrustPolicy().validate_edge(ev)  # mechanical + non-judge producer -> ok


def test_faithfulness_judged_edge_is_stamped_and_accepted():
    from leibniz.gates.faithfulness import FaithfulnessGate

    class _Judge:
        def round_trip_agrees(self, prop):
            return 0.95

    ev = FaithfulnessGate(smt=_NoWitnessSMT(), probes={}, judge=_Judge()).check(_prop(ClaimType.OPEN_FORM))
    assert ev.tier is TrustTier.JUDGED and ev.producer == JUDGE_PRODUCER
    TrustPolicy().validate_edge(ev)  # judged + judge producer -> ok


def test_novelty_trivial_edge_is_stamped():
    from leibniz.gates.novelty import NoveltyGate

    class _Lean:
        def is_trivial(self, expr):
            return True

    class _Corpus:
        def contains_equivalent(self, sig):
            return False

        def nearest(self, sig, k=5):
            return []

    prop = _prop(ClaimType.COMPLEXITY_BOUND)
    prop.signature = ClaimSignature(claim_type=ClaimType.COMPLEXITY_BOUND, subject="s", relation="r", formal_hash="h")
    ev = NoveltyGate(_Corpus(), _Lean()).check(prop)
    assert ev.producer == "LeanVerifier.is_trivial"
    TrustPolicy().validate_edge(ev)

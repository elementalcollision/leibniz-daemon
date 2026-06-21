"""ADR 0013: trust-edge provenance hardening (CI-safe).

A proof edge that names a producer must be the kernel's; a mislabel is rejected
structurally, not by honest tagging. Unstamped (legacy) edges are unaffected, so
the 11 invariant tests stay byte-identical and green.
"""
from __future__ import annotations

import pytest

from leibniz.propositio import Demonstratio, Expressio
from leibniz.trust import (
    FAITHFULNESS_EDGE,
    KERNEL_PRODUCER,
    NOVELTY_EDGE,
    PROOF_EDGE,
    TrustPolicy,
    TrustViolation,
)
from leibniz.types import EdgeEvidence, TrustTier, Verdict
from leibniz.verifiers import LeanVerifier

MECH = TrustTier.MECHANICAL
JUDGED = TrustTier.JUDGED


def _edges(proof_producer=None):
    return [
        EdgeEvidence(NOVELTY_EDGE, MECH, Verdict.PASS),
        EdgeEvidence(FAITHFULNESS_EDGE, MECH, Verdict.PASS),
        EdgeEvidence(PROOF_EDGE, MECH, Verdict.PASS, producer=proof_producer),
    ]


class _FakeBackend:
    def check_proof(self, expr, proof_src):
        return True

    def compile_statement(self, expr):
        return True

    def closed_by_decision_procedure(self, expr):
        return False


def test_discharge_stamps_kernel_provenance():
    demo = Demonstratio(proof_obligation="t", proof_src="by x")
    ev = LeanVerifier(_FakeBackend()).discharge(Expressio(theorem_src="theorem t : P"), demo)
    assert ev.producer == KERNEL_PRODUCER


def test_proof_edge_with_foreign_producer_is_rejected():
    with pytest.raises(TrustViolation):
        TrustPolicy().validate_path(_edges(proof_producer="some_llm_judge"))


def test_kernel_producer_passes():
    TrustPolicy().validate_path(_edges(proof_producer=KERNEL_PRODUCER))  # must not raise


def test_unstamped_edges_are_backward_compatible():
    # what the 11 invariant tests rely on: producer=None never trips provenance
    TrustPolicy().validate_path(_edges(proof_producer=None))  # must not raise


def test_mutation_flipping_proof_tier_still_raises():
    edges = _edges(proof_producer=KERNEL_PRODUCER)
    edges[2] = EdgeEvidence(PROOF_EDGE, JUDGED, Verdict.PASS, producer=KERNEL_PRODUCER)
    with pytest.raises(TrustViolation):
        TrustPolicy().validate_path(edges)

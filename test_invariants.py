"""Executable trust invariants.

CLAUDE.md states these rules for the agent's benefit, but a memory file is
*context, not enforcement*. This file is the enforcement: it turns each
non-negotiable invariant into a test that fails CI if a future change breaks it.

If you are Claude Code and a change you are about to make would require editing
this file to make it pass, STOP -- you are about to weaken the trust boundary.
Surface the change to the operator instead.

Run:  pytest -q
"""

from __future__ import annotations

import pytest

from leibniz.gates.verification import VerificationGate
from leibniz.propositio import Demonstratio, Enuntiatio, Propositio
from leibniz.trust import (
    FAITHFULNESS_EDGE,
    NOVELTY_EDGE,
    PROOF_EDGE,
    TrustPolicy,
    TrustViolation,
)
from leibniz.types import ClaimType, EdgeEvidence, TrustTier, Verdict


def _enuntiatio() -> Enuntiatio:
    return Enuntiatio(
        statement="comparison sort lower bound",
        claim_type=ClaimType.COMPLEXITY_BOUND,
        falsifiable_claim="exists comparison sort beating n log n",
    )


def _passing_edges(proof_tier: TrustTier = TrustTier.MECHANICAL,
                   novelty_tier: TrustTier = TrustTier.MECHANICAL,
                   faith_tier: TrustTier = TrustTier.MECHANICAL):
    return [
        EdgeEvidence(NOVELTY_EDGE, novelty_tier, Verdict.PASS),
        EdgeEvidence(FAITHFULNESS_EDGE, faith_tier, Verdict.PASS),
        EdgeEvidence(PROOF_EDGE, proof_tier, Verdict.PASS),
    ]


# --- INVARIANT 1: a proof may only be settled by the kernel (MECHANICAL) -------

def test_proof_edge_must_be_mechanical():
    policy = TrustPolicy()
    bad = _passing_edges(proof_tier=TrustTier.JUDGED)
    with pytest.raises(TrustViolation):
        policy.validate_path(bad)


def test_proof_edge_adversarial_also_rejected():
    policy = TrustPolicy()
    bad = _passing_edges(proof_tier=TrustTier.ADVERSARIAL)
    with pytest.raises(TrustViolation):
        policy.validate_path(bad)


# --- INVARIANT 2: novelty is never settled by an LLM judge ---------------------

def test_novelty_edge_may_not_be_judged():
    policy = TrustPolicy()
    bad = _passing_edges(novelty_tier=TrustTier.JUDGED)
    with pytest.raises(TrustViolation):
        policy.validate_path(bad)


# --- INVARIANT 3: no promotion without a proof edge present --------------------

def test_promotion_requires_a_proof_edge():
    policy = TrustPolicy()
    no_proof = [
        EdgeEvidence(NOVELTY_EDGE, TrustTier.MECHANICAL, Verdict.PASS),
        EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS),
    ]
    with pytest.raises(TrustViolation):
        policy.validate_path(no_proof)


def test_promotion_requires_a_faithfulness_edge():
    policy = TrustPolicy()
    no_faith = [
        EdgeEvidence(NOVELTY_EDGE, TrustTier.MECHANICAL, Verdict.PASS),
        EdgeEvidence(PROOF_EDGE, TrustTier.MECHANICAL, Verdict.PASS),
    ]
    with pytest.raises(TrustViolation):
        policy.validate_path(no_faith)


# --- INVARIANT 4: a non-PASS edge can never promote ---------------------------

def test_non_pass_edge_blocks_promotion():
    policy = TrustPolicy()
    deferred = _passing_edges()
    deferred[1] = EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.DEFER)
    with pytest.raises(TrustViolation):
        policy.validate_path(deferred)


# --- INVARIANT 5: JUDGED faithfulness is allowed but flagged as residual -------

def test_judged_faithfulness_is_permitted_but_detectable():
    policy = TrustPolicy()
    edges = _passing_edges(faith_tier=TrustTier.JUDGED)
    policy.validate_path(edges)  # must NOT raise -- the one permitted judged edge
    assert TrustPolicy.is_judged_faithfulness(edges) is True


# --- INVARIANT 6: Q.E.D. is earned by the kernel, never hand-set ---------------

def test_qed_requires_kernel_verification():
    demo = Demonstratio(proof_obligation="comparison_sort_lower_bound")
    demo.kernel_verified = False
    demo.seal()
    assert demo.qed == "Q.E.I."

    demo.kernel_verified = True
    demo.seal()
    assert demo.qed == "Q.E.D."


# --- INVARIANT 7: the gate's verdict is a pure function of recorded evidence ----

def test_is_promotable_true_only_on_complete_mechanical_path():
    gate = VerificationGate(TrustPolicy())
    prop = Propositio(enuntiatio=_enuntiatio())
    for ev in _passing_edges():
        prop.record(ev)
    assert gate.is_promotable(prop) is True


def test_is_promotable_false_when_proof_is_judged():
    gate = VerificationGate(TrustPolicy())
    prop = Propositio(enuntiatio=_enuntiatio())
    for ev in _passing_edges(proof_tier=TrustTier.JUDGED):
        prop.record(ev)
    # validate_path raises internally -> gate returns False rather than promoting.
    assert gate.is_promotable(prop) is False


def test_is_promotable_false_without_proof():
    gate = VerificationGate(TrustPolicy())
    prop = Propositio(enuntiatio=_enuntiatio())
    prop.record(EdgeEvidence(NOVELTY_EDGE, TrustTier.MECHANICAL, Verdict.PASS))
    prop.record(EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS))
    assert gate.is_promotable(prop) is False

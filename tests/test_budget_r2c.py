"""R2c: the judged-faithfulness budget is actually enforced (ADR 0001 §5).

Pure stdlib — always runs in CI. The 0.15 fraction was previously declared but
never counted; these pin that a judged-faithfulness promulgation is refused once
it would push the residual past budget.
"""
from __future__ import annotations

from leibniz.budget import TrustBudget
from leibniz.trust import FAITHFULNESS_EDGE, NOVELTY_EDGE, PROOF_EDGE, TrustPolicy
from leibniz.types import EdgeEvidence, TrustTier, Verdict

MECH = TrustTier.MECHANICAL
JUDGED = TrustTier.JUDGED


def _edges(faith_tier: TrustTier):
    return [
        EdgeEvidence(NOVELTY_EDGE, MECH, Verdict.PASS),
        EdgeEvidence(FAITHFULNESS_EDGE, faith_tier, Verdict.PASS),
        EdgeEvidence(PROOF_EDGE, MECH, Verdict.PASS),
    ]


# --- the pure policy arithmetic ----------------------------------------------

def test_admits_judged_arithmetic():
    p = TrustPolicy()  # 0.15
    assert p.admits_judged_faithfulness(0, 0) is False   # 1/1 = 100%
    assert p.admits_judged_faithfulness(0, 6) is True     # 1/7 ≈ 14.3%
    assert p.admits_judged_faithfulness(1, 7) is False    # 2/8 = 25%


# --- the stateful counter -----------------------------------------------------

def test_mechanical_faithfulness_always_admitted():
    b = TrustBudget(TrustPolicy())
    for _ in range(20):
        assert b.try_admit(_edges(MECH)) is True
    assert b.judged == 0 and b.total == 20


def test_first_judged_on_empty_ledger_is_refused_and_not_recorded():
    b = TrustBudget(TrustPolicy())
    assert b.try_admit(_edges(JUDGED)) is False
    assert b.total == 0 and b.judged == 0  # refused -> nothing recorded


def test_judged_admitted_once_ledger_is_large_enough_then_capped():
    b = TrustBudget(TrustPolicy())
    for _ in range(6):
        b.try_admit(_edges(MECH))  # total = 6
    assert b.try_admit(_edges(JUDGED)) is True   # 1/7 within budget
    assert (b.judged, b.total) == (1, 7)
    # a second judged immediately would be 2/8 = 25% > 15% -> refused, not recorded
    assert b.try_admit(_edges(JUDGED)) is False
    assert (b.judged, b.total) == (1, 7)
    assert b.fraction() <= TrustPolicy().max_judged_faithfulness_fraction

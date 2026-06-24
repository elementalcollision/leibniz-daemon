"""CI-safe tests for the prover A/B attribution math (scripts/ab_prover_reach.py).

The reach RUN is billable (LLM + Lean), but the conclusion-bearing attribution — does the
candidate prover unlock goals the incumbent set misses, and where is it decisive — is pure and
must be trustworthy, so it is tested here. No network, no Lean.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "ab_prover_reach", Path(__file__).resolve().parent.parent / "scripts" / "ab_prover_reach.py")
ab = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ab)

DS = "model:deepseek/deepseek-prover-v2"
OPUS = "model:anthropic/claude-opus-4-8"
GOEDEL = "model:Goedel-LM/Goedel-Prover-V2-32B"
CAND = {"Goedel-LM/Goedel-Prover-V2-32B"}


def _arm(reached, ids, count, required=2):
    return {"reached": reached, "identities": ids, "count": count, "required": required}


def test_candidate_models_is_b_minus_a_stripping_gateway():
    a = "deepseek/deepseek-prover-v2,deepseek/deepseek-prover-v2,anthropic/claude-opus-4-8"
    b = "deepseek/deepseek-prover-v2,Goedel-LM/Goedel-Prover-V2-32B@featherless,anthropic/claude-opus-4-8"
    assert ab._candidate_models(a, b) == {"Goedel-LM/Goedel-Prover-V2-32B"}  # @featherless stripped


def test_no_candidate_when_b_subset_of_a():
    a = "x,y,z"
    assert ab._candidate_models(a, "x,y") == set()


def test_summary_attribution_and_decisiveness():
    rows = [
        # g1: both arms reach via deepseek+opus -> not a B-only unlock
        {"goal": "g1", "a": _arm(True, [DS, OPUS], 2), "b": _arm(True, [DS, OPUS], 2)},
        # g2: A misses (only deepseek), B reaches via deepseek+GOEDEL at exactly the bar -> B-only,
        #     candidate closed it AND was decisive (count==required)
        {"goal": "g2", "a": _arm(False, [DS], 1), "b": _arm(True, [DS, GOEDEL], 2)},
        # g3: A reaches, B misses -> an A-only regression
        {"goal": "g3", "a": _arm(True, [DS, OPUS], 2), "b": _arm(False, [DS], 1)},
        # g4: both reach; B over-shoots the bar (deepseek+opus+GOEDEL, count 3) -> goedel a closer
        #     but NOT decisive (count>required), and not a B-only unlock
        {"goal": "g4", "a": _arm(True, [DS, OPUS], 2), "b": _arm(True, [DS, OPUS, GOEDEL], 3)},
    ]
    s = ab.summarize_ab(rows, CAND)
    assert s["goals"] == 4
    assert s["reached_A"] == 3 and s["reached_B"] == 3
    assert s["b_only_unlocks"] == 1            # g2
    assert s["a_only_regressions"] == 1        # g3
    assert s["candidate_closed_b_only"] == 1   # goedel closed g2 (which A missed)
    assert s["candidate_decisive"] == 1        # g2 only (g4 over-shoots the bar)
    assert s["closes_per_prover_B"] == {
        "anthropic/claude-opus-4-8": 2,
        "Goedel-LM/Goedel-Prover-V2-32B": 2,
        "deepseek/deepseek-prover-v2": 4,
    }
    assert s["closes_per_prover_A"]["deepseek/deepseek-prover-v2"] == 4
    assert s["closes_per_prover_A"]["anthropic/claude-opus-4-8"] == 3


def test_preflight_passes_when_all_reachable():
    avail_a = {"deepseek/deepseek-prover-v2", "anthropic/claude-opus-4-8"}
    avail_b = {"deepseek/deepseek-prover-v2", "Goedel-LM/Goedel-Prover-V2-32B", "anthropic/claude-opus-4-8"}
    assert ab.preflight(avail_a, avail_b, CAND, required=2) == []


def test_preflight_aborts_when_candidate_unreachable():
    # Goedel's key/URL is wrong -> it isn't in arm B's available set -> the A/B is meaningless.
    avail_a = {"deepseek/deepseek-prover-v2", "anthropic/claude-opus-4-8"}
    avail_b = {"deepseek/deepseek-prover-v2", "anthropic/claude-opus-4-8"}  # no goedel
    probs = ab.preflight(avail_a, avail_b, CAND, required=2)
    assert any("Goedel-LM/Goedel-Prover-V2-32B" in p and "reachable in arm B" in p for p in probs)


def test_preflight_aborts_when_an_arm_cannot_reach_consensus():
    # Only one voter available in an arm -> can never hit N+1=2.
    one = {"deepseek/deepseek-prover-v2"}
    full = {"deepseek/deepseek-prover-v2", "Goedel-LM/Goedel-Prover-V2-32B", "anthropic/claude-opus-4-8"}
    probs = ab.preflight(one, full, CAND, required=2)
    assert any("arm A has only 1 available distinct voter" in p for p in probs)


def test_liveness_all_alive_no_problems():
    res = {"anthropic/claude-opus-4-8": (True, "12 chars"),
           "Goedel-LM/Goedel-Prover-V2-32B": (True, "10 chars")}
    assert ab.liveness_problems(res, CAND) == []


def test_liveness_dead_candidate_is_fatal():
    res = {"anthropic/claude-opus-4-8": (True, "ok"),
           "Goedel-LM/Goedel-Prover-V2-32B": (False, "HTTPError: 404")}
    probs = ab.liveness_problems(res, CAND)
    assert len(probs) == 1 and "CANDIDATE" in probs[0] and "Goedel" in probs[0]


def test_liveness_dead_incumbent_is_also_flagged():
    # deepseek-prover-v2 404 (the real bug) must be flagged even when it isn't the candidate.
    res = {"deepseek/deepseek-prover-v2": (False, "HTTPError: 404 Not Found"),
           "anthropic/claude-opus-4-8": (True, "ok")}
    probs = ab.liveness_problems(res, CAND)
    assert any("deepseek/deepseek-prover-v2" in p and "404" in p for p in probs)
    assert all("CANDIDATE" not in p for p in probs)  # not tagged candidate (it isn't one)


def test_default_arms_drop_deepseek_and_test_goedel():
    # the post-mortem default: control = opus alone, treatment adds Goedel; candidate = {Goedel}
    assert ab._candidate_models(ab._DEFAULT_A, ab._DEFAULT_B) == {"Goedel-LM/Goedel-Prover-V2-32B"}
    assert "deepseek" not in ab._DEFAULT_A and "deepseek" not in ab._DEFAULT_B


def test_useless_candidate_shows_zero_unlocks():
    # If the candidate never closes anything A didn't already, the A/B says so plainly.
    rows = [
        {"goal": "g1", "a": _arm(True, [DS, OPUS], 2), "b": _arm(True, [DS, OPUS], 2)},
        {"goal": "g2", "a": _arm(False, [DS], 1), "b": _arm(False, [DS], 1)},  # goedel didn't help
    ]
    s = ab.summarize_ab(rows, CAND)
    assert s["b_only_unlocks"] == 0
    assert s["candidate_closed_b_only"] == 0
    assert s["candidate_decisive"] == 0
    assert "Goedel-LM/Goedel-Prover-V2-32B" not in s["closes_per_prover_B"]

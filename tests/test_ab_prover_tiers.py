"""CI-safe tests for the difficulty-tiered A/B prover extension (scripts/ab_prover_tiers.py).

Tests cover:
- Tier-file loader validation (pure, no I/O beyond reading a temp JSON)
- Per-tier aggregation logic (pure math over mock rows)
- Plateau detection (pure)

Nothing billable is touched — no network, no Lean, no LLM.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "ab_prover_tiers",
    Path(__file__).resolve().parent.parent / "scripts" / "ab_prover_tiers.py",
)
tiers_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(tiers_mod)

load_tier_file = tiers_mod.load_tier_file
aggregate_tiers = tiers_mod.aggregate_tiers
plateau_tier = tiers_mod.plateau_tier
TierFileError = tiers_mod.TierFileError

# Pull summarize_ab from ab_prover_reach via the already-imported module attr
summarize_ab = tiers_mod.summarize_ab

OPUS = "model:anthropic/claude-opus-4-8"
GOEDEL = "model:Goedel-LM/Goedel-Prover-V2-32B"
CAND = {"Goedel-LM/Goedel-Prover-V2-32B"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _arm(reached, ids, count, required=2):
    return {"reached": reached, "identities": ids, "count": count, "required": required}


def _write_json(tmp_path: str, obj: dict) -> str:
    p = Path(tmp_path) / "tiered.json"
    p.write_text(json.dumps(obj))
    return str(p)


# ---------------------------------------------------------------------------
# load_tier_file
# ---------------------------------------------------------------------------

def test_load_valid_tiered_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_json(tmp, {
            "_meta": {"note": "starter"},
            "T0": [{"theorem_src": "theorem foo : True", "imports": ["Mathlib.Tactic"]}],
            "T1": [{"theorem_src": "theorem bar (n : ℕ) : n = n", "imports": ["Mathlib.Tactic"]}],
        })
        result = load_tier_file(path)
    assert "T0" in result and "T1" in result
    assert result["T0"][0]["theorem_src"] == "theorem foo : True"
    # _meta should be excluded from tier dict
    assert "_meta" not in result


def test_load_ignores_meta_keys():
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_json(tmp, {
            "_meta": {"note": "ignored"},
            "_version": "1.0",
            "T0": [{"theorem_src": "theorem g : True", "imports": []}],
        })
        result = load_tier_file(path)
    assert set(result.keys()) == {"T0"}


def test_load_rejects_missing_theorem_src():
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_json(tmp, {
            "T0": [{"imports": ["Mathlib.Tactic"]}],  # no theorem_src
        })
        try:
            load_tier_file(path)
            assert False, "should have raised"
        except TierFileError as e:
            assert "theorem_src" in str(e)


def test_load_rejects_non_list_imports():
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_json(tmp, {
            "T0": [{"theorem_src": "theorem g : True", "imports": "Mathlib.Tactic"}],
        })
        try:
            load_tier_file(path)
            assert False, "should have raised"
        except TierFileError as e:
            assert "imports" in str(e)


def test_load_rejects_non_list_tier():
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_json(tmp, {"T0": "not a list"})
        try:
            load_tier_file(path)
            assert False, "should have raised"
        except TierFileError as e:
            assert "list" in str(e)


def test_load_rejects_bad_json():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "bad.json"
        p.write_text("{not valid json}")
        try:
            load_tier_file(str(p))
            assert False, "should have raised"
        except TierFileError as e:
            assert "invalid JSON" in str(e)


def test_load_rejects_missing_file():
    try:
        load_tier_file("/nonexistent/path/tiered.json")
        assert False, "should have raised"
    except TierFileError as e:
        assert "cannot read" in str(e)


def test_load_rejects_no_tier_keys():
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_json(tmp, {"_meta": {"note": "only meta"}})
        try:
            load_tier_file(path)
            assert False, "should have raised"
        except TierFileError as e:
            assert "no tier keys" in str(e)


def test_load_shipped_tiered_json():
    """The actual tiered.json in the repo must load without errors."""
    here = Path(__file__).resolve().parent.parent
    json_path = here / "scripts" / "ab_goalsets" / "tiered.json"
    assert json_path.exists(), f"tiered.json not found at {json_path}"
    result = load_tier_file(json_path)
    # Must have T0, T1, T2
    assert "T0" in result and "T1" in result and "T2" in result
    # Each tier must have goals
    for tier in ("T0", "T1", "T2"):
        assert len(result[tier]) >= 4, f"{tier} has fewer than 4 goals"
    # Every goal must have theorem_src starting with 'theorem '
    for tier, goals in result.items():
        for g in goals:
            assert g["theorem_src"].startswith("theorem "), (
                f"{tier} goal has bad theorem_src: {g['theorem_src'][:60]!r}"
            )


# ---------------------------------------------------------------------------
# aggregate_tiers
# ---------------------------------------------------------------------------

def test_aggregate_tiers_basic():
    rows_t0 = [
        {"goal": "g1", "a": _arm(True, [OPUS], 1, 1), "b": _arm(True, [OPUS], 1, 1)},
        {"goal": "g2", "a": _arm(True, [OPUS], 1, 1), "b": _arm(True, [GOEDEL], 1, 1)},
    ]
    rows_t1 = [
        {"goal": "g3", "a": _arm(False, [], 0, 2), "b": _arm(True, [GOEDEL, OPUS], 2, 2)},
    ]
    result = aggregate_tiers({"T0": rows_t0, "T1": rows_t1}, CAND)
    assert "T0" in result and "T1" in result
    assert result["T0"]["goals"] == 2
    assert result["T0"]["reached_A"] == 2
    assert result["T1"]["goals"] == 1
    assert result["T1"]["reached_A"] == 0
    assert result["T1"]["reached_B"] == 1
    assert result["T1"]["b_only_unlocks"] == 1


def test_aggregate_tiers_empty_tier():
    result = aggregate_tiers({"T0": [], "T1": []}, CAND)
    assert result["T0"]["goals"] == 0
    assert result["T1"]["goals"] == 0


# ---------------------------------------------------------------------------
# plateau_tier
# ---------------------------------------------------------------------------

def test_plateau_at_t1():
    summaries = {
        "T0": {"goals": 8, "reached_A": 8, "reached_B": 8, "b_only_unlocks": 0, "candidate_decisive": 0},
        "T1": {"goals": 8, "reached_A": 3, "reached_B": 6, "b_only_unlocks": 3, "candidate_decisive": 2},
        "T2": {"goals": 6, "reached_A": 0, "reached_B": 4, "b_only_unlocks": 4, "candidate_decisive": 3},
    }
    assert plateau_tier(summaries, ["T0", "T1", "T2"]) == "T1"


def test_plateau_at_t2():
    summaries = {
        "T0": {"goals": 8, "reached_A": 8, "reached_B": 8, "b_only_unlocks": 0, "candidate_decisive": 0},
        "T1": {"goals": 8, "reached_A": 6, "reached_B": 6, "b_only_unlocks": 0, "candidate_decisive": 0},
        "T2": {"goals": 6, "reached_A": 1, "reached_B": 5, "b_only_unlocks": 4, "candidate_decisive": 4},
    }
    assert plateau_tier(summaries, ["T0", "T1", "T2"]) == "T2"


def test_no_plateau_when_arms_track():
    summaries = {
        "T0": {"goals": 8, "reached_A": 8, "reached_B": 8, "b_only_unlocks": 0, "candidate_decisive": 0},
        "T1": {"goals": 8, "reached_A": 4, "reached_B": 4, "b_only_unlocks": 0, "candidate_decisive": 0},
    }
    assert plateau_tier(summaries, ["T0", "T1"]) is None


def test_no_plateau_empty_goals():
    # Tiers with 0 goals are skipped
    summaries = {
        "T0": {"goals": 0, "reached_A": 0, "reached_B": 0, "b_only_unlocks": 0, "candidate_decisive": 0},
        "T1": {"goals": 4, "reached_A": 4, "reached_B": 4, "b_only_unlocks": 0, "candidate_decisive": 0},
    }
    assert plateau_tier(summaries, ["T0", "T1"]) is None


def test_plateau_returns_first_diverging_tier():
    # If T1 and T2 both diverge, T1 is returned (first in order)
    summaries = {
        "T0": {"goals": 4, "reached_A": 4, "reached_B": 4, "b_only_unlocks": 0, "candidate_decisive": 0},
        "T1": {"goals": 4, "reached_A": 2, "reached_B": 4, "b_only_unlocks": 2, "candidate_decisive": 1},
        "T2": {"goals": 4, "reached_A": 0, "reached_B": 3, "b_only_unlocks": 3, "candidate_decisive": 2},
    }
    assert plateau_tier(summaries, ["T0", "T1", "T2"]) == "T1"


# ---------------------------------------------------------------------------
# Integration: summarize_ab is correctly re-exported
# ---------------------------------------------------------------------------

def test_summarize_ab_reexported():
    """summarize_ab imported from ab_prover_tiers delegates to ab_prover_reach."""
    rows = [
        {"goal": "g", "a": _arm(False, [], 0), "b": _arm(True, [GOEDEL, OPUS], 2)},
    ]
    s = summarize_ab(rows, CAND)
    assert s["b_only_unlocks"] == 1
    assert s["candidate_decisive"] == 1

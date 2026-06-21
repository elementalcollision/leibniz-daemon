"""ADR 0012: mechanical import-resolver + prover-output normalization (CI-safe).

Uses the committed Mathlib module index (corpus/mathlib_modules.json); no Lean/LLM.
"""
from __future__ import annotations

from collections import Counter

from leibniz.consensus import normalize_proof
from leibniz.imports import module_index, resolve_imports


def test_index_loads_and_reflects_current_mathlib():
    idx = module_index()
    assert len(idx) > 5000
    assert "Mathlib.Analysis.SpecialFunctions.Log.Basic" in idx
    # the stale path the live autoformalizer used does NOT exist in v4.31
    assert "Mathlib.Analysis.SpecialFunctions.Logb" not in idx


def test_resolve_keeps_valid_import():
    assert "Mathlib.Tactic" in resolve_imports(["Mathlib.Tactic"])


def test_resolve_drops_unresolvable_and_ensures_tactic():
    out = resolve_imports(["Mathlib.Analysis.SpecialFunctions.Logb"])
    assert "Mathlib.Analysis.SpecialFunctions.Logb" not in out  # stale -> dropped
    assert "Mathlib.Tactic" in out  # a Mathlib import was requested -> tactic ensured


def test_resolve_fuzzy_recovers_a_stale_path_by_unique_leaf():
    idx = module_index()
    leaf_counts = Counter(m.split(".")[-1] for m in idx)
    unique = next(m for m in sorted(idx) if leaf_counts[m.split(".")[-1]] == 1)
    stale = "Mathlib.Bogus.Path." + unique.split(".")[-1]
    assert unique in resolve_imports([stale])


def test_resolve_passthrough_without_index():
    assert resolve_imports(["Anything.At.All"], index=frozenset()) == ["Anything.At.All"]


# --- prover-output normalization ---------------------------------------------

def test_normalize_strips_fences():
    assert normalize_proof("```lean\nby simp\n```") == "by simp"
    assert normalize_proof("```\nby decide\n```") == "by decide"


def test_normalize_strips_a_restated_theorem():
    assert normalize_proof("theorem foo : P := by ring") == "by ring"


def test_normalize_passes_plain_tactics_through():
    assert normalize_proof("by induction n") == "by induction n"


def test_normalize_keeps_tactic_with_internal_assignment():
    assert normalize_proof("by have h := f; exact h") == "by have h := f; exact h"

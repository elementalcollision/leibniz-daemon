"""normalize_proof must strip markdown fences + language tags so a CORRECT prover proof
isn't rejected on formatting (ADR 0012). Regression: a Goedel-style ```lean4 fence left a
bare `lean4` token (isalpha() misses the digit), and the old isalpha() check would also have
eaten a proof whose first fenced line is the bare keyword `by`. Both are fixed by matching a
known language set. CI-safe (pure string); not a trust-edge change.
"""
from __future__ import annotations

import pytest

from leibniz.consensus import normalize_proof


@pytest.mark.parametrize("raw, expected", [
    # the regression: Goedel/Featherless wraps in ```lean4 — the `4` made isalpha() miss it
    ("### \n\n```lean4\nby simp [add_zero]\n```", "by simp [add_zero]"),
    ("```lean4\nby omega\n```", "by omega"),
    ("```lean\nby ring\n```", "by ring"),                 # lean (no digit)
    ("```\nby simp\n```", "by simp"),                      # bare fence
    ("by exact rfl", "by exact rfl"),                     # no fence at all — unchanged
    ("```lean4\nby\n  simp\n  omega\n```", "by\n  simp\n  omega"),  # multi-line body preserved
])
def test_fenced_proofs_normalize_to_a_usable_body(raw, expected):
    out = normalize_proof(raw)
    assert out == expected
    assert "```" not in out and not out.startswith("lean")


def test_bare_by_first_line_is_not_eaten():
    # The old isalpha() check would have dropped a lone `by` line (isalpha('by') is True),
    # truncating the proof. The known-language set must NOT treat `by` as a language tag.
    assert normalize_proof("```\nby\nsimp [add_zero]\n```") == "by\nsimp [add_zero]"


def test_restated_theorem_header_is_stripped():
    # an unchanged behavior: a prover that restates `theorem ... :=` is trimmed to the body
    assert normalize_proof("theorem t (n : Nat) : n + 0 = n := by simp") == "by simp"

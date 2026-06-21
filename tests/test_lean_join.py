"""Regression: _join_proof handles autoformalizer output that already carries a
proof body (the live-run MALFORMED cause). CI-safe (pure)."""
from __future__ import annotations

from leibniz.backends.lean_cli import _join_proof


def test_appends_proof_to_a_bare_header():
    assert _join_proof("theorem t : P", "by decide") == "theorem t : P := by decide"


def test_strips_an_existing_proof_tail_before_appending():
    # the live run hit this: theorem_src ended in ':= by sorry' and got doubled.
    assert _join_proof("theorem t : P := by sorry", "by decide") == "theorem t : P := by decide"


def test_default_sorry_when_no_proof_given():
    assert _join_proof("theorem t : P", "") == "theorem t : P := by sorry"


def test_binder_colons_are_not_mistaken_for_the_proof_assignment():
    assert _join_proof("theorem t (n : Nat) : P n := by sorry", "by simp") == "theorem t (n : Nat) : P n := by simp"

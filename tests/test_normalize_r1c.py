"""R1c: elaborator-canonical structural normalization + persistent container.

Requires the Lean container; skips where absent.
"""
from __future__ import annotations

import pytest

from leibniz.backends.lean_cli import LeanCliBackend, available
from leibniz.propositio import Expressio

pytestmark = [
    pytest.mark.lean,
    pytest.mark.skipif(
        not available(), reason="Lean container leibniz-lean:v4.31.0 not available"
    ),
]

_MT = ("Mathlib.Tactic",)


def _hash(src: str, imports=_MT):
    return LeanCliBackend().normalize_statement(Expressio(theorem_src=src, imports=imports))


def test_normalization_is_alpha_and_notation_invariant():
    # Different binder name (n vs m), different syntax (-> vs ∀), different spelling
    # of Nat (Nat vs ℕ) — all the same theorem, so the structural hash must collide.
    a = _hash("theorem a : (n : Nat) -> n + 0 = n")
    b = _hash("theorem b : ∀ m : ℕ, m + 0 = m")
    assert a is not None
    assert a == b


def test_normalization_distinguishes_different_statements():
    a = _hash("theorem a : ∀ n : ℕ, n + 0 = n")
    c = _hash("theorem c : ∀ k : ℕ, k + 1 = 1 + k")
    assert a is not None and c is not None
    assert a != c


def test_normalization_returns_none_for_malformed():
    assert _hash("theorem bad : NoSuchIdent", imports=()) is None


def test_persistent_mode_checks_proofs_and_cleans_up():
    with LeanCliBackend(persistent=True) as backend:
        ok = backend.check_proof(Expressio(theorem_src="theorem t : 1 + 1 = 2", imports=()), "by decide")
        bad = backend.check_proof(Expressio(theorem_src="theorem f : 1 + 1 = 3", imports=()), "by decide")
        cid = backend._cid
    assert ok is True
    assert bad is False
    assert cid is not None  # a persistent container was actually started
    assert backend._cid is None  # ...and closed on context exit

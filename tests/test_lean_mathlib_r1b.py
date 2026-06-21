"""R1b: Mathlib + aesop are online behind LeanBackend.

Uses *targeted* imports (e.g. `import Mathlib.Tactic`, `import Aesop`) rather than
the umbrella `import Mathlib` — the umbrella olean is not in the prebuilt cache and
loading all of Mathlib per check would wreck throughput. Real candidate statements
declare the modules they need via Expressio.imports.

Requires the Mathlib-enabled container (leibniz-lean:v4.31.0); skips where absent.
"""
from __future__ import annotations

import pytest

from leibniz.backends.lean_cli import LeanCliBackend, available
from leibniz.propositio import Demonstratio, Expressio
from leibniz.verifiers import LeanVerifier

pytestmark = [
    pytest.mark.lean,
    pytest.mark.skipif(
        not available(), reason="Lean container leibniz-lean:v4.31.0 not available"
    ),
]


def test_mathlib_tactic_theorem_is_kernel_verified():
    """A theorem needing Mathlib's `ring` tactic proves and is kernel-verified."""
    expr = Expressio(
        theorem_src="theorem binom_sq (a b : Nat) : (a + b) ^ 2 = a ^ 2 + 2 * a * b + b ^ 2",
        imports=("Mathlib.Tactic",),
    )
    demo = Demonstratio(proof_obligation="binom_sq", proof_src="by ring")
    LeanVerifier(LeanCliBackend()).discharge(expr, demo)
    assert demo.kernel_verified is True
    assert demo.qed == "Q.E.D."


def test_mathlib_false_theorem_is_not_verified():
    """`ring` cannot prove a false algebraic identity -> not verified."""
    expr = Expressio(
        theorem_src="theorem bad (a b : Nat) : a + b = a * b",
        imports=("Mathlib.Tactic",),
    )
    demo = Demonstratio(proof_obligation="bad", proof_src="by ring")
    LeanVerifier(LeanCliBackend()).discharge(expr, demo)
    assert demo.kernel_verified is False
    assert demo.qed == "Q.E.I."


def test_aesop_is_wired():
    """aesop (a Mathlib/Aesop tactic) closes a goal the core tactics cannot."""
    expr = Expressio(theorem_src="theorem from_hyp (p : Prop) (h : p) : p", imports=("Aesop",))
    ok = LeanCliBackend().check_proof(expr, "by aesop")
    assert ok is True


def test_aesop_in_triviality_set():
    """closed_by_decision_procedure succeeds on an aesop-closable statement."""
    backend = LeanCliBackend()
    expr = Expressio(theorem_src="theorem triv (p : Prop) (h : p) : p", imports=("Aesop",))
    assert backend.closed_by_decision_procedure(expr) is True

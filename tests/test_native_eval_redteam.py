"""ADR 0095 red-team: `kernel_verified` must mean KERNEL-decided, not compiler-decided.

Frozen from the 2026-09-10 Trail of Bits audit. The exploit below is the real one
(`String.Pos.Raw.extract`, CVE-adjacent, all stable Lean <= 4.33.1): on the pinned 4.31 the
compiled evaluator and the kernel disagree about the same string slice, so `native_decide` and
`decide` prove complementary propositions and `False` follows. Before ADR 0095 this returned
`kernel_verified=True` / `Q.E.D.` from `LeanVerifier.discharge`, the sole writer.

These tests are kernel-gated. The DOCKER-FREE ones below them must always run: they pin the
structural guarantee (a backend that does not enforce the footprint cannot mint a verdict)
without needing an image.
"""
from __future__ import annotations

import pytest

from leibniz.backends.lean_axioms import STD_AXIOMS, axiom_report, axiom_report_text
from leibniz.propositio import Demonstratio, Expressio
from leibniz.verifiers import LeanVerifier

# The published exploit, verbatim enough to still bite if the pin moves backwards.
EXPLOIT_PREAMBLE = '''def s : String := "a truly marvelous proof"
def big : String.Pos.Raw := ⟨2^63⟩
def slice : String := String.Pos.Raw.extract s big ⟨2^63 + 1⟩
theorem margin : False := by
  have hk : slice = "" := by decide
  have hn : slice ≠ "" := by native_decide
  exact hn hk'''
FLT = ("theorem fermat_last (a b c n : Nat) (hn : n > 2) (ha : a > 0) (hb : b > 0) : "
       "a^n + b^n ≠ c^n")


def _repl():
    from leibniz.backends.lean_cli import available
    if not available():
        pytest.skip("kernel lane: docker + leibniz-lean-repl image not present")
    from leibniz.backends.lean_repl import LeanReplBackend
    return LeanReplBackend()


# --- structural guarantees (no docker) --------------------------------------

class _PermissiveBackend:
    """A backend of the shape that existed before ADR 0095: says yes, checks no axioms."""
    def compile_statement(self, expr): return True
    def check_proof(self, expr, proof_src): return True
    def closed_by_decision_procedure(self, expr): return False


def test_backend_without_axiom_enforcement_cannot_mint_a_kernel_verdict():
    """ADR 0095 decision 2. `discharge` fails CLOSED when the backend does not assert that its
    `check_proof` read the axiom footprint -- so a future backend cannot be wired in and silently
    stamp Q.E.D. This is the property that call-site convention could not provide."""
    demo = Demonstratio(proof_obligation="redteam", proof_src="by native_decide")
    ev = LeanVerifier(backend=_PermissiveBackend()).discharge(
        Expressio(theorem_src="theorem t : True"), demo)
    assert demo.kernel_verified is False
    assert demo.qed == "Q.E.I."
    assert ev.verdict.name == "FAIL"


def test_real_lean_backends_assert_axiom_enforcement():
    """Both real Lean backends must carry the assertion -- otherwise decision 2 would silently
    disable the whole kernel lane rather than protect it."""
    from leibniz.backends.lean_cli import LeanCliBackend
    from leibniz.backends.lean_repl import LeanReplBackend
    assert LeanCliBackend.enforces_axiom_closure is True
    assert LeanReplBackend.enforces_axiom_closure is True


def test_generated_native_axiom_is_rejected_by_the_allowlist():
    """leanprover/lean4#12216: since Lean 4.29 native computation is one AUTO-GENERATED axiom per
    computation, named after the theorem. Measured on the pinned 4.31:
    `margin._native.native_decide.ax_1`. A denylist naming `Lean.ofReduceBool` / `trustCompiler`
    is therefore blind; only the allowlist sees it. This test pins that reasoning."""
    generated = "margin._native.native_decide.ax_1"
    assert "ofReduceBool" not in generated and "trustCompiler" not in generated
    assert generated not in STD_AXIOMS
    rep = axiom_report(
        {"messages": [{"severity": "info",
                       "data": f"'margin' depends on axioms: [propext, {generated}]"}]},
        "margin")
    assert rep["ok"] is False
    assert rep["extra_axioms"] == [generated]


def test_axiom_report_text_matches_the_repl_reader():
    """The CLI backend's flat-text transport must reach the SAME verdict as the REPL's message
    list -- ADR 0090's whole point was one hardened reader, not a second open-coded scan."""
    line = "'t' depends on axioms: [propext, Classical.choice, Quot.sound]"
    assert axiom_report_text(line, "t")["ok"] is True
    assert axiom_report_text(f"{line[:-1]}, t._native.native_decide.ax_1]", "t")["ok"] is False
    # fails closed on a dead backend and on an error-carrying run
    assert axiom_report_text(None, "t")["ok"] is False
    assert axiom_report_text(f"error: boom\n{line}", "t")["ok"] is False


def test_unnamed_declaration_fails_closed():
    """No name => no `#print axioms` target => nothing to certify. Must not pass vacuously."""
    from leibniz.backends.lean_repl import LeanReplBackend
    be = LeanReplBackend()
    assert be.check_proof(Expressio(theorem_src="example : True"), "by trivial") is False


# --- the live exploit (docker-gated) ----------------------------------------

def test_native_decide_cannot_set_kernel_verified():
    """A TRUE theorem proved by `native_decide`: the compiler decided it, not the kernel."""
    be = _repl()
    try:
        demo = Demonstratio(proof_obligation="redteam", proof_src="by native_decide")
        LeanVerifier(backend=be).discharge(
            Expressio(theorem_src="theorem nd_t : (1000000000000 : Nat) % 7 = 1",
                      imports=("Mathlib",)), demo)
        assert demo.kernel_verified is False, "native_decide must never be kernel_verified"
        assert demo.qed == "Q.E.I."
    finally:
        be.close()


def test_trail_of_bits_exploit_cannot_be_promulgated():
    """GATE: the published soundness bug, driven end-to-end through the sole kernel writer.

    On the pinned 4.31 this proof of Fermat's Last Theorem elaborates with no error and no sorry,
    so pre-ADR-0095 `check_proof` returned True and `discharge` sealed it `Q.E.D.`. It must now
    fail at the writer, not merely at a gate a caller might forget to run."""
    be = _repl()
    try:
        demo = Demonstratio(proof_obligation="fermats_last_theorem", proof_src="(margin).elim")
        ev = LeanVerifier(backend=be).discharge(
            Expressio(theorem_src=FLT, imports=("Mathlib",), preamble=EXPLOIT_PREAMBLE), demo)
        assert demo.kernel_verified is False
        assert demo.qed != "Q.E.D."
        assert ev.verdict.name == "FAIL"
    finally:
        be.close()


def test_honest_kernel_proofs_still_pass():
    """The guard must not be a blanket refusal -- genuine kernel proofs keep their Q.E.D."""
    be = _repl()
    try:
        v = LeanVerifier(backend=be)
        for src, proof in (("theorem h1 : (12 : Nat) % 5 = 2", "by decide"),
                           ("theorem h2 : (1 : Nat) + 1 = 2", "by rfl"),
                           ("theorem h3 : (7 : Nat) * 6 = 42", "by norm_num")):
            demo = Demonstratio(proof_obligation="honest", proof_src=proof)
            v.discharge(Expressio(theorem_src=src, imports=("Mathlib",)), demo)
            assert demo.kernel_verified is True, f"regression: {src} no longer verifies"
            assert demo.qed == "Q.E.D."
    finally:
        be.close()

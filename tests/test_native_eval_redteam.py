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

from leibniz.backends.lean_axioms import (
    STD_AXIOMS,
    axiom_report,
    axiom_report_text,
    declaration_name,
    mentions_sorry,
    smuggles_top_level,
)
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


def test_comment_cannot_hijack_the_declaration_name():
    """ADR 0095. The name handed to `#print axioms` must come from the real DECLARATION.

    `_NAME_RE.search` took the first `theorem <name>` match anywhere in `theorem_src`, comments
    included -- so a proposer-authored statement opening with

        -- theorem Nat.add_comm

    made the footprint check report on MATHLIB's `Nat.add_comm` (clean, and a different
    declaration entirely) while the real theorem was proved by `native_decide`. Measured on the
    pinned 4.31 before the fix: `discharge` gave `kernel_verified=True` / `Q.E.D.` AND
    `axiom_closure(...)["ok"]` was True -- it defeated the new writer-side check and the
    pre-existing gate at once."""
    assert declaration_name("-- theorem Nat.add_comm\ntheorem evil : True") == "evil"
    assert declaration_name("/-- mentions theorem Nat.add_comm -/\ntheorem ok1 : True") == "ok1"
    # Lean block comments NEST; a non-nesting stripper would leak the inner text back out.
    assert declaration_name("/- /- theorem Fake.name -/ -/\ntheorem ok2 : True") == "ok2"
    # ordinary shapes still resolve
    assert declaration_name("@[simp] theorem attr1 : True") == "attr1"
    assert declaration_name("private theorem priv1 : True") == "priv1"
    assert declaration_name("open Nat in\ntheorem opened : True") == "opened"
    assert declaration_name("lemma lem1 : True") == "lem1"
    # a name that exists ONLY in a comment must fail closed, not resolve to something else
    assert declaration_name("-- theorem Only.InComment") is None


def test_report_only_kernels_cannot_stamp():
    """ADR 0048 says Coq/Rocq and Isabelle may observe a kernel but never set `kernel_verified`.
    They cannot assert `enforces_axiom_closure`, so a `LeanVerifier` mistakenly built around one
    now fails closed at the writer instead of relying on nobody ever wiring it up."""
    from leibniz.backends.coq_docker import CoqDockerBackend
    from leibniz.backends.isabelle_docker import IsabelleDockerBackend
    for cls in (CoqDockerBackend, IsabelleDockerBackend):
        assert getattr(cls, "enforces_axiom_closure", False) is False, cls.__name__


def test_proof_src_cannot_smuggle_a_top_level_declaration():
    """ADR 0095 decision 4. `proof_src` is an EXPRESSION; it must not open new declarations.

    `Expressio.proof_hints` used to assert that "a smuggled top-level command would be a parse
    error inside the proof — there is no separate-declaration surface to poison". False, and
    load-bearing: nothing guarded `proof_src`. Lean elaborates a proof followed by more commands
    quite happily, and a still-open `namespace` makes the appended `#print axioms <name>` report
    on a DECOY of the same short name. Measured on the pinned 4.31 before this guard:
    `kernel_verified=True`, `Q.E.D.`, `axiom_closure(...)["ok"] is True`, and driven to `False`.
    """
    assert smuggles_top_level("by native_decide\n\nnamespace M\ntheorem margin : True := trivial")
    for bad in ("by decide\nend M", "by decide\nopen Foo", "by decide\n#print axioms other",
                "by decide\ndef d := 1", "by decide\n@[simp] theorem t : True := trivial",
                "by decide\nsection", "by decide\naxiom bad : False",
                "by decide\nset_option debug.skipKernelTC true"):
        assert smuggles_top_level(bad), bad
    # honest proofs -- including indented multi-line tactic blocks -- must pass
    for good in ("by decide", "by native_decide", "(margin).elim",
                 "by\n  have h : 1 = 1 := rfl\n  simp",
                 "by\n  induction n with\n  | zero => rfl\n  | succ k ih => simp [ih]",
                 "-- namespace in a comment is inert\nby decide"):
        assert not smuggles_top_level(good), good


def test_axiom_report_text_reads_OUR_report_not_the_first_one():
    """ADR 0095 decision 5. The CLI transport hands back the whole file as one blob.

    Flattening it into a single message defeated the ADR 0090 per-message name filter: the filter
    was satisfied by any report naming our theorem, while the axiom list came from a SEPARATE
    search that returned the FIRST list in the file. An ADR 0062 preamble carrying its own
    `#print axioms` (16 of the `docs/crt/*.lean` artifacts do) therefore lent its clean list to
    our dirty theorem -- no adversary required. Both transports must now agree on identical
    content."""
    blob = ("'decoy_ok' depends on axioms: [propext]\n"
            "'margin' depends on axioms: [propext, margin._native.native_decide.ax_1]")
    rep_text = axiom_report_text(blob, "margin")
    assert rep_text["ok"] is False
    assert "margin._native.native_decide.ax_1" in rep_text["axioms"]
    # the REPL reader, given the same content as separate messages, must agree
    rep_repl = axiom_report(
        {"messages": [{"severity": "info", "data": ln} for ln in blob.split("\n")]}, "margin")
    assert rep_repl["ok"] is rep_text["ok"]
    assert set(rep_repl["axioms"]) == set(rep_text["axioms"])
    # and the clean case still passes on both
    ok_blob = "'other' depends on axioms: [propext]\n'margin' does not depend on any axioms"
    assert axiom_report_text(ok_blob, "margin")["ok"] is True


def test_a_theorem_named_sorry_something_still_verifies():
    """ADR 0095 decision 6. `#print axioms <name>` echoes the declaration's NAME into the message
    stream, so a blind `"sorry" in message` scan started rejecting honest proofs whose name merely
    contains the letters -- a silent, unexplained DEFER. Match what Lean actually reports."""
    assert mentions_sorry("declaration uses 'sorry'")
    assert mentions_sorry("'t' depends on axioms: [sorryAx]")
    assert not mentions_sorry("'sorry_free_addition' does not depend on any axioms")
    assert not mentions_sorry("'no_sorry_here' depends on axioms: [propext]")


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


def test_namespace_decoy_cannot_promulgate_a_native_proof():
    """The live form of the smuggling attack, end-to-end through the sole writer."""
    be = _repl()
    try:
        THM = "theorem margin : (2:Nat)+2 = 4"
        PROOF = "by native_decide\n\nnamespace M\ntheorem margin : True := trivial"
        demo = Demonstratio(proof_obligation="decoy", proof_src=PROOF)
        LeanVerifier(backend=be).discharge(
            Expressio(theorem_src=THM, imports=()), demo)
        assert demo.kernel_verified is False
        assert demo.qed != "Q.E.D."
        # the by-convention gate must refuse it too
        from leibniz.backends.lean_axioms import axiom_closure
        assert axiom_closure(be, THM, PROOF, ())["ok"] is False
    finally:
        be.close()


def test_sorry_named_theorem_verifies_against_the_real_kernel():
    """The live counterpart of the `mentions_sorry` unit test -- an honest proof must not DEFER."""
    be = _repl()
    try:
        demo = Demonstratio(proof_obligation="named", proof_src="by decide")
        LeanVerifier(backend=be).discharge(
            Expressio(theorem_src="theorem sorry_free_addition : (1:Nat)+1 = 2", imports=()), demo)
        assert demo.kernel_verified is True, "honest proof rejected because of its NAME"
        assert demo.qed == "Q.E.D."
    finally:
        be.close()

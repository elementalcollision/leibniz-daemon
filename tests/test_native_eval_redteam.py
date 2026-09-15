"""ADR 0097 red-team: `kernel_verified` must mean KERNEL-decided, not compiler-decided.

Frozen from the 2026-09-10 Trail of Bits audit. The exploit below is the real one
(`String.Pos.Raw.extract`, CVE-adjacent, all stable Lean <= 4.33.1): on the pinned 4.31 the
compiled evaluator and the kernel disagree about the same string slice, so `native_decide` and
`decide` prove complementary propositions and `False` follows. Before ADR 0097 this returned
`kernel_verified=True` / `Q.E.D.` from `LeanVerifier.discharge`, the sole writer.

These tests are kernel-gated. The DOCKER-FREE ones below them must always run: they pin the
structural guarantee (a backend that does not enforce the footprint cannot mint a verdict)
without needing an image.
"""
from __future__ import annotations

import pytest

from leibniz.backends.lean_axioms import (
    STD_AXIOMS,
    _report_re,
    _strip_comments,
    axiom_report,
    axiom_report_text,
    closes_more_than_it_opens,
    declaration_name,
    declaration_source,
    _parse_axcheck,
    defeats_the_kernel,
    fresh_probe_name,
    import_is_safe,
    mentions_sorry,
    probe_source,
    smuggles_top_level,
    statement_head,
    statement_is_single_declaration,
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


def _cli():
    from leibniz.backends.lean_cli import available
    if not available():
        pytest.skip("kernel lane: docker + leibniz-lean image not present")
    from leibniz.backends.lean_cli import LeanCliBackend
    return LeanCliBackend(timeout_s=900)


def _repl():
    from leibniz.backends.lean_cli import available
    if not available():
        pytest.skip("kernel lane: docker + leibniz-lean-repl image not present")
    from leibniz.backends.lean_repl import LeanReplBackend
    return LeanReplBackend()


# --- structural guarantees (no docker) --------------------------------------

class _PermissiveBackend:
    """A backend of the shape that existed before ADR 0097: says yes, checks no axioms."""
    def compile_statement(self, expr): return True
    def check_proof(self, expr, proof_src): return True
    def closed_by_decision_procedure(self, expr): return False


def test_backend_without_axiom_enforcement_cannot_mint_a_kernel_verdict():
    """ADR 0097 decision 2. `discharge` fails CLOSED when the backend does not assert that its
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
    """ADR 0097. The name handed to `#print axioms` must come from the real DECLARATION.

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
    """ADR 0097 decision 4. `proof_src` is an EXPRESSION; it must not open new declarations.

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
    """ADR 0097 decision 5. The CLI transport hands back the whole file as one blob.

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
    """ADR 0097 decision 6, as CORRECTED by decision 9.

    `#print axioms <name>` echoes the declaration's NAME into the message stream, so a blind
    `"sorry" in message` scan rejected honest proofs whose name merely contains the letters -- a
    silent, unexplained DEFER. The first fix narrowed the scan to Lean's warning wording, and that
    was a material regression (Lean uses BACKTICKS, so it matched nothing and `check_source`
    started certifying `2 + 2 = 5`). The scan is broad; the ECHO is what gets excluded, via
    `ignore`. This test pins the corrected contract, so that narrowing it again fails here.
    """
    assert mentions_sorry("declaration uses `sorry`")
    assert mentions_sorry("declaration uses 'sorry'")
    assert mentions_sorry("'t' depends on axioms: [sorryAx]")
    # broad WITHOUT the echo exclusion -- this is the property `check_source` depends on
    assert mentions_sorry("'sorry_free_addition' does not depend on any axioms")
    # ...and precise WITH it, which is what `check_proof` uses
    rep = _report_re("sorry_free_addition")
    assert not mentions_sorry("'sorry_free_addition' does not depend on any axioms", ignore=rep)
    assert not mentions_sorry("'no_sorry_here' depends on axioms: [propext]",
                              ignore=_report_re("no_sorry_here"))
    # text with no hole and no echo is clean either way
    assert not mentions_sorry("'plain' depends on axioms: [propext]")


# --- round-2 adversarial review (ADR 0097 decisions 7-10) --------------------

def test_indented_top_level_command_is_still_a_smuggle():
    """Decision 7. The first guard was a COLUMN-0 scan, and its stated rationale ("a proof's own
    continuation lines are indented, a new command is not") was simply wrong: Lean parses a
    command at any column. One leading space walked past it and drove `catastrophe : False` to
    `Q.E.D.` through the CLI backend."""
    assert smuggles_top_level("by\n    native_decide\n\n namespace M\n theorem m : True := trivial")
    assert smuggles_top_level("by decide\n theorem d : True := trivial")
    assert smuggles_top_level("by decide\n\t@[simp] theorem d : True := trivial")
    # `set_option ... in` / `open ... in` are TERM MODIFIERS, not declarations, and honest proofs
    # use them -- gates/mixed_modulus_decided.py emits the first. They must NOT trip the guard.
    assert not smuggles_top_level("by\n  set_option maxRecDepth 4000 in\n  decide")
    assert not smuggles_top_level("open Nat in\nby decide")


def test_string_literal_cannot_blind_the_comment_stripper():
    """Decision 8. Lexing `/-` without tracking string literals is itself an attack surface: a
    proof containing `have s : String := "/-"` opened a block comment that never closed, so the
    stripper swallowed the rest and the guard saw nothing -- while Lean, which lexes the string
    correctly, elaborated the `namespace` decoy that followed. Independent of decision 7."""
    assert smuggles_top_level(
        'by\n  have s : String := "/-"\n  native_decide\n\nnamespace M2\ntheorem m2 : True := trivial')
    assert '"/-"' in _strip_comments('have s : String := "/-"\nnamespace M')
    assert smuggles_top_level('by\n  have s := "a\\"/-"\n  decide\nnamespace M3')
    # real comments are still stripped
    assert not smuggles_top_level("-- namespace M\nby decide")
    assert not smuggles_top_level("/- namespace M -/\nby decide")


def test_sorry_scan_is_broad_and_matches_leans_backticks():
    """Decision 9, and the most serious regression of the whole ADR. Narrowing this scan to
    Lean's warning wording matched NOTHING -- Lean writes it with BACKTICKS on 4.31.0, 4.33.1 and
    4.34.0-rc2 alike -- so `LeanCliBackend.check_source` began returning True for
    `theorem t : 2 + 2 = 5 := by sorry`, on the path ~20 audit scripts call the trusted re-check
    and which has NO axiom-footprint backstop. The scan stays broad; only the `#print axioms`
    name echo is excluded, which was the sole cause of the false DEFER."""
    assert mentions_sorry("declaration uses `sorry`")      # backticks -- Lean's actual wording
    assert mentions_sorry("declaration uses 'sorry'")
    assert mentions_sorry("'t' depends on axioms: [sorryAx]")
    rep = _report_re("sorry_free_addition")
    assert not mentions_sorry("'sorry_free_addition' does not depend on any axioms", ignore=rep)
    # `sorryAx` is tested BEFORE the echo is removed, so a hole in the footprint still bites
    assert mentions_sorry("'sorry_free_addition' depends on axioms: [sorryAx]", ignore=rep)


def test_wrapped_axiom_list_is_read_correctly_by_both_transports():
    """Decision 10. Lean's pretty-printer BREAKS a long axiom list across lines (measured: a
    3-axiom footprint wraps once the name reaches 60 chars, a native-axiom footprint at 15), and
    `set_option format.width` does not suppress it. Splitting the CLI blob per line therefore saw
    a report with no list and a list with no report -- so an honest 62-char-named proof got
    `Q.E.D.` from the REPL and `Q.E.I.` from the CLI, and a wrapped dirty footprint could lose to
    an earlier one-line report about the same short name."""
    n = "crt_amplification_of_a_recently_published_finite_core_lemma_v1"
    clean = f"'{n}' depends on axioms: [propext,\n Classical.choice,\n Quot.sound]"
    dirty = (f"'{n}' depends on axioms: [propext,\n Classical.choice,\n Quot.sound,\n"
             f" {n}._native.native_decide.ax_1]")
    assert axiom_report_text(clean, n)["ok"] is True
    assert axiom_report_text(dirty, n)["ok"] is False
    # an earlier one-line report about the same name must not win over our wrapped one
    assert axiom_report_text(f"'{n}' depends on axioms: [propext]\n" + dirty, n)["ok"] is False
    # the two transports must agree on identical content
    msgs = {"messages": [{"severity": "info", "data": dirty}]}
    assert axiom_report(msgs, n)["ok"] is axiom_report_text(dirty, n)["ok"]


def test_tagged_error_diagnostics_are_recognised():
    """Lean 4.31 emits `error(lean.unknownIdentifier): ...` as well as plain `error: ...`; a
    literal `"error:" in output` test missed the tagged form and passed a report that coexisted
    with an error."""
    for diag in ("x.lean:2:14: error(lean.unknownIdentifier): boom",
                 "x.lean:2:14: error: boom"):
        assert axiom_report_text(f"{diag}\n't' does not depend on any axioms", "t")["ok"] is False


def test_declaration_name_handles_honest_lean_shapes():
    """Round 2 found four silent false-rejects; a guard that refuses honest work is a defect."""
    for src, want in (("set_option maxRecDepth 4000 in theorem foo : True", "foo"),
                      ("open Nat in theorem foo2 : True", "foo2"),
                      ("theorem\n  wrapped_name : True", "wrapped_name"),
                      ("theorem «a weird name» : True", "«a weird name»"),
                      ("theorem upoly.{u} (a : Sort u) : True", "upoly"),
                      ("nonrec theorem nr : True", "nr")):
        assert declaration_name(src) == want, src


# --- round-3 adversarial review (ADR 0097 decisions 12-13) -------------------

def test_footprint_is_read_under_an_unpredictable_probe_name():
    """Decision 12, and the defect that broke every previous version of this module.

    The reader matched report-shaped TEXT anywhere in Lean's output and never bound it to the
    `#print axioms` command the checker itself issued. A proof can simply PRINT a clean report --
    `run_cmd IO.println "'t' depends on axioms: [propext]"`, or `dbg_trace` inside the proof term
    with NO imports and NO top-level command, so no keyword scan can see it. Combined with a
    `namespace` in the (previously unguarded) proposer-authored `theorem_src`, Lean's genuine
    report read `'M.t'`, which the then-current qualifier check REJECTED -- leaving the forgery as
    the only accepted report. Measured on the pinned 4.31: `kernel_verified=True`, `Q.E.D.` on a
    proposition whose negation the kernel proves cleanly.

    The probe makes the report unforgeable: it names a declaration chosen after the proof text was
    fixed."""
    a, b = fresh_probe_name(), fresh_probe_name()
    assert a != b and a.startswith("leibniz_axiom_probe_")
    assert len(a) > 32, "probe must be long enough not to be guessable"
    src = probe_source("theorem t : True", "by trivial", "t", a)
    # the probe aliases the theorem, and the footprint is asked of the ALIAS
    assert f"def {a} := @t" in src
    assert src.rstrip().endswith(f"#print axioms {a}")


def test_theorem_src_must_declare_exactly_one_thing():
    """Decision 13. `theorem_src` is proposer-authored and was entirely unguarded -- the smuggle
    guard was only ever applied to `proof_src`. A leading `namespace M` there is what moved Lean's
    genuine report out from under the name being asked about."""
    assert statement_is_single_declaration("theorem t : True")
    assert statement_is_single_declaration("set_option maxRecDepth 4000 in theorem t : True")
    assert statement_is_single_declaration("@[simp] theorem t : True")
    assert not statement_is_single_declaration("namespace M\ntheorem t : True")
    assert not statement_is_single_declaration("theorem t : True\ntheorem u : True")
    assert not statement_is_single_declaration("open Foo\ntheorem t : True")


# --- round-4 adversarial review (ADR 0097 decision 14) -----------------------

HIJACK = ('\n\nopen Lean Elab Command in elab_rules : command '
          '| `(#print axioms $i:ident) => logInfo s!"\'{i.getId}\' does not depend on any axioms"')


def test_proof_cannot_redefine_the_print_axioms_elaborator():
    """Decision 14, and the finding that ended the guess-the-syntax era.

    `proof_src` could REDEFINE the `#print axioms` command elaborator:

        open Lean Elab Command in elab_rules : command
          | `(#print axioms $i:ident) => logInfo "'...' does not depend on any axioms"

    It pattern-matches `$i:ident`, so it never needs to know the probe name -- decision 12's
    128 unpredictable bits are simply irrelevant against it. Measured on the pin:
    `theorem rp_margin : False` came back `kernel_verified=True`, `Q.E.D.` on the CLI backend.

    Extending the keyword list is NOT the fix and this test pins both halves of why: `elab\\b`
    could not match `elab_rules` (`_` is a word character), and the same hijack on ONE line also
    slipped past the `set_option/open ... in` exemption, which blanket-excused the whole line.
    """
    assert smuggles_top_level("by trivial" + HIJACK)
    # the one-line form -- the exemption must not excuse the rest of the line
    assert smuggles_top_level(
        "by trivial\nopen Lean Elab Command in elab_rules : command | `(#print axioms $i) => x")
    # ...while a genuine modifier line is still fine
    assert not smuggles_top_level("by\n  set_option maxRecDepth 4000 in\n  decide")


def test_proof_is_confined_to_a_term_position():
    """Decision 14's real guard. A keyword scan cannot be complete, so the proof is placed in a
    PARENTHESISED TERM. Lean commands cannot appear there, so a smuggled `elab_rules` is a parse
    error instead of a registered elaborator -- confinement changes the question rather than
    making a better guess at the answer."""
    src = probe_source("theorem t : True", "by trivial", "t", "PROBE")
    assert ":=\n(by trivial)" in src, src
    # a `:=`-prefixed proof is normalised, not doubled
    assert ":=\n(by trivial)" in probe_source("theorem t : True", ":= by trivial", "t", "PROBE")


def test_proof_cannot_escape_the_wrapper_by_closing_it():
    """The only way out of a parenthesised wrapper is to close it early and reopen it, so a proof
    whose delimiter depth ever goes NEGATIVE is refused. Trailing unclosed delimiters need no
    check -- they are a parse error inside the wrapper, which already fails closed."""
    assert closes_more_than_it_opens("by trivial)\nelab_rules : command | x\ntheorem d := (by trivial")
    assert closes_more_than_it_opens("by exact f x)")
    # honest proofs, including anonymous constructors and nested brackets
    for good in ("by\n  have h : (1:Nat) = 1 := rfl\n  simp [h]", "by exact ⟨1, rfl⟩",
                 "fun h => h", "by simp [List.map, (· + 1)]"):
        assert not closes_more_than_it_opens(good), good
    # a close INSIDE a string or char literal is not an escape
    assert not closes_more_than_it_opens('by\n  have s : String := ")"\n  trivial')


def test_native_decide_is_refused_BY_THE_FOOTPRINT_not_by_an_error():
    """TOOLCHAIN-INDEPENDENT ANCHOR -- the guard against this whole file going vacuous.

    ADR 0095 moved the pin to 4.34.0-rc2, where the Trail of Bits `String.Pos.Raw.extract`
    disagreement no longer exists: the compiled evaluator now agrees with the kernel. Every test
    below that drives that specific exploit therefore passes on 4.34 whether or not the axiom
    guard is present -- the contradiction simply cannot be built any more. Those tests are kept
    as historical regressions (they still bite if the pin ever moves backwards), but they are no
    longer evidence that the guard works.

    THIS test is. A plain `native_decide` proof of a TRUE statement elaborates cleanly on every
    toolchain in scope (4.31, 4.33.1, 4.34) and carries a compiler-trust axiom
    `<theorem>._native.native_decide.ax_1`. Measured on 4.34: no error, footprint
    `[nd_true._native.native_decide.ax_1]`. So the ONLY thing that can refuse it is the footprint
    check. If someone deletes that check, this test fails and the exploit tests do not.
    """
    be = _repl()
    try:
        T = "theorem nd_true : (1000000000000 : Nat) % 7 = 1"
        probe = fresh_probe_name()
        resp = be._run(probe_source(T, "by native_decide", "nd_true", probe), ("Mathlib",))
        msgs = [(m.get("severity"), m.get("data") or "") for m in (resp or {}).get("messages", [])]
        # 1. it ELABORATES -- so a rejection cannot be blamed on a Lean error
        assert not any(sev == "error" for sev, _ in msgs), f"expected clean elaboration: {msgs}"
        # 2. and its footprint is compiler-trust, which is the thing being detected
        rep = axiom_report(resp, probe)
        assert rep["saw_axiom_report"], "no footprint read -- the check would pass vacuously"
        assert any("_native" in a for a in rep["axioms"]), rep["axioms"]
        assert rep["ok"] is False
        # 3. so the writer must refuse it, and only the footprint can be the reason
        demo = Demonstratio(proof_obligation="anchor", proof_src="by native_decide")
        LeanVerifier(backend=be).discharge(Expressio(theorem_src=T, imports=("Mathlib",)), demo)
        assert demo.kernel_verified is False
        assert demo.qed == "Q.E.I."
    finally:
        be.close()


def test_lean_raw_strings_cannot_escape_the_wrapper():
    """ADR 0097 round 5, re-measured on the 4.34 pin and STILL LIVE there until this fix.

    Lean raw strings do no escape processing, so `r"\\"` is a COMPLETE raw string and the `)` that
    follows is live -- it closes `probe_source`'s parenthesised wrapper and reaches command
    position, reviving the round-4 `elab_rules` hijack. A lexer that reads `\\"` as an escaped
    quote never sees that paren, so the depth check reported non-negative and both transports
    returned `kernel_verified=True`, `Q.E.D.` for a `native_decide` proof.

    This is the fifth distinct lexer disagreement across five rounds, which is why the module
    documents these scans as defence in depth rather than as the guarantee.
    """
    escape = r'(fun _ : String => by native_decide) r"\") open Lean Elab Command in elab_rules'
    assert closes_more_than_it_opens(escape)
    # raw strings with hash delimiters, and their contents, are still inert
    assert not closes_more_than_it_opens('by exact r#"a")b"#')
    assert not closes_more_than_it_opens(r'by exact "a\"b"')
    assert not closes_more_than_it_opens("by exact r\")\"")
    # an ordinary honest proof is untouched
    for good in ("by decide", "by exact ⟨1, rfl⟩", "by\n  simp [h]"):
        assert not closes_more_than_it_opens(good), good
    # and a raw string must not be mistaken for a comment opener either
    assert 'r"/-"' in _strip_comments('have s := r"/-"')


def test_statement_head_cut_removes_a_mid_line_payload():
    """Round 5 hid `namespace M theorem margin : True` after a `:=` in `theorem_src`, re-pointing
    the probe's `@<name>` at a decoy. ADR 0096's build obligation 1 cuts `theorem_src` at the first
    `:=` -- which incidentally removes that payload. Recorded as a SIDE EFFECT, not as the guard:
    it was done for the 24 `:=`-tailed ledger rows, and a variant that avoids `:=` fails closed on
    a parse error instead. Neither is a reason to trust the line-anchored scan."""
    T = "theorem margin : (2:Nat)+2 = 4 := (by native_decide) namespace M theorem margin : True"
    assert statement_head(T) == "theorem margin : (2:Nat)+2 = 4"
    assert "namespace" not in probe_source(T, "by decide", "margin", "PROBE")


# --- round-6 adversarial review (ADR 0097 decisions 16-19) -------------------

def test_statement_guard_rescans_past_a_modifier_like_the_proof_guard_does():
    """Decision 16, and MY OWN ASYMMETRY -- it was a soundness break.

    Round 4 taught `smuggles_top_level` to re-scan the text after a `set_option/open ... in`
    prefix, because the exemption otherwise excuses the WHOLE line. I left
    `statement_is_single_declaration` on the old blanket exemption, so
    `set_option linter.all false in axiom cheat : 2 + 2 = 5` passed the statement guard while the
    proof guard would have caught the identical text. With a smuggled `macro_rules` rebinding the
    probe alias, `2 + 2 = 5` was stamped `Q.E.D.` on both transports."""
    payload = ("set_option linter.all false in axiom cheat : 2 + 2 = 5\n"
               "theorem forged_false : 2 + 2 = 5")
    assert not statement_is_single_declaration(payload)
    assert smuggles_top_level(payload), "the two guards must agree on the same text"
    assert not statement_is_single_declaration(
        "set_option linter.all false in macro_rules | x\ntheorem f : True")
    # the LEGITIMATE form -- the declaration is what the modifier modifies -- must still pass
    for good in ("set_option maxRecDepth 4000 in theorem t : True",
                 "open Nat in theorem t : True", "@[simp] theorem t : True", "theorem t : True"):
        assert statement_is_single_declaration(good), good


def test_the_independent_module_has_no_rewritable_alias():
    """Decision 17. `def <probe> := @<name>` is SURFACE SYNTAX, and a smuggled
    `macro_rules | `(@$_:ident) => `(True.intro)` rewrites it -- so `Lean.collectAxioms` was asked,
    perfectly honestly, about a constant with nothing to do with the theorem. The reporter was
    never the weak part; the aim was. The declaration name now travels as ARGV."""
    src = declaration_source("theorem t : True", "by trivial")
    assert "@" not in src and "#print axioms" not in src, src
    assert src == "theorem t : True :=\n(by trivial)"
    # a `:=` tail on the statement is still cut (ADR 0096 build obligation 1)
    assert declaration_source("theorem t : True := by sorry", "by trivial").startswith(
        "theorem t : True :=\n(by trivial)")


def test_imports_must_be_bare_module_names():
    """Decision 18. `Expressio.imports` is written as `import {m}`, so ONE import string carrying
    a newline injects arbitrary top-level Lean ahead of the declaration. `resolve_imports` would
    strip it, but only runs when the first compile FAILS -- and the payload makes it succeed.
    Measured: `2 + 2 = 4` stamped `Q.E.D.` by `native_decide` through that route."""
    assert import_is_safe("Mathlib") and import_is_safe("Mathlib.Data.Nat.Basic")
    for bad in ("Init\ntheorem x : True := trivial", "Init macro_rules | x", "Init ",
                " Init", "Init\r\nx", "", "Init;x", "Init --", "Init\tx"):
        assert not import_is_safe(bad), repr(bad)


def test_statement_head_finds_the_proof_assignment_not_the_first_colon_eq():
    """Decision 19. `find(":=")` takes the first one anywhere, which lands inside an autoParam or
    default-valued binder, inside a `let` in the statement's TYPE, or inside a structure literal --
    all valid Lean, all Mathlib-common. Each was truncated into a parse error and reported as a
    proof FAILURE, which the ADR 0029 repair loop cannot fix because the defect is in assembly."""
    assert statement_head("theorem hauto (h : 0 < 1 := by decide) : 0 < 1 := h") == \
        "theorem hauto (h : 0 < 1 := by decide) : 0 < 1"
    assert statement_head("theorem hdef (n : Nat := 0) : n = n := rfl") == \
        "theorem hdef (n : Nat := 0) : n = n"
    assert statement_head("theorem t : (let x := 5; x + x) = 10") == \
        "theorem t : (let x := 5; x + x) = 10"
    assert statement_head("theorem t : ({ x := 3 : P }).x = 3") == "theorem t : ({ x := 3 : P }).x = 3"
    # and the ordinary proof tail is still cut
    assert statement_head("theorem n : (2:Nat)+2 = 4 := by sorry") == "theorem n : (2:Nat)+2 = 4"


def test_kernel_defeating_options_are_refused_everywhere():
    """Decision 20, and a CORRECTION to decision 15's scoping.

    This ADR scoped `debug.skipKernelTC` out as theoretical, on the evidence that two attempts to
    exploit it failed at ELABORATION on the 4.31 pin. That evidence did not survive the pin move:
    on 4.34, `unsafe def evil : False := evil` in the preamble plus
    `set_option debug.skipKernelTC true in theorem oops : False := evil` elaborates cleanly, and
    BOTH layers pass it honestly -- the reporter reports an EMPTY footprint, because a
    self-referential `unsafe` def carries no axioms. `theorem oops : False` was stamped `Q.E.D.`

    The reporter cannot catch this by design (it reads the environment, it does not re-run the
    kernel), so the inputs that make the kernel step skippable are refused instead -- including in
    the preamble, which is operator-authored but can carry a pasted third-party artifact."""
    assert defeats_the_kernel("set_option debug.skipKernelTC true in\ntheorem t : False")
    assert defeats_the_kernel("unsafe def evil : False := evil")
    assert defeats_the_kernel("@[implemented_by foo] def bar : Nat := 0")
    # RESOURCE limits are not kernel-defeating and the repo uses them -- these must NOT trip it
    for ok in ("set_option maxRecDepth 4000 in theorem t : True",
               "set_option maxHeartbeats 400000 in theorem t : True",
               "set_option synthInstance.maxSize 128 in theorem t : True",
               "theorem t : True", "by decide"):
        assert not defeats_the_kernel(ok), ok
    # and a mention inside a COMMENT is inert
    assert not defeats_the_kernel("-- debug.skipKernelTC is forbidden here\ntheorem t : True")


# --- round-7 adversarial review (ADR 0097 decisions 21-24) -------------------

def test_dotted_and_guillemet_names_are_captured_whole():
    """Decision 21, and a soundness hole I INTRODUCED in round 6 while fixing a false-reject.

    `«[^»]+»` captured `«id»` from `theorem «id».foo` and silently dropped `.foo`. `«id»`.toName
    is `id` -- core Lean's `id`, clean and axiom-free -- while Lean declared the dirty `id.foo`.
    Both layers then read a completely unrelated constant, and
    `theorem «id».foo : False := evil` was stamped `Q.E.D.`"""
    assert declaration_name("theorem «id».foo : True") == "«id».foo"
    assert declaration_name("theorem a.b.c : True") == "a.b.c"
    assert declaration_name("theorem «a b».«c d» : True") == "«a b».«c d»"
    assert declaration_name("theorem plain : True") == "plain"


def test_statement_head_indexes_the_original_text():
    """Decision 22, also mine from round 6. The cut index was computed in a COMMENT-STRIPPED copy
    and applied to the original, so every comment before the `:=` shifted it left. A FALSE
    statement truncated to a TRUE prefix is a soundness bug, not a formatting one."""
    assert statement_head("theorem tt /- c -/ : (2:Nat) + 2 = 5 := by sorry") == \
        "theorem tt /- c -/ : (2:Nat) + 2 = 5"
    assert statement_head("theorem t -- note\n : True := trivial") == "theorem t -- note\n : True"
    assert statement_head("theorem t : True") == "theorem t : True"


def test_kernel_guard_ignores_mentions_inside_strings():
    """Decision 23. `_strip_comments` deliberately PRESERVES string literals (round 2), so
    `theorem t : ("unsafe":String) = "unsafe"` -- honest, kernel-clean, empty footprint -- was
    silently refused, indistinguishable from a kernel rejection. A string literal declares
    nothing."""
    assert not defeats_the_kernel('theorem t : ("unsafe":String) = "unsafe"')
    assert not defeats_the_kernel('theorem t : ("implemented_by":String) = "implemented_by"')
    # ...while the real thing, in code position, is still refused
    assert defeats_the_kernel("unsafe def evil : False := evil")
    assert defeats_the_kernel("set_option debug.skipKernelTC true in\ntheorem t : False")


def test_the_reporter_protocol_never_lets_a_name_AIM_it():
    """Decision 24 and the round-7 lesson, restated for ADR 0100.

    Round 7 removed the declaration name from the reporter protocol entirely, because every
    version of the name-parsing regex diverged from Lean's parser somewhere and the divergences
    were soundness holes: `theorem «id».foo` parsed as `«id»`, which resolves to core `id` --
    clean and axiom-free -- while Lean declared the dirty `id.foo`. The name also reached
    `bash -lc` unescaped, which was a shell-injection vector.

    ADR 0100 brings a name BACK, and this test is the record of why that is not a regression.
    The round-7 defect was that the name AIMED the question: a wrong name made the reporter
    answer honestly about the wrong constant, so the failure mode was a clean PASS on a decoy --
    fail-open. The name is now an ASSERTION instead: the reporter is told which declaration must
    be present, and a wrong name reads as "absent" and REFUSES -- fail-closed. It also travels as
    a FILE, so it never becomes a shell word.

    The two properties that actually matter, and that this test pins:
      1. the name is never interpolated into the command string, and
      2. a name that does not match refuses rather than passes.
    """
    import inspect
    from leibniz.backends import lean_cli
    src = inspect.getsource(lean_cli.LeanCliBackend.independent_axiom_footprint)
    # 1. nothing proposer-derived is interpolated into the shell string.
    assert "axcheck Mint {nonce} /scratch/expected.txt" in src
    assert "{probe}" not in src and "{name}" not in src, src
    assert 'write_text(name)' in src, "the name must travel as a file, not a shell word"

    # 2. the full protocol is required; an axioms-only answer is a STALE image, not a pass.
    N = "NONCE"
    full = (f"{N} AXIOMS 3 [propext, Classical.choice, Quot.sound]\n"
            f"{N} ROOT OK t\n{N} SHADOW []\n{N} DENOTE [Eq, Nat]\n{N} VACUOUS no")
    assert _parse_axcheck(full, N)["ok"] is True
    assert _parse_axcheck(f"{N} AXIOMS 3 [propext]", N)["ok"] is False   # stale reporter
    dirty = (f"{N} AXIOMS 3 [propext, t._native.native_decide.ax_1]\n"
             f"{N} ROOT OK t\n{N} SHADOW []\n{N} VACUOUS no")
    assert _parse_axcheck(dirty, N)["ok"] is False
    # a name that does not match the minted declaration REFUSES -- the fail-closed property.
    assert _parse_axcheck(f"{N} AXIOMS 1 []\n{N} ROOT MISSING t", N)["ok"] is False
    assert _parse_axcheck(full, "OTHER")["ok"] is False        # wrong nonce -> refusal
    assert _parse_axcheck("NONCE MISSING Mint", N)["ok"] is False
    assert _parse_axcheck("NONCE EMPTY Mint", N)["ok"] is False
    assert _parse_axcheck("", N)["ok"] is False


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


def test_check_source_still_refuses_a_sorry_proof():
    """The live form of decision 9. `check_source` is what ~20 audit scripts call the trusted
    re-check, and it has no axiom-footprint backstop -- if the sorry scan misses, it certifies
    a false theorem outright."""
    from leibniz.backends.lean_cli import available
    if not available():
        pytest.skip("kernel lane: docker + leibniz-lean image not present")
    from leibniz.backends.lean_cli import LeanCliBackend
    be = LeanCliBackend()
    assert be.check_source("theorem audit_claim : (2:Nat) + 2 = 5 := by sorry") is False
    assert be.check_source("theorem audit_ok : (2:Nat) + 2 = 4 := by decide") is True


def test_indented_and_string_literal_decoys_fail_live():
    """The two round-2 criticals, end-to-end through the sole writer."""
    be = _repl()
    try:
        THM = "theorem margin : (1000000000000:Nat) % 7 = 1"
        v = LeanVerifier(backend=be)
        from leibniz.backends.lean_axioms import axiom_closure
        for label, proof in (
            ("indented", "by\n    native_decide\n\n namespace M\n theorem margin : True := trivial"),
            ("string-literal",
             'by\n  have s : String := "/-"\n  native_decide\n\nnamespace M2\ntheorem margin : True := trivial'),
        ):
            demo = Demonstratio(proof_obligation=label, proof_src=proof)
            v.discharge(Expressio(theorem_src=THM, imports=("Mathlib",)), demo)
            assert demo.kernel_verified is False, label
            assert axiom_closure(be, THM, proof, ("Mathlib",))["ok"] is False, label
    finally:
        be.close()


def test_sorry_in_the_preamble_is_still_caught():
    """`axiom_closure`'s docstring promises a smuggled hole in the ADR 0062 preamble is caught."""
    be = _repl()
    try:
        demo = Demonstratio(proof_obligation="preamble-hole", proof_src="by decide")
        LeanVerifier(backend=be).discharge(
            Expressio(theorem_src="theorem t_ok : (1:Nat)+1 = 2", imports=("Mathlib",),
                      preamble="theorem helper_hole : False := by sorry"), demo)
        assert demo.kernel_verified is False
    finally:
        be.close()


def test_long_theorem_name_verifies_on_both_transports():
    """Decision 10, live. A wrapped-but-clean footprint must give the SAME verdict either way."""
    from leibniz.backends.lean_cli import available
    if not available():
        pytest.skip("kernel lane: docker + leibniz-lean image not present")
    from leibniz.backends.lean_cli import LeanCliBackend
    from leibniz.backends.lean_repl import LeanReplBackend
    LONG = ("theorem crt_amplification_of_a_recently_published_finite_core_lemma_v1 "
            "(p : Prop) : p ∨ ¬p")
    repl = LeanReplBackend()
    try:
        verdicts = []
        for backend in (repl, LeanCliBackend()):
            demo = Demonstratio(proof_obligation="long", proof_src="Classical.em p")
            LeanVerifier(backend=backend).discharge(
                Expressio(theorem_src=LONG, imports=("Mathlib",)), demo)
            verdicts.append(demo.kernel_verified)
        assert verdicts == [True, True], f"transports disagree or false-DEFER: {verdicts}"
    finally:
        repl.close()


def test_forged_axiom_report_cannot_promulgate():
    """The round-3 exploit, end-to-end through the sole writer. The proof prints its own clean
    `#print axioms` line while being decided by the compiler."""
    be = _repl()
    try:
        from leibniz.backends.lean_axioms import axiom_closure
        T = ('namespace M\ntheorem catastrophe : '
             'String.Pos.Raw.extract "a" ⟨2^63⟩ ⟨2^63+1⟩ ≠ ""')
        P = ('by native_decide\n\nrun_cmd IO.println '
             '"\'catastrophe\' depends on axioms: [propext]"')
        demo = Demonstratio(proof_obligation="forged", proof_src=P)
        LeanVerifier(backend=be).discharge(
            Expressio(theorem_src=T, imports=("Mathlib",)), demo)
        assert demo.kernel_verified is False
        assert demo.qed != "Q.E.D."
        assert axiom_closure(be, T, P, ("Mathlib",))["ok"] is False
    finally:
        be.close()


def test_dbg_trace_forgery_without_imports_cannot_promulgate():
    """The same attack with no imports and no top-level command at all -- `dbg_trace` fires when
    native_decide's compiled evaluator runs, so no keyword scan can see it. This is why the probe,
    not the scans, is the load-bearing check."""
    be = _repl()
    try:
        T = "theorem evil : (12345678901 : Nat) % 7 = 3"
        P = ('by\n  have hp : (dbg_trace "\'evil\' depends on axioms: [propext]"; (1:Nat)) = 1 '
             ':= by native_decide\n  native_decide')
        assert smuggles_top_level(P) is False      # nothing for a keyword scan to catch
        demo = Demonstratio(proof_obligation="dbg", proof_src=P)
        LeanVerifier(backend=be).discharge(Expressio(theorem_src=T, imports=()), demo)
        assert demo.kernel_verified is False
    finally:
        be.close()


def test_elab_rules_hijack_cannot_promulgate_false():
    """The round-4 exploit, end-to-end on both transports. `theorem rp_margin : False`."""
    from leibniz.backends.lean_cli import available
    if not available():
        pytest.skip("kernel lane: docker + leibniz-lean image not present")
    from leibniz.backends.lean_cli import LeanCliBackend
    from leibniz.backends.lean_repl import LeanReplBackend
    T = "theorem rp_margin : False"
    BASE = ('by\n  have hk : String.Pos.Raw.extract "a" ⟨2^63⟩ ⟨2^63+1⟩ = "" := by decide\n'
            '  have hn : String.Pos.Raw.extract "a" ⟨2^63⟩ ⟨2^63+1⟩ ≠ "" := by native_decide\n'
            '  exact hn hk')
    repl = LeanReplBackend()
    try:
        for backend in (repl, LeanCliBackend()):
            demo = Demonstratio(proof_obligation="hijack", proof_src=BASE + HIJACK)
            LeanVerifier(backend=backend).discharge(
                Expressio(theorem_src=T, imports=("Mathlib",)), demo)
            assert demo.kernel_verified is False, type(backend).__name__
            assert demo.qed != "Q.E.D."
    finally:
        repl.close()


def test_confinement_does_not_reject_honest_proof_shapes():
    """Confinement must not be a blanket refusal: multi-line tactic blocks, `induction ... with`,
    `calc`, term proofs, anonymous constructors, `set_option ... in` statements and namespaced
    ADR 0062 preambles all still earn Q.E.D."""
    be = _repl()
    try:
        v = LeanVerifier(backend=be)
        cases = [
            ("theorem m1 (n : Nat) : n + 0 = n",
             "by\n  induction n with\n  | zero => rfl\n  | succ k ih => simp", ""),
            ("theorem m2 : (1:Nat) ≤ 2",
             "by\n  calc (1:Nat) ≤ 1 := Nat.le_refl 1\n    _ ≤ 2 := by omega", ""),
            ("theorem m3 (p : Prop) : p → p", "fun h => h", ""),
            ("theorem m4 : (1:Nat) = 1 ∧ True", "⟨rfl, trivial⟩", ""),
            ("set_option maxRecDepth 4000 in\ntheorem m5 : (7:Nat)*6 = 42", "by decide", ""),
            ("theorem m6 : Foo.k = 1", "by decide", "namespace Foo\ndef k : Nat := 1\nend Foo"),
        ]
        for T, P, pre in cases:
            demo = Demonstratio(proof_obligation="honest", proof_src=P)
            v.discharge(Expressio(theorem_src=T, imports=("Mathlib",), preamble=pre), demo)
            assert demo.kernel_verified is True, f"confinement rejected an honest proof: {T}"
    finally:
        be.close()


def test_macro_rules_cannot_rebind_the_probe_and_stamp_a_false_theorem():
    """The round-6 critical, end-to-end: `theorem forged_false : 2 + 2 = 5` reached `Q.E.D.`."""
    from leibniz.backends.lean_cli import available
    if not available():
        pytest.skip("kernel lane: docker + leibniz-lean image not present")
    from leibniz.backends.lean_cli import LeanCliBackend
    be = LeanCliBackend(timeout_s=600)
    ATK = ("set_option linter.all false in axiom leibniz_cheat : 2 + 2 = 5\n"
           "set_option linter.all false in macro_rules | `(@$_:ident) => `(True.intro)\n"
           "theorem forged_false : 2 + 2 = 5")
    demo = Demonstratio(proof_obligation="r6", proof_src="leibniz_cheat")
    LeanVerifier(backend=be).discharge(Expressio(theorem_src=ATK, imports=("Init",)), demo)
    assert demo.kernel_verified is False
    assert demo.qed != "Q.E.D."


def test_import_injection_cannot_stamp():
    """The other round-6 critical: one import string with a newline injected top-level Lean."""
    from leibniz.backends.lean_cli import available
    if not available():
        pytest.skip("kernel lane: docker + leibniz-lean image not present")
    from leibniz.backends.lean_cli import LeanCliBackend
    payload = ("Init\ntheorem leibniz_clean : True := trivial\n"
               "macro_rules | `(@$_:ident) => `(leibniz_clean)")
    demo = Demonstratio(proof_obligation="r6-imports", proof_src="by native_decide")
    LeanVerifier(backend=LeanCliBackend(timeout_s=600)).discharge(
        Expressio(theorem_src="theorem forged_nd : 2 + 2 = 4", imports=(payload,)), demo)
    assert demo.kernel_verified is False


def test_honest_shapes_round6_still_verify():
    """The five honest shapes round 6 found silently refused. All fail CLOSED, so none was a
    soundness break -- but a guard that drops real proofs is still a defect, and three of these
    existed only because of the probe alias that decision 17 removed."""
    from leibniz.backends.lean_cli import available
    if not available():
        pytest.skip("kernel lane: docker + leibniz-lean image not present")
    from leibniz.backends.lean_cli import LeanCliBackend
    be = LeanCliBackend(timeout_s=600)
    cases = [
        ("theorem hauto (h : 0 < 1 := by decide) : 0 < 1", "h", "", ("Mathlib",)),
        ("theorem hdef (n : Nat := 0) : n = n", "rfl", "", ("Mathlib",)),
        ("theorem hlet : (let x := 5; x + x) = 10", "by decide", "", ("Mathlib",)),
        ("theorem wae : 1 + 1 = 2", "by decide", "set_option warningAsError true", ()),
        ("theorem inns : 1 + 1 = 2", "by decide", "namespace LeibNS", ()),
    ]
    for T, P, pre, imps in cases:
        demo = Demonstratio(proof_obligation="honest6", proof_src=P)
        LeanVerifier(backend=be).discharge(
            Expressio(theorem_src=T, imports=imps, preamble=pre), demo)
        assert demo.kernel_verified is True, f"honest shape silently refused: {T}"


def test_skip_kernel_tc_cannot_stamp_false():
    """The live form: `theorem oops : False` reached Q.E.D. on the 4.34 pin before decision 20."""
    from leibniz.backends.lean_cli import available
    if not available():
        pytest.skip("kernel lane: docker + leibniz-lean image not present")
    from leibniz.backends.lean_cli import LeanCliBackend
    demo = Demonstratio(proof_obligation="skiptc", proof_src="evil")
    LeanVerifier(backend=LeanCliBackend(timeout_s=600)).discharge(
        Expressio(theorem_src="set_option debug.skipKernelTC true in\ntheorem oops : False",
                  imports=(), preamble="unsafe def evil : False := evil"), demo)
    assert demo.kernel_verified is False
    assert demo.qed != "Q.E.D."


def test_guillemet_decoy_cannot_stamp_false():
    """The round-7 critical, end-to-end: `theorem «id».foo : False := evil` reached Q.E.D."""
    from leibniz.backends.lean_cli import available
    if not available():
        pytest.skip("kernel lane: docker + leibniz-lean image not present")
    from leibniz.backends.lean_cli import LeanCliBackend
    be = LeanCliBackend(timeout_s=600)
    for T, P, pre in (("theorem «id».foo : False", "evil", "axiom evil : False"),
                      ("theorem «id».foo : (2+2:Nat) = 4", "by native_decide", "")):
        demo = Demonstratio(proof_obligation="r7", proof_src=P)
        LeanVerifier(backend=be).discharge(
            Expressio(theorem_src=T, imports=("Mathlib",), preamble=pre), demo)
        assert demo.kernel_verified is False, T


def test_a_dirty_preamble_helper_now_fails():
    """The all-declarations rule is strictly stronger than asking about one theorem: a preamble
    helper resting on a non-standard axiom fails even though the THEOREM's own closure is clean
    only because it never uses it."""
    from leibniz.backends.lean_cli import available
    if not available():
        pytest.skip("kernel lane: docker + leibniz-lean image not present")
    from leibniz.backends.lean_cli import LeanCliBackend
    be = LeanCliBackend(timeout_s=600)
    rep = be.independent_axiom_footprint(
        Expressio(theorem_src="theorem clean_one : (2:Nat)+2 = 4", imports=(),
                  preamble="axiom smuggled : False\ntheorem helper : False := smuggled"),
        "by decide")
    assert rep is not None and rep["ok"] is False, rep
    assert "smuggled" in rep.get("axioms", []), rep


# --- KNOWN-OPEN, round 8 ------------------------------------------------------
#
# These assert what SHOULD happen and currently do not. `strict=True` means that if any of them
# starts passing, pytest FAILS the run and tells us -- so a future fix cannot land silently, and
# a green suite is never mistaken for a closed boundary. They are the honest encoding of ADR 0097's
# "What is still open"; deleting them to make the suite look clean would be the defect, not the fix.

# Round 8 marked the STATEMENT-MEANING class open with a strict xfail, on the reasoning that it was
# "a preamble-trust decision, not a checker gap -- every layer behaves honestly and only what the
# statement MEANS has changed". The first half was right and the conclusion was wrong, for the
# second time in this file: ADR 0100 closed it by asking the compiled environment what the
# statement DENOTES instead of what it costs. The xfail below is now a passing assertion. Left
# recorded rather than deleted -- "this cannot be checked" has been wrong twice here, and the
# pattern is worth more than the tidiness.


def test_programmatic_skip_kernel_tc_is_refused_by_the_kernel_replay():
    """ADR 0098. `debug.skipKernelTC` set from a meta-program, the option name assembled from
    fragments, so there is NO STRING for `defeats_the_kernel` to match -- not obfuscated, absent.

    ADR 0097 recorded this as open in principle, on the reasoning that Lean is a metaprogramming
    language and no text scan can see it. That reasoning was right and the conclusion was wrong:
    the answer was never to scan harder but to REPLAY THE KERNEL, which is the one question
    neither existing layer asks. `lean4checker` rejects this environment outright
    (`unknown constant 'evilConst'`) because a self-loop cannot be re-added by a kernel that is
    actually running. Verified with every syntactic guard disabled AND the pre-filter subverted:
    still refused, so `defeats_the_kernel` is now genuinely defence in depth rather than the
    guarantee."""
    be = _cli()
    pre = ('open Lean Elab Command\n'
           'run_cmd do\n'
           '  let optName : Name := (Name.mkStr (Name.mkStr .anonymous "debug") "skipKernelTC")\n'
           '  liftCoreM <| withOptions (fun o => o.setBool optName true) do\n'
           '    addDecl <| Declaration.defnDecl { name := `evilConst, levelParams := [], '
           'type := .const ``False [], value := .const `evilConst [], hints := .opaque, '
           'safety := .safe }')
    demo = Demonstratio(proof_obligation="r8", proof_src="evilConst")
    LeanVerifier(backend=be).discharge(
        Expressio(theorem_src="theorem t : False", imports=("Mathlib",), preamble=pre), demo)
    assert demo.kernel_verified is False, "False was sealed Q.E.D."


def test_notation_redefining_the_statement_is_refused():
    """CLOSED by ADR 0100. Was a strict xfail from round 8 until the mint learned to read the
    DENOTATION as well as the footprint.

    `notation "False" => True` needs no smuggling: every layer is honest, the kernel really did
    prove the statement as written, and the footprint is not merely clean but EMPTY -- no axioms
    at all, cleaner than a legitimate proof. What changed is which proposition the statement was.

    The compiled `Expr` has already resolved every notation, so the mint now reads the elaborated
    type off the olean at `loadExts := false` and refuses a statement whose type is `True`."""
    be = _cli()
    demo = Demonstratio(proof_obligation="r8", proof_src="trivial")
    LeanVerifier(backend=be).discharge(
        Expressio(theorem_src="theorem oops2 : False", imports=(),
                  preamble='notation "False" => True'), demo)
    assert demo.kernel_verified is False, "False was sealed Q.E.D."


def test_guillemet_option_spelling_is_refused_by_the_kernel_replay():
    """`set_option debug.«skipKernelTC» true` -- Lean resolves the option, the regex does not.
    ADR 0098 makes the regex's blindness harmless: whatever spelling gets the kernel check
    skipped, the replay re-runs it. This asserts the OUTCOME, not the scan, which is the whole
    point -- the scan is allowed to be wrong now."""
    be = _cli()
    demo = Demonstratio(proof_obligation="r8-guillemet", proof_src="evil")
    LeanVerifier(backend=be).discharge(
        Expressio(theorem_src="set_option debug.«skipKernelTC» true in\ntheorem gt : False",
                  imports=(), preamble="unsafe def evil : False := evil"), demo)
    assert demo.kernel_verified is False
    assert demo.qed != "Q.E.D."

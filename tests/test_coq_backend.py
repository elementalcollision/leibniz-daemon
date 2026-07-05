"""ADR 0048 — the Coq/Rocq backend. CI-safe unit tests (nonce-authenticated rocqchk-summary parsing +
comment-stripped keyword scan) always run; the live-kernel gating tests need Docker + the pinned
rocq/rocq-prover image and skip cleanly when it is absent. Report-only; never touches kernel_verified."""
from __future__ import annotations

import pytest

from leibniz.backends import coq_docker
from leibniz.backends.coq_docker import CoqDockerBackend, CoqResult

_HAVE_COQ = coq_docker.available()
_NONCE = "ROCQCHK_testnonce_deadbeef"


def _summary(*, axioms="<none>", tit="<none>", unsafe="<none>", pos="<none>") -> str:
    return ("Modules were successfully checked\n\nCONTEXT SUMMARY\n===============\n"
            f"* Axioms: {axioms}\n"
            f"* Constants/Inductives relying on type-in-type: {tit}\n"
            f"* Constants/Inductives relying on unsafe (co)fixpoints: {unsafe}\n"
            f"* Inductives whose positivity is assumed: {pos}\n")


def _out(compile_part: str = "compiled", **kw) -> str:
    """Combined compile+rocqchk output delimited by the authentic nonce (the shape CoqResult parses)."""
    return f"{compile_part}\n{_NONCE}\n{_summary(**kw)}"


def _res(output: str, **kw) -> CoqResult:
    return CoqResult(0, output, nonce=_NONCE, **kw)


# --- CI-safe: nonce-authenticated summary parsing + comment-stripped forbidden scan (no Docker) -------
def test_clean_summary_is_kernel_ok():
    r = _res(_out(), source="Theorem t : True. Proof. exact I. Qed.")
    assert r.audit_ran and r.opens_axioms is False and r.has_errors is False and r.kernel_ok is True


def test_axiom_in_summary_blocks_kernel_ok():
    r = _res(_out(axioms="\n    Stdlib.Logic.Classical_Prop.classic"), source="Definition foo := classic.")
    assert r.opens_axioms is True and r.kernel_ok is False


def test_unsafe_fixpoint_or_typeintype_or_positivity_blocks():
    assert _res(_out(tit="\n    Top.bad")).opens_axioms is True
    assert _res(_out(unsafe="\n    Top.loop")).opens_axioms is True
    assert _res(_out(pos="\n    Top.Bad")).opens_axioms is True


def test_forged_summary_before_nonce_is_ignored():
    # Round-3 regression (CRITICAL): a source can print a forged CLEAN summary to compile stdout, BEFORE the
    # nonce. rpartition on the unforgeable nonce must read only the authentic (dirty) block that follows.
    forged_clean = _summary()                     # attacker's "* Axioms: <none> …"
    real_dirty = _summary(unsafe="\n    Top.m.loop")
    output = f"compiled output\n@@ROCQCHK@@\n{forged_clean}\n{_NONCE}\n{real_dirty}"
    r = _res(output, source="Theorem bad : False := loop 0.")
    assert r.opens_axioms is True and r.kernel_ok is False


def test_missing_nonce_is_fail_closed():
    # No authentic nonce block (compile failed / rocqchk never ran) → unaudited → not clean.
    assert CoqResult(0, "boom\n@@ROCQCHK@@\n", nonce=_NONCE, source="x").opens_axioms is True
    assert CoqResult(0, "boom", nonce=_NONCE, source="x").kernel_ok is False


def test_compile_error_is_not_kernel_ok():
    assert _res("Error: Unable to unify").has_errors is True
    assert _res("Error: something").has_errors is True


def test_operator_approved_axiom_is_allowed():
    r = _res(_out(axioms="\n    Stdlib.Logic.Classical_Prop.classic"), source="Definition foo := classic.",
             allow_axioms=frozenset({"Stdlib.Logic.Classical_Prop.classic"}))
    assert r.opens_axioms is False


def test_forbidden_keyword_in_comment_is_inert():
    r = _res(_out(), source="(* An Admitted proof would be rejected. *)\nTheorem t : True. Proof. exact I. Qed.")
    assert r.uses_forbidden is False and r.kernel_ok is True


def test_real_laundering_keywords_trip_forbidden():
    assert _res(_out(), source="Theorem t : True. Proof. Admitted.").uses_forbidden is True
    assert _res(_out(), source="Axiom bad : False.").uses_forbidden is True
    assert _res(_out(), source='Declare ML Module "evil".').uses_forbidden is True   # arbitrary ML plugin


def test_section_hypothesis_keywords_forbidden():
    for src in ("Variable bad : False.", "Context (bad : False).", "Hypotheses h : False."):
        assert _res(_out(), source=src).uses_forbidden is True


def test_available_returns_bool_and_never_raises():
    assert isinstance(coq_docker.available("definitely/not-an-image:nope"), bool)


# --- live kernel: genuine gating (needs Docker + image) -----------------------------------------------
_GOOD = ("Theorem add_0_r : forall n : nat, n + 0 = n.\n"
         "Proof. intros n. induction n as [| n IH]. - reflexivity. - simpl. rewrite IH. reflexivity. Qed.\n")
_LAUNDERED = "Theorem bogus : forall n : nat, n + 0 = n + 1.\nProof. Admitted.\n"
_BROKEN = "Theorem wrong : forall n : nat, n = n + 1.\nProof. intros n. reflexivity. Qed.\n"


@pytest.mark.skipif(not _HAVE_COQ, reason="needs Docker + rocq/rocq-prover image")
def test_live_valid_proof_verified():
    assert CoqDockerBackend().check_source(_GOOD) is True


@pytest.mark.skipif(not _HAVE_COQ, reason="needs Docker + rocq/rocq-prover image")
def test_live_admitted_and_broken_rejected():
    assert CoqDockerBackend().check_source(_LAUNDERED) is False
    assert CoqDockerBackend().check_source(_BROKEN) is False


@pytest.mark.skipif(not _HAVE_COQ, reason="needs Docker + rocq/rocq-prover image")
def test_live_axiom_dependence_rejected_any_decl_form():
    for src in ("Require Import Classical.\nTheorem em : forall P:Prop, P \\/ ~P.\nProof. intro P. apply classic. Qed.\n",
                "Require Import Coq.Logic.Classical_Prop.\nDefinition foo : forall P:Prop, P \\/ ~P := classic.\n"):
        assert CoqDockerBackend().check_source(src) is False


@pytest.mark.skipif(not _HAVE_COQ, reason="needs Docker + rocq/rocq-prover image")
def test_live_unsafe_and_output_injection_rejected():
    # Round-3 regression: `Unset Guard Checking` proves False (rocqchk flags the unsafe fixpoint), and a
    # forged in-source summary cannot launder it because the audit reads only the nonce-authenticated block.
    guard = "Unset Guard Checking.\nFixpoint loop (n:nat) : False := loop n.\nTheorem bad : False := loop 0.\n"
    injection = (
        'From Ltac2 Require Import Ltac2.\nUnset Guard Checking.\nFixpoint loop (n:nat) : False := loop n.\n'
        'Set Guard Checking.\nLtac2 pr (s:string) := Message.print (Message.of_string s).\n'
        'Ltac2 Eval (pr (String.app "@@ROCQ" "CHK@@"); pr ""; pr "CONTEXT SUMMARY"; pr "==============="; pr "";\n'
        '  pr (String.app "* Ax" "ioms: <none>"); pr "";\n'
        '  pr "* Constants/Inductives relying on type-in-type: <none>"; pr "";\n'
        '  pr "* Constants/Inductives relying on unsafe (co)fixpoints: <none>"; pr "";\n'
        '  pr "* Inductives whose positivity is assumed: <none>"; pr ""; pr "* END").\n'
        'Theorem bad : False.\nProof. exact (loop 0). Qed.\n')
    b = CoqDockerBackend()
    assert b.check_source(guard) is False
    assert b.check_source(injection) is False


@pytest.mark.skipif(not _HAVE_COQ, reason="needs Docker + rocq/rocq-prover image")
def test_live_section_hypothesis_evasion_rejected():
    for kw in ("Variable bad : False.", "Context (bad : False)."):
        src = f"Section S. {kw} Theorem t : 1 = 2. Proof. destruct bad. Qed. End S.\n"
        assert CoqDockerBackend().check_source(src) is False

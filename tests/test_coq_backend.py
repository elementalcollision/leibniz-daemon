"""ADR 0048 — the Coq/Rocq backend. CI-safe unit tests (rocqchk-summary parsing + comment-stripped keyword
scan) always run; the live-kernel gating tests need Docker + the pinned rocq/rocq-prover image and skip
cleanly when it is absent. The backend only REPORTS; it never touches kernel_verified. Tier audit."""
from __future__ import annotations

import pytest

from leibniz.backends import coq_docker
from leibniz.backends.coq_docker import CoqDockerBackend, CoqResult

_HAVE_COQ = coq_docker.available()


def _out(compile_part: str = "compiled", *, axioms="<none>", tit="<none>", unsafe="<none>", pos="<none>") -> str:
    """Build a combined compile+rocqchk output with a CONTEXT SUMMARY (the shape CoqResult parses)."""
    return (f"{compile_part}\n@@ROCQCHK@@\nModules were successfully checked\n\nCONTEXT SUMMARY\n"
            "===============\n"
            f"* Axioms: {axioms}\n"
            f"* Constants/Inductives relying on type-in-type: {tit}\n"
            f"* Constants/Inductives relying on unsafe (co)fixpoints: {unsafe}\n"
            f"* Inductives whose positivity is assumed: {pos}\n")


# --- CI-safe: rocqchk-summary parsing + comment-stripped forbidden scan (no Docker) -------------------
def test_clean_summary_is_kernel_ok():
    r = CoqResult(0, _out(), source="Theorem t : True. Proof. exact I. Qed.")
    assert r.audit_ran and r.opens_axioms is False and r.has_errors is False and r.kernel_ok is True


def test_axiom_in_summary_blocks_kernel_ok():
    # The re-attack's `Definition foo := classic` route: rocqchk names the axiom regardless of decl form.
    r = CoqResult(0, _out(axioms="\n    Stdlib.Logic.Classical_Prop.classic"), source="Definition foo := classic.")
    assert r.opens_axioms is True and r.kernel_ok is False


def test_unsafe_fixpoint_or_typeintype_blocks():
    assert CoqResult(0, _out(tit="\n    Top.bad")).opens_axioms is True
    assert CoqResult(0, _out(unsafe="\n    Top.loop")).opens_axioms is True
    assert CoqResult(0, _out(pos="\n    Top.Bad")).opens_axioms is True


def test_missing_audit_is_fail_closed():
    # No CONTEXT SUMMARY (e.g. compile failed so rocqchk never ran) → unaudited → not clean.
    assert CoqResult(0, "boom\n@@ROCQCHK@@\n", source="x").opens_axioms is True
    assert CoqResult(0, "boom\n@@ROCQCHK@@\n", source="x").kernel_ok is False


def test_compile_error_is_not_kernel_ok():
    assert CoqResult(1, "Error: Unable to unify\n@@ROCQCHK@@\n").has_errors is True
    assert CoqResult(0, "Error: something\n@@ROCQCHK@@\n").has_errors is True


def test_operator_approved_axiom_is_allowed():
    r = CoqResult(0, _out(axioms="\n    Stdlib.Logic.Classical_Prop.classic"),
                  source="Definition foo := classic.",
                  allow_axioms=frozenset({"Stdlib.Logic.Classical_Prop.classic"}))
    assert r.opens_axioms is False


def test_forbidden_keyword_in_comment_is_inert():
    r = CoqResult(0, _out(), source="(* An Admitted proof would be rejected. *)\nTheorem t : True. Proof. exact I. Qed.")
    assert r.uses_forbidden is False and r.kernel_ok is True


def test_real_laundering_keywords_trip_forbidden():
    assert CoqResult(0, _out(), source="Theorem t : True. Proof. Admitted.").uses_forbidden is True
    assert CoqResult(0, _out(), source="Axiom bad : False.").uses_forbidden is True


def test_section_hypothesis_keywords_forbidden():
    # `Variable`/`Context`/`Hypothesis` let the STATED theorem rest on a section hypothesis that rocqchk
    # sees (post-discharge) as a sound implication — so they are blocked lexically.
    for src in ("Variable bad : False.", "Context (bad : False).", "Hypotheses h : False."):
        assert CoqResult(0, _out(), source=src).uses_forbidden is True


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
def test_live_admitted_rejected():
    assert CoqDockerBackend().check_source(_LAUNDERED) is False


@pytest.mark.skipif(not _HAVE_COQ, reason="needs Docker + rocq/rocq-prover image")
def test_live_broken_rejected():
    assert CoqDockerBackend().check_source(_BROKEN) is False


@pytest.mark.skipif(not _HAVE_COQ, reason="needs Docker + rocq/rocq-prover image")
def test_live_axiom_dependence_rejected_any_decl_form():
    # Regression (adversarial review): a `classic` dependence is caught by rocqchk regardless of decl form
    # or whether the cert opted into `Print Assumptions`.
    for src in ("Require Import Classical.\nTheorem em : forall P:Prop, P \\/ ~P.\nProof. intro P. apply classic. Qed.\n",
                "Require Import Coq.Logic.Classical_Prop.\nDefinition foo : forall P:Prop, P \\/ ~P := classic.\n"):
        assert CoqDockerBackend().check_source(src) is False


@pytest.mark.skipif(not _HAVE_COQ, reason="needs Docker + rocq/rocq-prover image")
def test_live_section_hypothesis_evasion_rejected():
    for kw in ("Variable bad : False.", "Context (bad : False)."):
        src = f"Section S. {kw} Theorem t : 1 = 2. Proof. destruct bad. Qed. End S.\n"
        assert CoqDockerBackend().check_source(src) is False

"""ADR 0048 — the Coq/Rocq backend. CI-safe unit tests (result parsing + comment-stripped keyword scan)
always run; the live-kernel gating tests need Docker + the pinned rocq/rocq-prover image and skip cleanly
when it is absent. The backend only REPORTS; it never touches kernel_verified. Tier audit."""
from __future__ import annotations

import os

import pytest

from leibniz.backends import coq_docker
from leibniz.backends.coq_docker import CoqDockerBackend, CoqResult

_HAVE_COQ = coq_docker.available()


# --- CI-safe: result parsing + comment-stripped forbidden scan (no Docker) ----------------------------
def test_closed_proof_is_kernel_ok():
    r = CoqResult(0, "Closed under the global context\n", source="Theorem t : True. Proof. exact I. Qed.")
    assert r.kernel_ok is True and r.opens_axioms is False and r.has_errors is False


def test_open_axioms_block_kernel_ok():
    r = CoqResult(0, "Axioms:\nbogus : nat\n", source="Theorem bogus : nat. Admitted.")
    assert r.opens_axioms is True and r.kernel_ok is False


def test_error_output_is_not_kernel_ok():
    assert CoqResult(1, "Error: Unable to unify", source="Theorem t : False. Qed.").has_errors is True
    assert CoqResult(0, "Error: something", source="x").has_errors is True


def test_forbidden_keyword_in_comment_is_inert():
    # A keyword MENTIONED in a comment must not trip the scan; only real code counts.
    r = CoqResult(0, "Closed under the global context\n",
                  source="(* An Admitted proof would be rejected. *)\nTheorem t : True. Proof. exact I. Qed.")
    assert r.uses_forbidden is False and r.kernel_ok is True


def test_real_admitted_in_code_trips_forbidden():
    assert CoqResult(0, "", source="Theorem t : True. Proof. Admitted.").uses_forbidden is True
    assert CoqResult(0, "", source="Axiom bad : False.").uses_forbidden is True


def test_available_returns_bool_and_never_raises():
    assert isinstance(coq_docker.available("definitely/not-an-image:nope"), bool)


# --- live kernel: genuine gating (needs Docker + image) -----------------------------------------------
_GOOD = ("Theorem add_0_r : forall n : nat, n + 0 = n.\n"
         "Proof. intros n. induction n as [| n IH]. - reflexivity. - simpl. rewrite IH. reflexivity. Qed.\n"
         "Print Assumptions add_0_r.\n")
_LAUNDERED = "Theorem bogus : forall n : nat, n + 0 = n + 1.\nProof. Admitted.\nPrint Assumptions bogus.\n"
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


@pytest.mark.skipif(not (_HAVE_COQ and os.environ.get("LEIBNIZ_RUN_LEAN")),
                    reason="live demo cert check; set LEIBNIZ_RUN_LEAN=1 with Docker up")
def test_live_demo_cert_closed_under_global_context():
    from pathlib import Path
    cert = Path(__file__).resolve().parent.parent / "docs" / "crt" / "coq_demo.v"
    d = CoqDockerBackend().check_source_with_detail(cert.read_text())
    assert d and d["verified"] is True and d["closed_under_global_context"] is True

"""ADR 0048 — the Isabelle/HOL backend. CI-safe unit tests (theory-name extraction, comment/cartouche-
stripped keyword scan, result parsing) always run; the live-kernel gating tests need Docker + the pinned
makarius/isabelle image and skip cleanly when it is absent. Report-only; never touches kernel_verified."""
from __future__ import annotations

import os

import pytest

from leibniz.backends import isabelle_docker
from leibniz.backends.isabelle_docker import IsabelleDockerBackend, IsabelleResult, _strip, _THEORY_NAME_RE

_HAVE_ISA = isabelle_docker.available()


# --- CI-safe: name extraction + comment/cartouche-stripped scan + result parsing (no Docker) ----------
def test_theory_name_ignores_word_in_comment():
    # "one-theory" inside a comment must NOT be mistaken for the `theory NAME` declaration.
    src = "(* built as a one-theory session *)\ntheory Isabelle_Demo\n  imports Main\nbegin\nend\n"
    m = _THEORY_NAME_RE.search(_strip(src))
    assert m is not None and m.group(1) == "Isabelle_Demo"


def test_sorry_in_comment_or_cartouche_is_inert():
    src = ('(* build hard-errors on sorry *)\ntheory T imports Main begin\n'
           'text \\<open>we never use sorry here\\<close>\nlemma x: "True" by simp\nend\n')
    assert IsabelleResult(0, "", source=src).uses_forbidden is False


def test_real_sorry_or_oops_trips_forbidden():
    assert IsabelleResult(0, "", source='lemma x: "P" sorry').uses_forbidden is True
    assert IsabelleResult(0, "", source='lemma x: "P" oops').uses_forbidden is True
    assert IsabelleResult(0, "", source="axiomatization where bad: False").uses_forbidden is True


def test_ml_and_oracle_escape_hatches_forbidden():
    # Regression (adversarial review, CRITICAL): the ML/oracle surface must be forbidden — `sorry` desugars
    # to Skip_Proof.cheat_tac, reachable via the `tactic` method / `ML*` / `oracle`, which closes any goal.
    for src in ('lemma x: "P" by (tactic \\<open>Skip_Proof.cheat_tac\\<close>)',
                'ML \\<open>Thm.assume\\<close>', "oracle bad = ...", 'lemma x: "P" by (ML_prf \\<open>x\\<close>)'):
        assert IsabelleResult(0, "", source=src).uses_forbidden is True


def test_proof_cartouche_is_scanned_but_doc_cartouche_is_stripped():
    # A cheat hidden in a PROOF cartouche is still caught; the SAME words inside a doc `text` cartouche are
    # inert prose and must not false-positive.
    proof = 'lemma bad: "(2::nat)+2=5" by (tactic \\<open>Skip_Proof.cheat_tac \\<^context> 1\\<close>)'
    doc = 'text \\<open>we discuss the tactic method and ML here\\<close>\nlemma ok: "True" by simp'
    assert IsabelleResult(0, "", source=proof).uses_forbidden is True
    assert IsabelleResult(0, "", source=doc).uses_forbidden is False


def test_build_error_marker_and_returncode():
    assert IsabelleResult(1, "*** Failed to finish proof", source="x").has_errors is True
    assert IsabelleResult(0, "Finished T", source='lemma x: "True" by simp').kernel_ok is True


def test_available_returns_bool_and_never_raises():
    assert isinstance(isabelle_docker.available("definitely/not-an-image:nope"), bool)


# --- live kernel: genuine gating (needs Docker + image) -----------------------------------------------
_GOOD = 'theory Good imports Main begin\nlemma add_0_r: "n + (0::nat) = n" by simp\nend\n'
_LAUNDERED = 'theory Bad imports Main begin\nlemma bogus: "n + (0::nat) = n + 1" sorry\nend\n'
_BROKEN = 'theory Wrong imports Main begin\nlemma wrong: "n = n + (1::nat)" by simp\nend\n'


@pytest.mark.skipif(not _HAVE_ISA, reason="needs Docker + makarius/isabelle image")
def test_live_valid_proof_verified():
    assert IsabelleDockerBackend().check_source(_GOOD) is True


@pytest.mark.skipif(not _HAVE_ISA, reason="needs Docker + makarius/isabelle image")
def test_live_sorry_rejected():
    assert IsabelleDockerBackend().check_source(_LAUNDERED) is False


@pytest.mark.skipif(not _HAVE_ISA, reason="needs Docker + makarius/isabelle image")
def test_live_broken_rejected():
    assert IsabelleDockerBackend().check_source(_BROKEN) is False


@pytest.mark.skipif(not _HAVE_ISA, reason="needs Docker + makarius/isabelle image")
def test_live_ml_cheat_tac_escape_rejected():
    # Regression (adversarial review, CRITICAL): the ML cheat tactic proving 2+2=5 must FAIL (it builds
    # exit-0 with no error marker, so only the forbidden-token scan catches it).
    src = ('theory Scratch imports Main begin\nlemma bad: "(2::nat) + 2 = 5"\n'
           '  by (tactic \\<open>Skip_Proof.cheat_tac \\<^context> 1\\<close>)\nend\n')
    assert IsabelleDockerBackend().check_source(src) is False


@pytest.mark.skipif(not (_HAVE_ISA and os.environ.get("LEIBNIZ_RUN_LEAN")),
                    reason="live demo cert check; set LEIBNIZ_RUN_LEAN=1 with Docker up")
def test_live_demo_cert_builds():
    from pathlib import Path
    cert = Path(__file__).resolve().parent.parent / "docs" / "crt" / "isabelle_demo.thy"
    assert IsabelleDockerBackend().check_source(cert.read_text()) is True

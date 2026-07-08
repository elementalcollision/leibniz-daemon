"""ADR 0050 Phase 4 / ADR 0063 — the origination path (fail-closed novelty attestation).

An originated law MUST pass the full mechanical novelty gate; `attest_novelty` returns None otherwise.
CI-safe tests drive the REAL `NoveltyGate` with a fake Lean (configurable `is_trivial`) + a fake or the
REAL corpus. Per the Phase-4 decision, NO law is written — this only exercises the machinery. An opt-in
`LEIBNIZ_LEAN_E2E` anchor confirms the real `is_trivial` ladder does not falsely close a novel candidate.
"""
from __future__ import annotations

import os

import pytest

from leibniz.calculemus_site import law_payload
from leibniz.corpus import CorpusBackend
from leibniz.gates.novelty import NoveltyGate
from leibniz.origination import attest_novelty, claim_signature
from leibniz.propositio import Demonstratio, Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimType


class FakeLean:
    def __init__(self, trivial=False):
        self._t = trivial

    def is_trivial(self, expressio):
        return self._t


class FakeCorpus:
    def __init__(self, equivalent=False, structural=False):
        self._eq, self._s = equivalent, structural

    def contains_equivalent(self, sig):
        return self._eq

    def nearest(self, sig):
        return [("neighbor", 0.4)]

    def structural_known(self, cp):
        return "match" if self._s else None


def mkprop(cp="(a*a + b*b) % 4 != 3"):
    en = Enuntiatio(statement="s", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain="a >= 0 and b >= 0", claim_property=cp)
    ex = Expressio(theorem_src="theorem cand : True")
    prop = Propositio(enuntiatio=en, expressio=ex,
                      demonstratio=Demonstratio(proof_obligation="cand", proof_src="by decide"))
    prop.signature = claim_signature("theorem cand : True", ClaimType.INVARIANT, "cand", "novel")
    return prop


def _gate(lean, corpus):
    return NoveltyGate(corpus=corpus, lean=lean)


# --- fail-closed: every gate rejection ⇒ not originatable -----------------------------------------

def test_attest_passes_a_genuinely_novel_claim():
    att = attest_novelty(mkprop(), _gate(FakeLean(trivial=False), FakeCorpus()))
    assert att is not None
    assert att["verdict"] == "novel" and att["producer"] == "NoveltyGate"
    assert "absolute" in att["caveat"].lower()          # the honesty caveat is carried in the attestation


def test_fail_closed_on_trivial():
    assert attest_novelty(mkprop(), _gate(FakeLean(trivial=True), FakeCorpus())) is None


def test_fail_closed_on_known_hash():
    assert attest_novelty(mkprop(), _gate(FakeLean(), FakeCorpus(equivalent=True))) is None


def test_fail_closed_on_structural_known():
    assert attest_novelty(mkprop(), _gate(FakeLean(), FakeCorpus(structural=True))) is None


def test_fail_closed_on_coefficient_degenerate():
    # ADR 0061 check inside the gate: a variable-independent modular claim is never originatable
    assert attest_novelty(mkprop("(2*a*b) % 2 == 0"), _gate(FakeLean(), FakeCorpus())) is None


# --- against the REAL corpus (no Docker: is_trivial faked False) -----------------------------------

def test_real_corpus_refuses_a_known_congruence_but_passes_a_novel_one():
    gate = _gate(FakeLean(trivial=False), CorpusBackend.from_json())
    # `(a^7 - a) % 42` is a curated known (structural_known: pow7_minus_self_div_42) → refused
    assert attest_novelty(mkprop("(a**7 - a) % 42 == 0"), gate) is None
    # a fresh binomial-power congruence not in the corpus → passes the mechanical gate
    assert attest_novelty(mkprop("((a + b)**5 - a**5 - b**5) % 30 == 0"), gate) is not None


# --- payload shape ---------------------------------------------------------------------------------

def test_originated_payload_carries_attestation_and_no_citation():
    att = attest_novelty(mkprop(), _gate(FakeLean(), FakeCorpus()))
    payload = law_payload(mkprop(), origination="originated", references=[], novelty_attestation=att)
    assert payload["origination"] == "originated"
    assert payload["references"] == []
    assert payload["novelty_attestation"]["verdict"] == "novel"


def test_amplified_payload_has_no_attestation():
    payload = law_payload(mkprop(), origination="amplified", references=[{"citation": "X"}])
    assert payload["novelty_attestation"] is None and payload["references"]


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_is_trivial_does_not_close_the_novel_candidate():  # pragma: no cover
    # the real tactic ladder must NOT close the candidate over unbounded ℤ (else it would be trivial,
    # not novel). Confirms the candidate genuinely survives the full real gate. No law is written.
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean image unavailable")
    be = LeanReplBackend(timeout_s=120)
    try:
        expr = Expressio(theorem_src="theorem cand (a b : Int) : ((a + b)^5 - a^5 - b^5) % 30 = 0",
                         imports=("Mathlib.Tactic",))
        assert be.closed_by_decision_procedure(expr) is False
    finally:
        be.close()

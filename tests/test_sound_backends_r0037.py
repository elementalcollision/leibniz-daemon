"""ADR 0037 — guard the SoundFaithfulnessBackend dispatch (the new path is unguarded
by test_invariants.py, which covers the proved path; these tests guard THIS path).

The non-negotiables, each pinned below:
  * a PASS is accepted ONLY when the GATE's own independent re-checker for the
    certificate kind exists AND returns True -- the backend's self-reported
    `rechecked` flag is advisory, never sufficient (no laundering);
  * a PASS without a certificate, or of a kind with no registered re-checker, or
    whose re-check fails, is downgraded to fall-through (DEFER), never a pass;
  * DEFER never becomes PASS;
  * a backend FAIL is a sound refutation -> quarantine UNFAITHFUL;
  * the gaming-witness spine still runs FIRST (a witness kills even a would-PASS backend);
  * backends run cheapest-first and a sound PASS short-circuits;
  * a sound-backend PASS is MECHANICAL and survives TrustPolicy.validate_path.

Stdlib-only (no z3/Lean) so it runs in the universal `invariants` CI job too.
"""
from __future__ import annotations

from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.gates.sound_backends import Certificate, FaithfulnessVerdict
from leibniz.gates.verification import VerificationGate
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.trust import NOVELTY_EDGE, PROOF_EDGE, TrustPolicy
from leibniz.types import ClaimType, EdgeEvidence, FinishReason, TrustTier, Verdict


# --- fixtures ---------------------------------------------------------------

class _NoWitnessBackend:
    def find_gaming_witness(self, statement, negated_claim, bound):
        return None


class _WitnessBackend:
    def find_gaming_witness(self, statement, negated_claim, bound):
        return {"n": 7}  # the spine finds a gaming witness


class _SMT:
    def __init__(self, backend):
        self.backend = backend


class _AlwaysJudge:
    def round_trip_agrees(self, prop):  # would rubber-stamp; must never be reached here
        return 1.0


# a gate-owned re-checker for kind "fake"; toggled to test the authoritative re-check
def _ok_recheck(cert):
    return True


def _bad_recheck(cert):
    return False


def _gate(sound_backends=(), witness=False, recheckers=None) -> FaithfulnessGate:
    smt = _SMT(_WitnessBackend() if witness else _NoWitnessBackend())
    return FaithfulnessGate(
        smt=smt, probes={}, judge=_AlwaysJudge(),
        sound_backends=sound_backends,
        recheckers=recheckers if recheckers is not None else {"fake": _ok_recheck},
    )


def _prop(claim_type=ClaimType.COMPLEXITY_BOUND) -> Propositio:
    en = Enuntiatio(
        statement="s", claim_type=claim_type,
        falsifiable_claim="exists counterexample",
    )
    return Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem t : P"))


class _Backend:
    """A fake SoundFaithfulnessBackend with controllable verdict/cert."""

    def __init__(self, name, cost_rank, verdict, *, rechecked=None, kind="fake", applies=True,
                 producer=None):
        self.name = name
        self.cost_rank = cost_rank
        self._verdict = verdict
        self._rechecked = rechecked
        self._kind = kind
        self._applies = applies
        self._producer = producer or f"fake/{name}"   # ADR 0041: validate_path now allowlists producers
        self.checked = False

    def applies(self, prop):
        return self._applies

    def check(self, prop):
        self.checked = True
        cert = None
        if self._rechecked is not None:
            cert = Certificate(kind=self._kind, rechecked=self._rechecked, data="c")
        return FaithfulnessVerdict(
            verdict=self._verdict, producer=self._producer, certificate=cert,
        )


# --- the soundness guards (the ones that matter most) -----------------------

def test_sound_pass_requires_gate_recheck_and_is_mechanical():
    b = _Backend("b", 1, Verdict.PASS, rechecked=True)
    ev = _gate((b,)).check(_prop())            # gate has the "fake" re-checker
    assert ev.verdict is Verdict.PASS
    assert ev.tier is TrustTier.MECHANICAL     # never JUDGED
    assert ev.detail["backend"] == "b"
    assert ev.detail["certificate_kind"] == "fake"
    assert ev.detail["rechecked_by_gate"] is True
    assert ev.producer == "fake/b"


def test_pass_with_no_registered_rechecker_is_not_a_pass():
    # The backend self-reports rechecked=True, but the GATE has no re-checker for
    # this kind -> not a pass. (The dormant default: no re-checker => no PASS.)
    b = _Backend("b", 1, Verdict.PASS, rechecked=True, kind="walnut-automaton")
    ev = _gate((b,), recheckers={}).check(_prop())
    assert ev.verdict is Verdict.DEFER


def test_pass_with_failing_gate_recheck_is_not_a_pass():
    # The gate's own re-check vetoes a self-reported PASS.
    b = _Backend("b", 1, Verdict.PASS, rechecked=True)
    ev = _gate((b,), recheckers={"fake": _bad_recheck}).check(_prop())
    assert ev.verdict is Verdict.DEFER


def test_pass_without_rechecked_flag_is_not_a_pass():
    b = _Backend("b", 1, Verdict.PASS, rechecked=False)  # backend itself didn't re-check
    ev = _gate((b,)).check(_prop())
    assert ev.verdict is Verdict.DEFER


def test_pass_with_no_certificate_is_not_a_pass():
    b = _Backend("b", 1, Verdict.PASS, rechecked=None)  # cert=None
    ev = _gate((b,)).check(_prop())
    assert ev.verdict is Verdict.DEFER


# --- FAIL / DEFER / routing -------------------------------------------------

def test_backend_fail_quarantines_unfaithful():
    b = _Backend("b", 1, Verdict.FAIL)
    prop = _prop()
    ev = _gate((b,)).check(prop)
    assert ev.verdict is Verdict.FAIL
    assert ev.tier is TrustTier.MECHANICAL
    assert prop.finish_reason is FinishReason.UNFAITHFUL


def test_defer_backend_falls_through():
    b = _Backend("b", 1, Verdict.DEFER)
    ev = _gate((b,)).check(_prop())
    assert ev.verdict is Verdict.DEFER  # measurable claim, no probe -> DEFER


def test_non_applicable_backend_is_skipped():
    b = _Backend("b", 1, Verdict.PASS, rechecked=True, applies=False)
    ev = _gate((b,)).check(_prop())
    assert b.checked is False
    assert ev.verdict is Verdict.DEFER


# --- ordering: spine first, then cheapest-first, short-circuit ---------------

def test_gaming_spine_runs_before_sound_backends():
    b = _Backend("b", 1, Verdict.PASS, rechecked=True)
    prop = _prop()
    ev = _gate((b,), witness=True).check(prop)
    assert ev.verdict is Verdict.FAIL
    assert prop.finish_reason is FinishReason.GAMED
    assert b.checked is False  # never reached


def test_cheapest_first_and_short_circuit_on_sound_pass():
    cheap = _Backend("cheap", 1, Verdict.PASS, rechecked=True)
    expensive = _Backend("expensive", 9, Verdict.FAIL)
    ev = _gate((expensive, cheap)).check(_prop())  # registered out of order
    assert ev.verdict is Verdict.PASS
    assert ev.detail["backend"] == "cheap"
    assert expensive.checked is False  # short-circuited before the expensive one


def test_defer_then_pass_runs_both():
    first = _Backend("first", 1, Verdict.DEFER)
    second = _Backend("second", 2, Verdict.PASS, rechecked=True)
    ev = _gate((first, second)).check(_prop())
    assert first.checked is True and second.checked is True
    assert ev.verdict is Verdict.PASS
    assert ev.detail["backend"] == "second"


def test_no_backends_is_unchanged_behavior():
    ev = _gate(()).check(_prop())
    assert ev.verdict is Verdict.DEFER


# --- end-to-end: a sound-backend PASS promotes through the trust policy ------

def test_sound_backend_pass_survives_validate_path():
    # ADR 0041: a MECHANICAL faithfulness edge must name an operator-admitted producer
    # (FAITHFULNESS_PRODUCERS). A real sound backend uses an admitted producer; the fake here borrows
    # "walnut/recheck" to model that. A non-admitted producer is rejected (see test_tool_trust.py).
    b = _Backend("b", 1, Verdict.PASS, rechecked=True, producer="walnut/recheck")
    prop = _prop()
    prop.record(EdgeEvidence(NOVELTY_EDGE, TrustTier.MECHANICAL, Verdict.PASS))
    prop.record(_gate((b,)).check(prop))                      # the MECHANICAL faithfulness PASS
    prop.record(EdgeEvidence(PROOF_EDGE, TrustTier.MECHANICAL, Verdict.PASS))
    gate = VerificationGate(TrustPolicy())
    assert gate.is_promotable(prop) is True

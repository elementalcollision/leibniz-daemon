"""ADR 0038 — guard the Walnut-decided Observatory tier (a SEPARATE, non-Q.E.D. ledger).

The non-negotiables, each pinned below:
  * a Walnut DECISION never enters the kernel Q.E.D. Codex: a WALNUT_DECIDED record is NOT
    promotable (it lacks the PROOF/FAITHFULNESS/NOVELTY edges), never `promulgated`, never has
    a `Demonstratio`/Q.E.D.;
  * DECIDED requires the gate's own independent re-check (a universal automaton); a fabricated
    bare "true" / non-universal / indeterminate / missing-binary / numeration-mismatch all
    quarantine, never decide;
  * a refuted automaton => REFUTED.

Stdlib-only (Walnut binary never invoked — the runner is injected).
"""
from __future__ import annotations

from leibniz.gates.verification import VerificationGate
from leibniz.observatory import WALNUT_DECISION_EDGE, WalnutObservatory, is_walnut_decided
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.trust import TrustPolicy
from leibniz.types import ClaimType, FinishReason

# real-serializer-format automata (see test_walnut_backend_r0037)
_UNIVERSAL = "msd_2\n\n0 1\n0 -> 0\n1 -> 0\n"
_NON_UNIVERSAL = "msd_2\n\n0 1\n0 -> 0\n1 -> 1\n\n1 0\n0 -> 1\n1 -> 1\n"
_PARTIAL = "msd_2\n\n0 1\n0 -> 0\n"  # incomplete -> indeterminate


def _claim(pred="claim(n)", num="msd_2"):
    en = Enuntiatio(statement="Thue-Morse is overlap-free", claim_type=ClaimType.INVARIANT,
                    falsifiable_claim="exists a counterexample n")
    ex = Expressio(theorem_src="theorem t : P", walnut_predicate=pred, walnut_numeration=num)
    return Propositio(enuntiatio=en, expressio=ex)


def _decide(automaton_text, **claim_kw):
    obs = WalnutObservatory(runner=lambda *a, **k: automaton_text)
    return obs.decide(_claim(**claim_kw))


# --- the headline guard: a DECIDED record can never reach the Q.E.D. Codex ---

def test_decided_record_is_not_promotable_and_not_qed():
    prop = _decide(_UNIVERSAL)
    assert prop.finish_reason is FinishReason.WALNUT_DECIDED
    assert is_walnut_decided(prop) is True
    # the tier never touches the kernel path:
    assert prop.promulgated is False
    assert prop.demonstratio is None                 # no proof => no kernel_verified / Q.E.D.
    # and the kernel gate refuses to promote it (no PROOF/FAITHFULNESS/NOVELTY edges):
    gate = VerificationGate(TrustPolicy())
    assert gate.is_promotable(prop) is False
    # the certificate is recorded as PROVENANCE, not a promotion edge:
    edges = [e.edge for e in prop.edges]
    assert WALNUT_DECISION_EDGE in edges


# --- decision outcomes ------------------------------------------------------

def test_refuted_automaton_is_refuted():
    prop = _decide(_NON_UNIVERSAL)
    assert prop.finish_reason is FinishReason.REFUTED
    assert is_walnut_decided(prop) is False


def test_indeterminate_is_unproven_not_decided():
    prop = _decide(_PARTIAL)
    assert prop.finish_reason is FinishReason.UNPROVEN
    assert is_walnut_decided(prop) is False


def test_missing_binary_is_unproven():
    obs = WalnutObservatory(runner=lambda *a, **k: None)
    prop = obs.decide(_claim())
    assert prop.finish_reason is FinishReason.UNPROVEN


def test_numeration_mismatch_is_unproven():
    # universal automaton over msd_3 but the claim asked for msd_2
    prop = _decide("msd_3\n\n0 1\n0 -> 0\n1 -> 0\n2 -> 0\n", num="msd_2")
    assert prop.finish_reason is FinishReason.UNPROVEN


def test_missing_walnut_predicate_is_malformed():
    en = Enuntiatio(statement="s", claim_type=ClaimType.INVARIANT, falsifiable_claim="c")
    prop = Propositio(enuntiatio=en, expressio=Expressio(theorem_src="theorem t : P"))
    assert WalnutObservatory(runner=lambda *a, **k: _UNIVERSAL).decide(prop).finish_reason \
        is FinishReason.MALFORMED


# --- laundering: a fabricated bare "true" must not be DECIDED ----------------

def test_fabricated_bare_true_is_not_decided():
    # a bare token has no universal automaton -> recheck fails -> not decided.
    prop = _decide("true")
    assert prop.finish_reason is not FinishReason.WALNUT_DECIDED
    assert is_walnut_decided(prop) is False


# --- defense-in-depth (from the tier soundness review) ----------------------

def test_provenance_edge_is_disjoint_from_promotion_edges():
    # pin the namespace separation: a future rename that collides with a promotion edge
    # (and would silently count toward is_promotable) must fail CI here.
    from leibniz.trust import FAITHFULNESS_EDGE, NOVELTY_EDGE, PROOF_EDGE
    assert WALNUT_DECISION_EDGE not in {PROOF_EDGE, FAITHFULNESS_EDGE, NOVELTY_EDGE}


def test_decide_never_refiles_a_proved_prop():
    # a prop that already carries a kernel proof is left untouched (no WALNUT_DECIDED over it).
    from leibniz.propositio import Demonstratio
    prop = _claim()
    prop.demonstratio = Demonstratio(proof_obligation="x", proof_src="by decide")
    out = WalnutObservatory(runner=lambda *a, **k: _UNIVERSAL).decide(prop)
    assert out.finish_reason is not FinishReason.WALNUT_DECIDED
    assert is_walnut_decided(out) is False

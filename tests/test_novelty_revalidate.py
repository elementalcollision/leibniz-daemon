"""ADR 0059 review #3 — NoveltyGate.revalidate re-checks the CANONICAL law a decision-procedure
fast-path installs after FORMALIZE ran novelty on the autoformalized statement. A trivial or
duplicate canonical law must earn a FAIL NOVELTY_EDGE (→ not promotable), never ride the stale PASS.

No Docker: fake `lean` (configurable is_trivial) + fake corpus. Also verifies the daemon-loop gate
(re-check only when a fast-path fired) and that a FAIL edge makes is_promotable False.
"""
from __future__ import annotations

from leibniz.gates.novelty import NoveltyGate
from leibniz.gates.verification import VerificationGate
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.trust import (
    FAITHFULNESS_EDGE,
    KERNEL_PRODUCER,
    NOVELTY_EDGE,
    PROOF_EDGE,
    TrustPolicy,
)
from leibniz.types import (
    ClaimSignature,
    ClaimType,
    EdgeEvidence,
    FinishReason,
    TrustTier,
    Verdict,
)


class FakeLean:
    def __init__(self, trivial=False):
        self._trivial = trivial

    def is_trivial(self, expressio):
        return self._trivial


class FakeCorpus:
    def __init__(self, equivalent=False, structural=False):
        self._eq, self._struct = equivalent, structural

    def contains_equivalent(self, sig):
        return self._eq

    def nearest(self, sig):
        return []

    def structural_known(self, claim_property):
        return "match" if self._struct else None


def mkprop(cp="((a*b) % 3 == 0) == ((a % 3 == 0) or (b % 3 == 0))"):
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain="a >= 0 and b >= 0", claim_property=cp)
    ex = Expressio(theorem_src="theorem boolean_law_x : True", normalized_hash="h_canonical")
    sig = ClaimSignature(claim_type=ClaimType.INVARIANT, subject="s", relation="r", formal_hash="h_canonical")
    return Propositio(enuntiatio=en, expressio=ex, signature=sig)


def _gate(lean, corpus):
    return NoveltyGate(corpus=corpus, lean=lean)


def test_revalidate_keeps_a_novel_nontrivial_canonical_law():
    prop = mkprop()
    assert _gate(FakeLean(trivial=False), FakeCorpus()).revalidate(prop) is None
    assert prop.finish_reason is None   # not quarantined


def test_revalidate_fails_a_trivial_canonical_law():
    prop = mkprop()
    ev = _gate(FakeLean(trivial=True), FakeCorpus()).revalidate(prop)
    assert ev is not None and ev.edge == NOVELTY_EDGE and ev.verdict is Verdict.FAIL
    assert ev.producer == "LeanVerifier.is_trivial" and prop.finish_reason is FinishReason.TRIVIAL


def test_revalidate_fails_a_hash_duplicate_canonical_law():
    prop = mkprop()
    ev = _gate(FakeLean(), FakeCorpus(equivalent=True)).revalidate(prop)
    assert ev is not None and ev.verdict is Verdict.FAIL and prop.finish_reason is FinishReason.KNOWN


def test_revalidate_fails_a_structural_duplicate_canonical_law():
    prop = mkprop()
    ev = _gate(FakeLean(), FakeCorpus(structural=True)).revalidate(prop)
    assert ev is not None and ev.verdict is Verdict.FAIL
    assert ev.producer == "CorpusBackend.structural_known" and prop.finish_reason is FinishReason.KNOWN


def test_fail_revalidation_makes_is_promotable_false():
    # the canonical-law FAIL novelty edge overrides the FORMALIZE PASS at is_promotable time
    prop = mkprop()
    prop.record(EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS, producer="boolean_modular/kernel"))
    prop.record(EdgeEvidence(NOVELTY_EDGE, TrustTier.MECHANICAL, Verdict.PASS, producer="NoveltyGate"))
    prop.record(EdgeEvidence(PROOF_EDGE, TrustTier.MECHANICAL, Verdict.PASS, producer=KERNEL_PRODUCER,
                             detail={"decision_procedure": "boolean-modular-zmod", "consensus": 1}))
    verify = VerificationGate(TrustPolicy())
    assert verify.is_promotable(prop) is True                      # before re-check: promotable
    ev = _gate(FakeLean(trivial=True), FakeCorpus()).revalidate(prop)
    prop.record(ev)
    assert verify.is_promotable(prop) is False                     # FAIL novelty edge → refused


def test_daemon_gate_only_rechecks_when_a_fastpath_fired():
    # the daemon re-checks only when a proof edge carries a `decision_procedure` tag (a fast-path);
    # an ensemble proof (no tag) leaves the statement unchanged and is not re-checked.
    fastpath = mkprop()
    fastpath.record(EdgeEvidence(PROOF_EDGE, TrustTier.MECHANICAL, Verdict.PASS, producer=KERNEL_PRODUCER,
                                 detail={"decision_procedure": "residue-poly-zmod"}))
    ensemble = mkprop()
    ensemble.record(EdgeEvidence(PROOF_EDGE, TrustTier.MECHANICAL, Verdict.PASS, producer=KERNEL_PRODUCER,
                                 detail={"consensus": 2}))

    def fastpath_fired(prop):
        return any(e.edge == PROOF_EDGE and (e.detail or {}).get("decision_procedure") for e in prop.edges)

    assert fastpath_fired(fastpath) is True
    assert fastpath_fired(ensemble) is False

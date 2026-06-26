"""ADR 0038 — conjecturer-side automatic-sequence generation (proposal side).

Proves the generator parses proposals into Walnut-tier claims and routes them to the
Observatory decider, and that nothing it produces can become Q.E.D. (it only ever reaches
the non-Q.E.D. tier). Stdlib-only: provider + Walnut runner are both injected fakes.
"""
from __future__ import annotations

import json

from leibniz.observatory import WalnutObservatory, is_walnut_decided
from leibniz.types import FinishReason, Role
from leibniz.walnut_conjecture import WalnutConjecturer, parse_walnut_claim

_UNIVERSAL = "msd_2\n\n0 1\n0 -> 0\n1 -> 0\n"

_GOOD_DRAFT = json.dumps({
    "statement": "Thue-Morse is overlap-free",
    "walnut_predicate": "A i, p (p >= 1) => E t (t < 3*p) & T[i+t] != T[i+t+p]",
    "walnut_numeration": "msd_2",
    "falsifiable_claim": "exists an overlap in Thue-Morse",
})


class _FakeProvider:
    def __init__(self, draft, role_seen=None):
        self._draft = draft
        self.role_seen = role_seen

    def propose(self, role, context):
        self.role_seen = role
        return self._draft


class _RaisingProvider:
    def propose(self, role, context):
        raise RuntimeError("provider down")


# --- parsing ----------------------------------------------------------------

def test_parse_good_draft():
    prop = parse_walnut_claim(_GOOD_DRAFT)
    assert prop is not None
    assert prop.expressio.walnut_predicate.startswith("A i, p")
    assert prop.expressio.walnut_numeration == "msd_2"
    assert prop.enuntiatio.statement == "Thue-Morse is overlap-free"
    assert prop.seed_origin == "walnut"


def test_parse_missing_fields_returns_none():
    assert parse_walnut_claim(json.dumps({"statement": "x"})) is None          # no predicate/num
    assert parse_walnut_claim(json.dumps({"walnut_predicate": "p", "walnut_numeration": "msd_2"})) is None  # no statement
    assert parse_walnut_claim("not json at all") is None


# --- generation -------------------------------------------------------------

def test_generate_uses_conjecture_role():
    prov = _FakeProvider(_GOOD_DRAFT)
    prop = WalnutConjecturer(provider=prov).generate()
    assert prov.role_seen is Role.CONJECTURE
    assert prop is not None and prop.expressio.walnut_numeration == "msd_2"


def test_generate_robust_to_provider_failure():
    assert WalnutConjecturer(provider=_RaisingProvider()).generate() is None


def test_generate_robust_to_garbage_draft():
    assert WalnutConjecturer(provider=_FakeProvider("```garbage```")).generate() is None


# --- end-to-end: generate -> decide -> non-Q.E.D. tier ----------------------

def test_generate_and_decide_files_in_walnut_tier():
    conj = WalnutConjecturer(
        provider=_FakeProvider(_GOOD_DRAFT),
        observatory=WalnutObservatory(runner=lambda *a, **k: _UNIVERSAL),
    )
    prop = conj.generate_and_decide()
    assert prop is not None
    assert prop.finish_reason is FinishReason.WALNUT_DECIDED
    assert is_walnut_decided(prop) is True
    # never Q.E.D.: no proof, not promulgated
    assert prop.promulgated is False
    assert prop.demonstratio is None


def test_generate_and_decide_none_when_proposal_unusable():
    conj = WalnutConjecturer(provider=_FakeProvider("garbage"))
    assert conj.generate_and_decide() is None

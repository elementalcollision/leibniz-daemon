"""Run-2 follow-up — anti-collapse conjecturer diversity (proposal-side only).

The run-2 live result was 20/20 IDENTICAL claims ("RS is 4th-power-free") because each
generate() saw only a static seed with no memory. These pin the fix:
  * each call's context carries a ROTATING (sequence, family) breadth steer;
  * after the first proposal, the context carries the session AVOID-LIST (prior statements +
    their decision outcomes), so the model is told not to repeat — and which were refuted;
  * none of this touches the trust boundary (it is pure proposal-side context engineering).

Stdlib-only; provider + Walnut runner injected.
"""
from __future__ import annotations

import json

from leibniz.observatory import WalnutObservatory
from leibniz.walnut_conjecture import (
    WALNUT_FAMILIES,
    WALNUT_WORDS,
    WalnutConjecturer,
    _rotation_target,
)

_UNIVERSAL = "msd_2\n\n0 1\n0 -> 0\n1 -> 0\n"
_NON_UNIVERSAL = "msd_2\n\n0 1\n0 -> 0\n1 -> 1\n\n1 0\n0 -> 1\n1 -> 1\n"  # => refuted


def _draft(stmt, word="T"):
    # word=T, cube-free (exponent 3) is a TRUE property => the decided-true path PASSES the lint,
    # so decide() yields WALNUT_DECIDED (these diversity tests are not about the lint catch).
    return json.dumps({"statement": stmt, "walnut_predicate": f"A n ({word}[n]=@0)",
                       "walnut_numeration": "msd_2",
                       "property_descriptor": {"family": "power_free", "word": word, "exponent": 3}})


class _RecordingProvider:
    """Returns successive drafts and records every context string it was handed."""

    def __init__(self, drafts):
        self._drafts = list(drafts)
        self.contexts: list[str] = []
        self._i = 0

    def propose(self, role, context):
        self.contexts.append(context)
        d = self._drafts[min(self._i, len(self._drafts) - 1)]
        self._i += 1
        return d


# --- rotation ---------------------------------------------------------------

def test_rotation_varies_word_then_family():
    # word cycles fastest; the first len(WALNUT_WORDS) targets hit every word exactly once.
    words_seen = [
        next(w for w in WALNUT_WORDS if w in _rotation_target(i))
        for i in range(len(WALNUT_WORDS))
    ]
    assert set(words_seen) == set(WALNUT_WORDS)
    # the family advances after a full word cycle
    assert WALNUT_FAMILIES[0] in _rotation_target(0)
    assert WALNUT_FAMILIES[1] in _rotation_target(len(WALNUT_WORDS))


# --- session memory / avoid-list -------------------------------------------

def test_context_carries_rotating_target_and_grows_avoid_list():
    prov = _RecordingProvider([_draft("claim A"), _draft("claim B"), _draft("claim C")])
    conj = WalnutConjecturer(provider=prov)
    for _ in range(3):
        conj.generate()
    c0, c1, c2 = prov.contexts
    # first call: no avoid-list yet
    assert "ALREADY proposed" not in c0
    # later calls: prior statements appear in the avoid-list
    assert "claim A" in c1
    assert "claim A" in c2 and "claim B" in c2
    # rotation steer present every call, and the first two targets differ (breadth)
    assert _rotation_target(0) in c0 and _rotation_target(1) in c1
    assert c0 != c1


def test_outcome_is_threaded_into_next_context():
    # a refuted proposal must show as 'refuted' in the NEXT call's avoid-list (so the model
    # learns the claim was false, not merely that it was already said).
    prov = _RecordingProvider([_draft("false claim"), _draft("next claim")])
    conj = WalnutConjecturer(provider=prov,
                             observatory=WalnutObservatory(runner=lambda *a, **k: _NON_UNIVERSAL))
    conj.generate_and_decide()
    conj.generate_and_decide()
    assert "false claim -> refuted" in prov.contexts[1]


def test_history_records_statement_and_outcome():
    prov = _RecordingProvider([_draft("c1"), _draft("c2")])
    conj = WalnutConjecturer(provider=prov,
                             observatory=WalnutObservatory(runner=lambda *a, **k: _UNIVERSAL))
    conj.generate_and_decide()
    assert conj.history[-1]["statement"] == "c1"
    assert conj.history[-1]["outcome"] == "walnut_decided"
    assert conj.call_index == 1


def test_explicit_context_overrides_dynamic_build():
    # passing context explicitly (e.g. a test/replay) bypasses the rotation/avoid machinery.
    prov = _RecordingProvider([_draft("x")])
    WalnutConjecturer(provider=prov).generate(context="EXACT CONTEXT")
    assert prov.contexts[0] == "EXACT CONTEXT"


def test_provider_failure_still_recorded_in_history():
    class _Boom:
        def propose(self, role, context):
            raise RuntimeError("down")
    conj = WalnutConjecturer(provider=_Boom())
    assert conj.generate() is None
    assert conj.history[-1]["outcome"] == "no_proposal"

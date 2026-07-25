"""ADR 0074 — the gate-loop retry with a mechanically-derived `established_domain`.

CI-safe: no Docker, no Lean, no z3 — fake backends exercise every guard. The load-bearing
property is ROLLBACK: the derived value must be invisible to everything except the backend
that earns a fully re-checked, statement-bound PASS with it. An earlier draft derived the
field in FORMALIZE instead; that mutation survived a DEFER into paths where nothing
re-renders the statement, disarmed the ADR 0004 gaming spine, and let a FALSE claim reach
kernel_verified + Q.E.D. Those failure modes are pinned here as regressions.
"""
from __future__ import annotations

import os

import pytest

from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.gates.sound_backends import Certificate, FaithfulnessVerdict
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimType, Verdict

BOX = "a >= 0 and b >= 0"
CP = "(a^2 + a*b + b^2) % 9 != 6"
KIND = "fake-kind"


class _Z3:
    """decide_unsat: False = conclusively satisfiable, True = unsat/empty, None = unknown."""

    def __init__(self, verdict=False):
        self.verdict, self.calls = verdict, 0

    def decide_unsat(self, preds, bound=0):
        self.calls += 1
        return self.verdict

    def find_gaming_witness(self, *a, **k):
        return None            # the gate's minimal-backend fallback path


class _Smt:
    def __init__(self, backend):
        self.backend = backend

    def find_gaming_witness(self, *a, **k):
        return None


class _Backend:
    """PASSes only when handed the CANONICAL contract — the shape of the real defect."""

    def __init__(self, name="lean-decided", pass_on_canonical=True, raise_on_retry=False):
        self.name, self.cost_rank = name, 90
        self._pass, self._raise_on_retry = pass_on_canonical, raise_on_retry
        self.seen: list = []

    def applies(self, prop):
        return True

    def check(self, prop):
        # NB: raising on the FIRST call is pre-existing gate behaviour (unguarded); what the
        # ADR 0074 retry must survive is a backend that explodes on the RETRY.
        if self._raise_on_retry and self.seen:
            raise RuntimeError("backend exploded on the canonical retry")
        ed = prop.expressio.established_domain
        self.seen.append(ed)
        if self._pass and ed == prop.enuntiatio.claim_domain:
            return FaithfulnessVerdict(
                verdict=Verdict.PASS, producer="lean_decided/kernel",
                certificate=Certificate(kind=KIND, rechecked=True, data={},
                                        detail={"statement": "CANON"}), detail={})
        return FaithfulnessVerdict(verdict=Verdict.DEFER, producer="x/defer", detail={})


def _gate(backend, z3=None, rechecker=True, template="CANON"):
    g = FaithfulnessGate(smt=_Smt(z3 if z3 is not None else _Z3()), probes={},
                         judge=type("J", (), {"round_trip_agrees": lambda self, p: 0.0})())
    g.sound_backends = (backend,)
    if rechecker:
        g.recheckers[KIND] = lambda cert: True
    if template is not None:
        g.templates[KIND] = lambda prop: template
    return g


def _prop(cd=BOX, cp=CP, ed=CP):
    en = Enuntiatio(statement="t", claim_type=ClaimType.INVARIANT, falsifiable_claim="x",
                    claim_domain=cd, claim_property=cp)
    return Propositio(enuntiatio=en,
                      expressio=Expressio(theorem_src="theorem t : True", established_domain=ed))


def test_retry_earns_a_pass_and_commits_the_derived_domain():
    be, p = _Backend(), _prop()
    ev = _gate(be).check(p)
    assert ev.verdict is Verdict.PASS and ev.producer == "lean_decided/kernel"
    assert ev.detail["established_domain_derived"] is True      # provenance for the ledger
    assert p.expressio.established_domain == BOX                # committed only after the PASS
    assert be.seen == [CP, BOX]                                 # defective first, canonical retry


def test_rollback_is_byte_exact_when_the_retry_does_not_pass():
    for be in (_Backend(pass_on_canonical=False), _Backend(raise_on_retry=True)):
        p = _prop()
        ev = _gate(be).check(p)
        assert ev.verdict is not Verdict.PASS
        assert p.expressio.established_domain == CP             # THE load-bearing property


def test_rollback_when_the_certificate_fails_the_gate_recheck_or_binding():
    p = _prop()                                                  # re-checker refuses
    assert _gate(_Backend(), rechecker=False).check(p).verdict is not Verdict.PASS
    assert p.expressio.established_domain == CP
    p2 = _prop()                                                 # statement binding mismatches
    assert _gate(_Backend(), template="OTHER").check(p2).verdict is not Verdict.PASS
    assert p2.expressio.established_domain == CP


def test_only_rerendering_backends_may_retry():
    """`walnut` is a registered sound backend with NO re-rendering prover, so the ADR 0058 A2
    argument does not cover it and the derived contract must never be offered to it."""
    be, p = _Backend(name="walnut"), _prop()
    _gate(be).check(p)
    assert be.seen == [CP]                                      # asked ONCE, never canonically
    assert p.expressio.established_domain == CP


def test_the_gaming_spine_always_sees_the_ORIGINAL_contract():
    """The ADR 0004 spine runs above the loop. An earlier draft derived the field before the
    gate, which made the spine's target `not(D) and D and not(P)` empty by construction."""
    seen: list = []

    class _Spy(_Z3):
        def find_gaming_witness(self, statement, negated_claim, bound=0):
            seen.append(statement)      # the spine is called on smt.BACKEND
            return None
    g = _gate(_Backend(), z3=_Spy())
    p = _prop()
    g.check(p)
    assert seen and CP in seen[0]                               # the honest, narrower ed
    assert BOX not in seen[0]


@pytest.mark.parametrize("verdict", [True, None])
def test_fail_closed_on_empty_or_undecided_claim_domain(verdict):
    # True = claim_domain UNSAT (a derived ed would launder a vacuous PASS); None = unknown.
    be, p = _Backend(), _prop()
    _gate(be, z3=_Z3(verdict)).check(p)
    assert p.expressio.established_domain == CP and be.seen == [CP]


def test_fail_closed_without_a_usable_decide_unsat():
    """A "minimal" backend (the deterministic-fake path) has the spine but no decide_unsat:
    the retry cannot discharge its satisfiability guard, so it must refuse."""

    class _Minimal:
        def find_gaming_witness(self, *a, **k):
            return None
    be, p = _Backend(), _prop()
    g = _gate(be)
    g.smt = _Smt(_Minimal())
    g.check(p)
    assert p.expressio.established_domain == CP
    assert be.seen == [CP]                                       # never asked canonically


def test_no_retry_when_already_canonical_costs_nothing():
    be, z3, p = _Backend(pass_on_canonical=False), _Z3(), _prop(ed=BOX)
    _gate(be, z3=z3).check(p)
    assert be.seen == [BOX] and z3.calls == 0                   # no second check, no Z3 call


def test_non_str_contract_fields_defer_instead_of_raising():
    for bad in ([], 3, {"a": 1}, ""):
        be, p = _Backend(), _prop()
        p.expressio.established_domain = bad
        _gate(be).check(p)                                       # must not raise
        assert p.expressio.established_domain == bad


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_LEAN_E2E"), reason="set LEIBNIZ_LEAN_E2E=1 for the Lean e2e")
def test_real_kernel_certifies_the_tail_and_leaves_the_exploit_untouched(monkeypatch):  # pragma: no cover
    from leibniz.assembly import maybe_register_lean_decided
    from leibniz.backends import lean_repl
    from leibniz.backends.smt_z3 import Z3Backend
    from leibniz.probes import default_probes
    from leibniz.verifiers import SMTVerifier
    monkeypatch.setenv("LEIBNIZ_LEAN_DECIDED", "1")
    if not lean_repl.available():
        pytest.skip("Lean image unavailable")
    smt = SMTVerifier(backend=Z3Backend())
    gate = FaithfulnessGate(smt=smt, probes=default_probes(smt),
                            judge=type("J", (), {"round_trip_agrees": lambda self, p: 0.0})())
    assert maybe_register_lean_decided(gate, lean_repl.REPL_IMAGE)
    for cp in (CP, "(a^2 + b^2) % 4 != 3"):                      # true tail claims certify
        p = _prop(cp=cp, ed=cp)
        ev = gate.check(p)
        assert ev.verdict is Verdict.PASS and ev.producer == "lean_decided/kernel"
        assert ev.detail.get("established_domain_derived") is True
        assert p.expressio.established_domain == BOX
    # The review exploit: an inequality-restricted domain the [0,64] box misrepresents.
    # lean_decided DEFERs on it, so the derived contract must be ROLLED BACK -- this gate
    # behaves exactly as origin/main here (which also passes it via ClaimProbe; that bounded
    # probe weakness is PRE-EXISTING and out of scope for ADR 0074).
    ex = _prop(cd="a % 4 == 1 and a > 60 and b % 4 == 1 and b > 60",
               cp="(a*a + b*b) % 16 == 2", ed="a % 16 == 13 and b % 16 == 13")
    ev = gate.check(ex)
    assert ex.expressio.established_domain == "a % 16 == 13 and b % 16 == 13"   # rolled back
    assert ev.detail.get("established_domain_derived") is not True


def test_no_retry_after_a_pass_whose_certificate_the_gate_REJECTED():
    """The retry is for DEFERs (a contract problem). A backend that claimed a PASS whose
    certificate failed the gate's own re-check is a red flag, not a contract problem — it must
    NOT be handed a canonical contract for a second attempt."""

    class _AlwaysPass(_Backend):
        def check(self, prop):
            self.seen.append(prop.expressio.established_domain)
            return FaithfulnessVerdict(
                verdict=Verdict.PASS, producer="lean_decided/kernel",
                certificate=Certificate(kind=KIND, rechecked=True, data={},
                                        detail={"statement": "CANON"}), detail={})
    be, p = _AlwaysPass(), _prop()
    ev = _gate(be, rechecker=False).check(p)                 # gate re-check refuses
    assert ev.verdict is not Verdict.PASS
    assert be.seen == [CP]                                  # asked ONCE — no second chance
    assert p.expressio.established_domain == CP

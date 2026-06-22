"""ADR 0022: steer the structured faithfulness contract INTO the sound DSL.

Two levers: (1) the CONJECTURE/FORMALIZE prompts carry the DSL grammar; (2) a
bounded, mechanical repair pass in `Formalize` rewrites an un-encodable contract
toward the DSL — but accepts a repair ONLY if it is strictly sound (every field
encodable AND claim_domain still non-empty), so it can never launder a vacuous PASS.
All proposal-side: the honest gate still decides. The control-flow/guard tests run
in CI with a fake backend; the grammar-reality tests are gated on real z3.
"""
from __future__ import annotations

import json

import pytest

from leibniz.backends.smt_z3 import Z3Backend, available
from leibniz.pipeline import Formalize
from leibniz.propositio import Enuntiatio, Expressio, Propositio
from leibniz.providers.anthropic_provider import _DSL, _PROMPTS, AnthropicProvider
from leibniz.types import ClaimType, Role
from leibniz.verifiers import SMTVerifier


# --- the prompts embed the DSL grammar (no z3 / no network) ------------------

def test_conjecture_prompt_embeds_the_dsl_and_contract():
    p = _PROMPTS[Role.CONJECTURE]
    assert _DSL in p
    assert "CONSTANT exponent" in p and "FORBIDDEN" in p
    assert "claim_domain" in p and "claim_property" in p


def test_formalize_prompt_embeds_the_dsl_and_coverage_rule():
    p = _PROMPTS[Role.FORMALIZE]
    assert _DSL in p
    assert "established_domain" in p and "COVER claim_domain" in p


def test_repair_contract_prompt_carries_grammar_claim_and_anti_narrowing():
    prov = AnthropicProvider()
    captured: dict[str, str] = {}
    prov._chat = lambda content: captured.setdefault("c", content) or "{}"  # type: ignore[assignment]
    prov.repair_contract("my human claim", "n >= 1", "n*n >= n", "2^n", ["established_domain"])
    c = captured["c"]
    assert _DSL in c and "my human claim" in c and "established_domain" in c
    assert "NON-EMPTY" in c  # the anti-domain-narrowing instruction


# --- the repair pass: control flow + soundness guards (fake backend, CI-safe) -

def _prop(cd, cp, ed) -> Propositio:
    return Propositio(
        enuntiatio=Enuntiatio(
            statement="claim", claim_type=ClaimType.STRUCTURAL, falsifiable_claim="no",
            claim_domain=cd, claim_property=cp,
        ),
        expressio=Expressio(theorem_src="theorem t : True", established_domain=ed),
    )


class _FakeBackend:
    """Deterministic stand-in for Z3Backend: `unencodable` predicates fail
    encodable(); `empty` predicates are reported unsatisfiable by decide_unsat()."""

    def __init__(self, unencodable=(), empty=()):
        self.unencodable, self.empty = set(unencodable), set(empty)

    def encodable(self, pred: str) -> bool:
        return pred not in self.unencodable

    def decide_unsat(self, preds, bound: int = 0):
        return any(p in self.empty for p in preds)


class _FakeProvider:
    def __init__(self, reply: dict):
        self.reply, self.calls = reply, 0

    def repair_contract(self, statement, cd, cp, ed, problems):
        self.calls += 1
        return json.dumps(self.reply)


def _formalize(provider, backend, k: int = 1) -> Formalize:
    # _steer_contract only touches provider/smt/max_contract_repairs.
    return Formalize(provider, None, SMTVerifier(backend), None, None,
                     max_repairs=0, max_contract_repairs=k)


def test_repair_upgrades_an_unencodable_field_and_commits():
    backend = _FakeBackend(unencodable={"2^n"})
    good = {"claim_domain": "n >= 1", "claim_property": "n*n >= n", "established_domain": "n >= 1"}
    prov = _FakeProvider(good)
    prop = _prop("n >= 1", "n*n >= n", "2^n")
    _formalize(prov, backend)._steer_contract(prop)
    assert prop.expressio.established_domain == "n >= 1"  # committed
    assert prov.calls == 1


def test_already_encodable_contract_is_left_untouched():
    prov = _FakeProvider({"claim_domain": "x", "claim_property": "x", "established_domain": "x"})
    prop = _prop("n >= 1", "n*n >= n", "n >= 1")
    _formalize(prov, _FakeBackend())._steer_contract(prop)
    assert prov.calls == 0  # no repair attempted
    assert prop.enuntiatio.claim_domain == "n >= 1"


def test_repair_that_empties_the_domain_is_rejected():
    backend = _FakeBackend(unencodable={"2^n"}, empty={"n >= 5 and n <= 1"})
    bad = {"claim_domain": "n >= 5 and n <= 1", "claim_property": "n*n >= n", "established_domain": "n >= 1"}
    prov = _FakeProvider(bad)
    prop = _prop("n >= 1", "n*n >= n", "2^n")
    _formalize(prov, backend)._steer_contract(prop)
    assert prop.expressio.established_domain == "2^n"  # rejected -> unchanged, DEFERs honestly
    assert prop.enuntiatio.claim_domain == "n >= 1"


def test_repair_still_unencodable_is_not_committed():
    backend = _FakeBackend(unencodable={"2^n", "log n"})
    prov = _FakeProvider({"claim_domain": "n >= 1", "claim_property": "n*n >= n", "established_domain": "log n"})
    prop = _prop("n >= 1", "n*n >= n", "2^n")
    _formalize(prov, backend)._steer_contract(prop)
    assert prop.expressio.established_domain == "2^n"  # never committed a non-DSL field


def test_noop_when_disabled():
    backend = _FakeBackend(unencodable={"2^n"})
    prov = _FakeProvider({"claim_domain": "n >= 1", "claim_property": "n*n >= n", "established_domain": "n >= 1"})
    prop = _prop("n >= 1", "n*n >= n", "2^n")
    _formalize(prov, backend, k=0)._steer_contract(prop)
    assert prov.calls == 0 and prop.expressio.established_domain == "2^n"


def test_noop_without_repair_hook():
    class _NoRepair:  # a provider that does not offer repair_contract
        pass
    prop = _prop("n >= 1", "n*n >= n", "2^n")
    _formalize(_NoRepair(), _FakeBackend(unencodable={"2^n"}))._steer_contract(prop)
    assert prop.expressio.established_domain == "2^n"


def test_noop_without_structured_contract():
    prov = _FakeProvider({"claim_domain": "n >= 1", "claim_property": "n*n >= n", "established_domain": "n >= 1"})
    prop = _prop(None, None, None)  # prose-only / OPEN_FORM
    _formalize(prov, _FakeBackend())._steer_contract(prop)
    assert prov.calls == 0


# --- grammar reality: the same pass over the REAL z3 DSL ----------------------

@pytest.mark.skipif(not available(), reason="z3 not installed (verify extra)")
def test_real_dsl_repairs_variable_exponent_established_domain():
    # "2^n" is a VARIABLE exponent -> genuinely un-encodable in the sound DSL.
    good = {"claim_domain": "n >= 1", "claim_property": "n*n >= n", "established_domain": "n >= 1"}
    prov = _FakeProvider(good)
    prop = _prop("n >= 1", "n*n >= n", "2^n")
    _formalize(prov, Z3Backend())._steer_contract(prop)
    assert prop.expressio.established_domain == "n >= 1"
    assert prov.calls == 1


@pytest.mark.skipif(not available(), reason="z3 not installed (verify extra)")
def test_real_dsl_rejects_an_empty_repaired_domain():
    # encodable but unsatisfiable over the bounded box -> must be rejected.
    bad = {"claim_domain": "n >= 5 and n <= 1", "claim_property": "n*n >= n", "established_domain": "n >= 1"}
    prov = _FakeProvider(bad)
    prop = _prop("n >= 1", "n*n >= n", "2^n")
    _formalize(prov, Z3Backend())._steer_contract(prop)
    assert prop.expressio.established_domain == "2^n"  # the emptying repair was refused


# --- review hardening: fail-closed + property cannot be weakened (the HIGH finding) -

class _FakeBackendNoDecide:
    """encodable() but no decide_unsat() — exercises the fail-closed guard."""

    def __init__(self, unencodable=()):
        self.unencodable = set(unencodable)

    def encodable(self, pred: str) -> bool:
        return pred not in self.unencodable


def test_repair_refused_when_backend_cannot_verify_soundness():
    # No decide_unsat -> the empty-domain / property-strength guards cannot run, so the
    # pass must FAIL CLOSED (commit nothing), even though the repair was encodable.
    good = {"claim_domain": "n >= 1", "claim_property": "n*n >= n", "established_domain": "n >= 1"}
    prov = _FakeProvider(good)
    prop = _prop("n >= 1", "n*n >= n", "2^n")
    _formalize(prov, _FakeBackendNoDecide(unencodable={"2^n"}))._steer_contract(prop)
    assert prop.expressio.established_domain == "2^n"  # nothing committed
    assert prov.calls == 1  # repair was attempted, but its result was refused


@pytest.mark.skipif(not available(), reason="z3 not installed (verify extra)")
def test_real_dsl_rejects_property_weakening_repair():
    # Repair fixes the un-encodable established_domain but WEAKENS claim_property
    # (drops the evenness for a tautology). The new property does not imply the old
    # -> the repair must be refused so faithfulness cannot rest on a hollowed property.
    weaken = {"claim_domain": "n >= 1", "claim_property": "n >= 0", "established_domain": "n >= 1"}
    prov = _FakeProvider(weaken)
    prop = _prop("n >= 1", "n % 2 == 0", "2^n")
    _formalize(prov, Z3Backend())._steer_contract(prop)
    assert prop.enuntiatio.claim_property == "n % 2 == 0"   # original property preserved
    assert prop.expressio.established_domain == "2^n"        # whole repair refused


@pytest.mark.skipif(not available(), reason="z3 not installed (verify extra)")
def test_real_dsl_rejects_repair_of_an_unencodable_property():
    # The exact reproduced exploit: an un-encodable PROPERTY honestly DEFERs; repair
    # must NOT be able to rescue it by swapping in an encodable tautology, because the
    # original property cannot be compiled to verify the replacement preserves it.
    tautology = {"claim_domain": "n >= 1", "claim_property": "n >= 0", "established_domain": "n >= 1"}
    prov = _FakeProvider(tautology)
    prop = _prop("n >= 1", "2 ^ n > n * n", "n >= 1")  # property has a symbolic exponent
    _formalize(prov, Z3Backend())._steer_contract(prop)
    assert prop.enuntiatio.claim_property == "2 ^ n > n * n"  # not laundered into a PASS


@pytest.mark.skipif(not available(), reason="z3 not installed (verify extra)")
def test_real_backend_compile_is_crash_safe_on_nonboolean():
    # ADR 0022 review (medium): non-boolean terms raise z3.Z3Exception at CONSTRUCTION;
    # encodable/decide_unsat must report un-encodable, never crash (and so never abort a
    # cycle through _steer_contract).
    be = Z3Backend()
    assert be.encodable("not n") is False
    assert be.encodable("n and (n > 0)") is False
    assert be.decide_unsat(["not n"]) is None


# --- end-to-end through the REAL gate (call placement + the ADR 0022 goal) -----

def _gate(backend):
    from leibniz.gates.faithfulness import FaithfulnessGate
    from leibniz.probes import default_probes

    class _Judge:
        def round_trip_agrees(self, prop):
            return 0.0

    smt = SMTVerifier(backend)
    return FaithfulnessGate(smt=smt, probes=default_probes(smt), judge=_Judge())


@pytest.mark.skipif(not available(), reason="z3 not installed (verify extra)")
def test_steered_contract_turns_a_defer_into_a_pass():
    from leibniz.types import ClaimType, TrustTier, Verdict
    be = Z3Backend()
    good = {"claim_domain": "n >= 1", "claim_property": "n < 2 * n", "established_domain": "n >= 1"}
    prov = _FakeProvider(good)
    prop = _prop("n >= 1", "n < 2 * n", "2^n")
    prop.enuntiatio.claim_type = ClaimType.COMPLEXITY_BOUND
    # un-encodable established_domain -> the gate DEFERs before steering …
    assert _gate(be).check(prop).verdict is Verdict.DEFER
    _formalize(prov, be)._steer_contract(prop)
    # … and certifies mechanically after (the ADR 0022 goal, end to end).
    ev = _gate(be).check(prop)
    assert ev.verdict is Verdict.PASS and ev.tier is TrustTier.MECHANICAL


@pytest.mark.skipif(not available(), reason="z3 not installed (verify extra)")
def test_steer_commits_but_gate_still_defers_a_coverage_break():
    # _steer_contract does NOT re-check coverage; it relies on the downstream gate. A
    # repair that is encodable + non-empty but breaks coverage must still DEFER there.
    from leibniz.types import ClaimType, Verdict
    be = Z3Backend()
    break_cov = {"claim_domain": "n >= 0", "claim_property": "n >= 0", "established_domain": "n >= 5"}
    prov = _FakeProvider(break_cov)
    prop = _prop("n >= 0", "n >= 0", "2^n")
    prop.enuntiatio.claim_type = ClaimType.COMPLEXITY_BOUND
    _formalize(prov, be)._steer_contract(prop)
    assert prop.expressio.established_domain == "n >= 5"   # committed (encodable, non-empty)
    assert _gate(be).check(prop).verdict is Verdict.DEFER  # but coverage gap -> DEFER

"""SEALED trust guards for the ADR 0041 tool seam (Phase 1).

This file is a load-bearing invariant suite (ADR 0041 §2.4 option B): it is protected from agent edits
by the same PreToolUse hook that guards `tests/test_invariants.py`, so the anti-TCB-growth property
cannot be quietly weakened. The existing seven invariants in `tests/test_invariants.py` stay
byte-identical; these are NEW guards for the generalized seam.

What is proven here (the USE-vs-DECIDE gate + the two laundering attacks):
  - a tool can be REGISTERED + RUN, but with the dormant-empty registry every PASS is DEFER (State 1);
  - a PASS is accepted (MECHANICAL) only when an operator registered BOTH a re-checker and a statement
    template, the re-checker RE-DERIVES from the certificate data, and the claimed statement equals the
    operator template applied to that data (E1/E2/E6/E7);
  - a tool can never be KERNEL_PRODUCER / on the proof edge (E3);
  - trust.py rejects a mechanical faithfulness edge whose producer is not operator-admitted (ATTACK 2).
"""
from __future__ import annotations

import pytest

from leibniz.tools.protocol import (
    Certificate,
    Provenance,
    ToolDescriptor,
    ToolEvidence,
    ToolResult,
)
from leibniz.tools.registry import ToolRegistry
from leibniz.types import EdgeEvidence, TrustTier, Verdict
from leibniz.trust import (
    FAITHFULNESS_EDGE,
    FAITHFULNESS_PRODUCERS,
    KERNEL_PRODUCER,
    PROOF_EDGE,
    TrustPolicy,
    TrustViolation,
)


# --- fakes -------------------------------------------------------------------------------------
class _FakeTool:
    def __init__(self, result: ToolResult, *, name="fake", kind="t", cost=10,
                 provenance=Provenance.SELF_BUILT):
        self.descriptor = ToolDescriptor(name=name, provenance=provenance, cost_rank=cost,
                                         result_kind=kind)
        self._result = result
        self.seen_args = []

    def applies(self, ctx):
        return True

    def run(self, ctx):
        self.seen_args.append(ctx)
        return self._result


def _cert(kind="t", rechecked=True, data=5, statement="ge 5"):
    return Certificate(kind=kind, rechecked=rechecked, data=data, detail={"statement": statement})


# re-checker that genuinely RE-DERIVES from the certificate data (never trusts cert.kind/.rechecked)
def _rechecker(cert) -> bool:
    return isinstance(cert.data, int) and cert.data >= 0


def _template(data) -> str:        # operator-owned statement template (E7)
    return f"ge {data}"


def _passing_tool(**kw):
    return _FakeTool(ToolResult(Verdict.PASS, "fake/recheck", certificate=_cert(**kw)))


# --- State 1: dormant-empty registry => every PASS is DEFER (E1/E2) ----------------------------
def test_empty_registry_downgrades_pass_to_defer():
    reg = ToolRegistry(tools=(_passing_tool(),))
    ev = reg.run(ctx=None)
    assert ev.verdict is Verdict.DEFER          # registered + runnable, but cannot DECIDE
    assert ev.rechecked_by_registry is False


def test_unregistered_kind_defers_even_with_other_kinds_registered():
    reg = ToolRegistry(tools=(_passing_tool(kind="t"),))
    reg.register_decider("other", _rechecker, _template)   # a DIFFERENT kind
    assert reg.run(ctx=None).verdict is Verdict.DEFER


# --- State 2: accept only on operator registration + re-derive + statement match ---------------
def test_registered_decider_accepts_a_genuine_pass():
    reg = ToolRegistry(tools=(_passing_tool(data=5, statement="ge 5"),))
    reg.register_decider("t", _rechecker, _template)
    ev = reg.run(ctx=None)
    assert ev.verdict is Verdict.PASS and ev.tier is TrustTier.MECHANICAL
    assert ev.rechecked_by_registry is True and ev.certificate_kind == "t"


def test_rechecker_must_rederive_from_data_not_kind(_e6=True):
    # cert claims kind "t" (registered) but data fails re-derivation => DEFER (cert.rechecked ignored)
    reg = ToolRegistry(tools=(_passing_tool(data=-1, statement="ge -1"),))
    reg.register_decider("t", _rechecker, _template)
    assert reg.run(ctx=None).verdict is Verdict.DEFER


def test_statement_template_capture_is_blocked(_e7=True):
    # the tool authors a STRONGER statement than its data supports; template recomputes "ge 5" != "ge 999"
    reg = ToolRegistry(tools=(_passing_tool(data=5, statement="ge 999"),))
    reg.register_decider("t", _rechecker, _template)
    ev = reg.run(ctx=None)
    assert ev.verdict is Verdict.DEFER and "template" in ev.detail.get("defer_reason", "")


def test_pass_without_certificate_defers():
    reg = ToolRegistry(tools=(_FakeTool(ToolResult(Verdict.PASS, "fake", certificate=None)),))
    reg.register_decider("t", _rechecker, _template)
    assert reg.run(ctx=None).verdict is Verdict.DEFER


def test_fail_is_a_mechanical_refutation():
    reg = ToolRegistry(tools=(_FakeTool(ToolResult(Verdict.FAIL, "fake/refute")),))
    ev = reg.run(ctx=None)
    assert ev.verdict is Verdict.FAIL and ev.tier is TrustTier.MECHANICAL


# --- E3: a tool is never KERNEL_PRODUCER and never on the proof edge ----------------------------
def test_tool_evidence_is_never_proof_edge_or_kernel_producer():
    reg = ToolRegistry(tools=(_passing_tool(),))
    reg.register_decider("t", _rechecker, _template)
    ev = reg.run(ctx=None)
    assert isinstance(ev, ToolEvidence)
    assert not hasattr(ev, "edge")               # structurally cannot be PROOF_EDGE
    assert ev.producer != KERNEL_PRODUCER        # a tool is never the kernel


def test_tool_run_receives_only_ctx_not_the_registry():
    t = _passing_tool()
    reg = ToolRegistry(tools=(t,))
    reg.register_decider("t", _rechecker, _template)
    reg.run(ctx="just-the-context")
    assert t.seen_args == ["just-the-context"]   # the tool never gets recheckers/templates


# --- ATTACK 2: trust.py faithfulness-producer allowlist ----------------------------------------
def test_faithfulness_producer_allowlist_rejects_unadmitted_producer():
    p = TrustPolicy()
    # producer=None (legacy/unstamped) is unaffected -> no raise
    p.validate_edge(EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS))
    # an operator-admitted producer passes
    p.validate_edge(EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS,
                                 producer="walnut/recheck"))
    # a tool's self-chosen producer is rejected structurally
    with pytest.raises(TrustViolation):
        p.validate_edge(EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS,
                                     producer="self_built_tool/recheck"))


def test_live_faithfulness_producers_are_all_allowlisted():
    # regression: the four producers the live pipeline emits must stay admitted
    for prod in ("SMTVerifier.gaming_witness", "ClaimProbe", "FaithfulnessGate", "walnut/recheck"):
        assert prod in FAITHFULNESS_PRODUCERS


class _EvilStr(str):
    """A tool-supplied str subclass that lies about equality to defeat a naive `!=` check."""
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    __hash__ = str.__hash__


def test_statement_str_subclass_cannot_launder_a_stronger_claim(_m1=True):
    # E7 must pin the claimed statement to a builtin str: an _EvilStr("ge 999") over data=5 (template
    # "ge 5") must DEFER, not PASS — otherwise a tool authors the proposition it is graded on.
    tool = _FakeTool(ToolResult(Verdict.PASS, "fake/recheck",
                                certificate=Certificate(kind="t", rechecked=True, data=5,
                                                        detail={"statement": _EvilStr("ge 999")})))
    reg = ToolRegistry(tools=(tool,))
    reg.register_decider("t", _rechecker, _template)
    assert reg.run(ctx=None).verdict is Verdict.DEFER


def test_fail_short_circuits_before_a_costlier_pass():
    failing = _FakeTool(ToolResult(Verdict.FAIL, "fake/refute"), name="fail", cost=1)
    passing = _passing_tool()                       # cost 10
    reg = ToolRegistry(tools=(passing, failing))    # dispatch sorts by cost_rank, not tuple order
    reg.register_decider("t", _rechecker, _template)
    assert reg.run(ctx=None).verdict is Verdict.FAIL
    assert passing.seen_args == []                  # the cheaper FAIL killed before the costlier PASS ran


def test_dispatch_is_cheapest_first():
    order = []

    class _Rec:
        def __init__(self, name, cost):
            self.descriptor = ToolDescriptor(name=name, provenance=Provenance.SELF_BUILT,
                                             cost_rank=cost, result_kind="t")

        def applies(self, ctx):
            order.append(self.descriptor.name)
            return True

        def run(self, ctx):
            return ToolResult(Verdict.DEFER, "fake")

    ToolRegistry(tools=(_Rec("dear", 100), _Rec("cheap", 1))).run(ctx=None)
    assert order == ["cheap", "dear"]


def test_fall_through_after_a_rejected_pass_reaches_a_good_tool():
    bad = _FakeTool(ToolResult(Verdict.PASS, "fake/recheck", certificate=_cert(data=-1, statement="ge -1")),
                    name="bad", cost=1)
    good = _FakeTool(ToolResult(Verdict.PASS, "fake/recheck", certificate=_cert(data=5, statement="ge 5")),
                     name="good", cost=2)
    reg = ToolRegistry(tools=(bad, good))
    reg.register_decider("t", _rechecker, _template)
    ev = reg.run(ctx=None)
    assert ev.verdict is Verdict.PASS and ev.rechecked_by_registry is True and ev.tool == "good"


def test_tool_producer_is_rejected_on_a_faithfulness_edge_end_to_end():
    # ATTACK 2, end-to-end: the producer the registry stamps on a real PASS is a tool string; if a
    # future caller put it on a MECHANICAL faithfulness edge, trust.py rejects it (not allowlisted).
    reg = ToolRegistry(tools=(_passing_tool(),))
    reg.register_decider("t", _rechecker, _template)
    ev = reg.run(ctx=None)
    assert ev.verdict is Verdict.PASS
    with pytest.raises(TrustViolation):
        TrustPolicy().validate_edge(
            EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS, producer=ev.producer))


def test_a_tool_cannot_promulgate_via_a_faithfulness_edge_it_authored():
    # even if a tool fabricated a mechanical faithfulness EdgeEvidence, validate_path rejects it
    p = TrustPolicy()
    edges = [
        EdgeEvidence(PROOF_EDGE, TrustTier.MECHANICAL, Verdict.PASS, producer=KERNEL_PRODUCER),
        EdgeEvidence(FAITHFULNESS_EDGE, TrustTier.MECHANICAL, Verdict.PASS,
                     producer="self_built_tool/recheck"),
    ]
    with pytest.raises(TrustViolation):
        p.validate_path(edges)

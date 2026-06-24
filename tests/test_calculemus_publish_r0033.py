"""ADR 0033 Slice 2: the publish guard on the operator publish tier. CI-safe.

The public Codex is a PROD artefact. Publishing is ADDITIVE-stricter than ADR 0008's
operator-approval gate: it is refused unless this process runs as PROD *and* the caller
confirms the running instance explicitly (so a UAT/dev law can never be published as PROD,
and a publish can never happen by default). The rendered colophon / public output shows the
instance so provenance is visible.

Pure Python — no Lean, no network. Deliberately NOT in test_invariants.py, which stays
byte-identical: this is additive isolation, not a trust-edge change.
"""
from __future__ import annotations

import pytest

from leibniz.calculemus import Calculemus, running_instance
from leibniz.propositio import Demonstratio, Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimType


def _law(statement: str = "comparison sort is Omega(n log n)") -> Propositio:
    p = Propositio(
        enuntiatio=Enuntiatio(statement=statement, claim_type=ClaimType.COMPLEXITY_BOUND,
                              falsifiable_claim="a comparison sort in o(n log n)"),
        expressio=Expressio(theorem_src="theorem sort_bound : SortLowerBound"),
    )
    demo = Demonstratio(proof_obligation="sort_bound", proof_src="by induction_hammer")
    demo.kernel_verified = True
    demo.seal()  # Q.E.D.
    p.demonstratio = demo
    p.promulgated = True
    return p


def _codex_with_law(monkeypatch) -> tuple[Calculemus, Propositio]:
    """A Codex holding one promulgated law. Promotion runs without instance context —
    only publish (the operator step) is guarded — so this is instance-agnostic."""
    monkeypatch.delenv("LEIBNIZ_INSTANCE", raising=False)
    cx = Calculemus()
    law = _law()
    assert cx.promulgate(law) is True  # promulgation (promotion) is unchanged by Slice 2
    return cx, law


def test_running_instance_matches_runtime_convention(monkeypatch):
    monkeypatch.delenv("LEIBNIZ_INSTANCE", raising=False)
    assert running_instance() == "dev"               # default
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "  PROD ")
    assert running_instance() == "prod"               # stripped + lowered


def test_publish_refused_when_instance_is_not_prod(monkeypatch):
    cx, law = _codex_with_law(monkeypatch)
    for inst in ("dev", "uat", "UAT", "staging"):
        monkeypatch.setenv("LEIBNIZ_INSTANCE", inst)
        with pytest.raises(RuntimeError, match="publish guard"):
            cx.publish(law.pid, operator_approved=True, confirm_instance="prod")
        assert law.pid not in cx.published           # nothing slipped through


def test_publish_refused_without_matching_confirm_instance(monkeypatch):
    cx, law = _codex_with_law(monkeypatch)
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "prod")
    # missing confirmation -> refused (cannot publish by default)
    with pytest.raises(RuntimeError, match="publish guard"):
        cx.publish(law.pid, operator_approved=True)
    # mismatched confirmation -> refused
    with pytest.raises(RuntimeError, match="publish guard"):
        cx.publish(law.pid, operator_approved=True, confirm_instance="uat")
    assert law.pid not in cx.published


def test_publish_succeeds_for_prod_plus_confirm_plus_operator(monkeypatch):
    cx, law = _codex_with_law(monkeypatch)
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "prod")
    # operator-approval gate (ADR 0008) is still enforced — additive, not weaker
    assert cx.publish(law.pid, operator_approved=False, confirm_instance="prod") is False
    assert law.pid not in cx.published
    # confirm_instance is normalized like the running instance
    assert cx.publish(law.pid, operator_approved=True, confirm_instance="PROD") is True
    assert law.pid in cx.published


def test_uat_law_cannot_be_published_as_prod(monkeypatch):
    # The core ADR 0033 failure mode: a law surfaced under UAT must not reach the public Codex.
    cx, law = _codex_with_law(monkeypatch)
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "uat")
    with pytest.raises(RuntimeError):
        cx.publish(law.pid, operator_approved=True, confirm_instance="uat")   # confirm matches, but not PROD
    with pytest.raises(RuntimeError):
        cx.publish(law.pid, operator_approved=True, confirm_instance="prod")  # spoofed confirm, still refused
    assert law.pid not in cx.published
    assert "nothing published" in cx.render_public().lower()


def test_colophon_and_public_output_show_the_instance(monkeypatch):
    cx, law = _codex_with_law(monkeypatch)
    # held-back colophon shows provenance under any instance
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "uat")
    assert "instance: uat" in cx.colophon()
    assert "instance: uat" in cx.render_public()      # even when nothing is published yet
    # once published under PROD, the public ledger shows the PROD instance
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "prod")
    assert cx.publish(law.pid, operator_approved=True, confirm_instance="prod") is True
    public = cx.render_public()
    assert "instance: prod" in public
    assert law.enuntiatio.statement in public         # the law itself is rendered

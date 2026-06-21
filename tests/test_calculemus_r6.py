"""R6: Calculemus reading-room + operator publish tier (ADR 0008). CI-safe.

Exit test: a law appears in Calculemus, proof open, only after an explicit operator
publish; promotion is not publication.
"""
from __future__ import annotations

from leibniz.calculemus import Calculemus, render_propositio
from leibniz.propositio import Demonstratio, Enuntiatio, Expressio, Propositio
from leibniz.types import ClaimType


def _law(statement="comparison sort is Omega(n log n)", verified=True) -> Propositio:
    p = Propositio(
        enuntiatio=Enuntiatio(statement=statement, claim_type=ClaimType.COMPLEXITY_BOUND,
                              falsifiable_claim="a comparison sort in o(n log n)"),
        expressio=Expressio(theorem_src="theorem sort_bound : SortLowerBound"),
    )
    demo = Demonstratio(proof_obligation="sort_bound", proof_src="by induction_hammer")
    demo.kernel_verified = verified
    demo.seal()  # Q.E.D. iff verified
    p.demonstratio = demo
    p.promulgated = verified
    return p


def test_render_shows_full_triad_and_certificate():
    md = render_propositio(_law())
    assert "comparison sort is Omega(n log n)" in md
    assert "theorem sort_bound : SortLowerBound" in md
    assert "by induction_hammer" in md
    assert "Q.E.D." in md
    assert "kernel_verified: True" in md


def test_codex_admits_only_kernel_verified_laws():
    cx = Calculemus()
    assert cx.promulgate(_law(verified=False)) is False  # Q.E.I. -> refused
    assert len(cx.codex) == 0
    assert cx.promulgate(_law(verified=True)) is True
    assert len(cx.codex) == 1


def test_promotion_is_not_publication():
    cx = Calculemus()
    law = _law()
    cx.promulgate(law)
    assert law.pid not in cx.published
    assert "nothing published" in cx.render_public().lower()
    assert law.enuntiatio.statement in cx.colophon()  # held back, with reason


def test_publish_requires_explicit_operator_approval():
    cx = Calculemus()
    law = _law()
    cx.promulgate(law)
    assert cx.publish(law.pid, operator_approved=False) is False  # daemon can't publish
    assert law.pid not in cx.published
    assert cx.publish(law.pid, operator_approved=True) is True    # human does
    assert law.pid in cx.published
    public = cx.render_public()
    assert law.enuntiatio.statement in public
    assert "by induction_hammer" in public  # proof open to inspection


def test_publish_unknown_pid_is_refused():
    assert Calculemus().publish("no-such-pid", operator_approved=True) is False

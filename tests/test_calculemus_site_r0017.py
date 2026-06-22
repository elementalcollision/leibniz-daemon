"""ADR 0017: Calculemus site ledger export (CI-safe; no Lean, no network)."""
from __future__ import annotations

from leibniz.calculemus import Calculemus
from leibniz.calculemus_site import law_payload, ledger_payload
from leibniz.propositio import Demonstratio, Enuntiatio, Expressio, Propositio
from leibniz.trust import PROOF_EDGE
from leibniz.types import ClaimType, EdgeEvidence, TrustTier, Verdict


def _law(stmt: str, name: str, *, verified: bool = True, consensus: int = 2) -> Propositio:
    p = Propositio(
        enuntiatio=Enuntiatio(statement=stmt, claim_type=ClaimType.STRUCTURAL, falsifiable_claim="nope"),
        expressio=Expressio(theorem_src=f"theorem {name} (a b : Nat) : a + b = b + a", imports=("Mathlib.Tactic",)),
    )
    de = Demonstratio(proof_obligation=name, proof_src="by ring")
    de.kernel_verified = verified
    de.seal()
    p.demonstratio = de
    p.promulgated = verified  # test-only (boundary guard scans leibniz/, not tests/)
    if consensus:
        p.record(EdgeEvidence(PROOF_EDGE, TrustTier.MECHANICAL, Verdict.PASS, detail={"consensus": consensus}))
    return p


def test_only_published_laws_appear_in_laws():
    cx = Calculemus()
    a, b = _law("Addition commutes", "add_comm"), _law("Multiplication commutes", "mul_comm")
    cx.promulgate(a)
    cx.promulgate(b)
    cx.publish(a.pid, operator_approved=True)  # only `a` is published

    led = ledger_payload(cx)
    assert [law["statement"] for law in led["laws"]] == ["Addition commutes"]
    held = [h["statement"] for h in led["held_back"]]
    assert "Multiplication commutes" in held  # promulgated, not published -> colophon only


def test_law_payload_carries_triad_and_certificate():
    pl = law_payload(_law("Addition commutes", "add_comm"))
    assert pl["id"] == "add_comm"
    assert pl["statement"] == "Addition commutes"
    assert pl["theorem_src"].startswith("theorem add_comm")
    assert pl["proof_src"] == "by ring"
    assert pl["qed"] == "Q.E.D." and pl["kernel_verified"] is True
    assert pl["consensus"] == 2
    assert pl["imports"] == ["Mathlib.Tactic"]


def test_unverified_law_carries_no_qed_and_cannot_reach_codex():
    p = _law("Bad claim", "bad", verified=False)
    pl = law_payload(p)
    assert pl["kernel_verified"] is False and pl["qed"] == "Q.E.I."
    assert Calculemus().promulgate(p) is False  # never reaches the Codex


def test_ledger_payload_shape():
    led = ledger_payload(Calculemus(), generated_at="2026-06-21T00:00:00Z", cycles=[{"cycle": 1}])
    assert led["site"] == "Calculemus"
    assert led["generated_at"] == "2026-06-21T00:00:00Z"
    assert led["laws"] == [] and led["held_back"] == []
    assert led["cycles"] == [{"cycle": 1}]

"""ADR 0017: Calculemus site ledger export (CI-safe; no Lean, no network)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from leibniz.calculemus import Calculemus
from leibniz.calculemus_site import (
    cycle_payload,
    downloadable_artifact,
    file_sha256,
    law_payload,
    ledger_payload,
    requires_references,
)
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


def test_only_published_laws_appear_in_laws(monkeypatch):
    monkeypatch.setenv("LEIBNIZ_INSTANCE", "prod")  # ADR 0033: publish is PROD-only + confirmed
    cx = Calculemus()
    a, b = _law("Addition commutes", "add_comm"), _law("Multiplication commutes", "mul_comm")
    cx.promulgate(a)
    cx.promulgate(b)
    cx.publish(a.pid, operator_approved=True, confirm_instance="prod")  # only `a` is published

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


def test_cycle_payload_shape_and_read_only():
    # The work-log entry (Il Lavoro / /cycles) is descriptive: no certificate fields.
    c = cycle_payload(
        cycle=2, date="2026-07-03", domain="Formal verification", kind="audit",
        title="An audit", summary="what happened",
        findings=[{"id": "P1", "verdict": "VACUOUS"}], artifacts=[{"name": "x.lean"}],
    )
    assert c["cycle"] == 2 and c["date"] == "2026-07-03" and c["kind"] == "audit"
    assert c["domain"] == "Formal verification" and c["title"] == "An audit"
    assert c["findings"][0]["verdict"] == "VACUOUS" and c["artifacts"][0]["name"] == "x.lean"
    assert c["links"] == [] and c["laws"] == [] and c["references"] == []   # optional fields default empty
    assert c["repositories"] == []                                          # code-provenance defaults empty
    # a cycle mints no certificate: no kernel_verified / qed / promulgated leaks in
    assert not ({"kernel_verified", "qed", "promulgated"} & set(c))
    # it composes into the ledger under `cycles`, untouched
    assert ledger_payload(Calculemus(), cycles=[c])["cycles"] == [c]


def test_downloadable_artifact_publishes_bytes_with_hash(tmp_path):
    # Because the source repo is private, the public download IS the auditable artifact — pinned by sha256.
    f = tmp_path / "cert.lean"
    f.write_text("theorem t : True := trivial\n")
    a = downloadable_artifact(f, cycle_id="cycle_000005", checker="Lean 4.31", result="0 errors", kind="lean-proof")
    assert a["name"] == "cert.lean" and a["download"] == "/artifacts/cycle_000005/cert.lean"
    assert a["sha256"] == file_sha256(f) and len(a["sha256"]) == 64
    import hashlib
    assert a["sha256"] == hashlib.sha256(f.read_bytes()).hexdigest()   # the exact bytes served


def test_sources_must_be_cited_on_cite_worthy_cycles():
    # A cite-worthy cycle (audit/verification/refutation of external work) MUST carry references (APA).
    ref = {"citation": "Kheltz. (2026). MCR: A universal transition equation [Whitepaper].", "url": ""}
    cited = cycle_payload(cycle=2, date="2026-07-03", domain="Formal verification", kind="audit",
                          title="t", summary="s", references=[ref])
    assert cited["references"] == [ref]
    assert requires_references(cited) is False          # cited audit is fine
    uncited = cycle_payload(cycle=3, date="2026-07-03", domain="d", kind="audit", title="t", summary="s")
    assert requires_references(uncited) is True          # an uncited audit is a defect
    # a metrics-shaped cycle (no external source) is not cite-worthy
    metrics = cycle_payload(cycle=4, date="2026-07-03", domain="d", kind="", title="t", summary="s")
    assert requires_references(metrics) is False


def test_mcr_audit_cycle_carries_all_eight_verdicts():
    # Lock the shipped MCR work-log entry (scripts/export_mcr_cycle.py -> the /cycles fragment).
    root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("export_mcr_cycle", root / "scripts" / "export_mcr_cycle.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    c = m.build_cycle()
    assert c["kind"] == "audit" and c["domain"] == "Formal verification"
    ids = [f["id"] for f in c["findings"]]
    assert ids == ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]     # every problem is present
    verdicts = {f["id"]: f["verdict"] for f in c["findings"]}
    assert verdicts["P4"].startswith("REFUTED") and verdicts["P7"] == "NOT-PROVEN"  # the honest downgrade held
    assert verdicts["P8"] == "PROVEN"                                  # the steelman is carried
    assert {a["name"] for a in c["artifacts"]} == {"mcr_p4_not_derivable.lean", "mcr_audit_artifacts.py"}
    # the underpinnings are publicly downloadable with an integrity hash (private repo notwithstanding)
    for a in c["artifacts"]:
        assert a["download"] == f"/artifacts/cycle_000002/{a['name']}"
        assert len(a["sha256"]) == 64 and all(ch in "0123456789abcdef" for ch in a["sha256"])
    assert "no-op stub" in c["summary"]                               # the flagship VACUOUS framing survives
    # the audited source is cited (APA) — the scholarly-integrity requirement
    assert c["references"] and "Kheltz" in c["references"][0]["citation"]
    assert not requires_references(c)                                 # a cited audit passes the guard
    # the code trail links back to GitHub — the auditable provenance
    roles = {r["role"] for r in c["repositories"]}
    assert {"source", "produced"} <= roles
    assert all(r["url"].startswith("https://github.com/") for r in c["repositories"])
    p3 = {f["id"]: f for f in c["findings"]}["P3"]
    assert "ambiguous state" in p3["note"] and "per-symbol" in p3["note"]  # the state-a correction is carried

    # The pipeline contract: a self-describing fragment the publication agent consumes.
    frag = m.build_fragment(generated_at="2026-07-03T00:00:00Z")
    assert frag["meta"]["generated_at"] == "2026-07-03T00:00:00Z"
    assert "codex-calculemus" in frag["meta"]["target"] and "cycles[]" in frag["meta"]["target"]
    assert frag["cycles"] == [c]                                      # meta is provenance; cycles is the payload

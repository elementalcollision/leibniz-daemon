"""ADR 0050 Phase 4 / ADR 0063 — the origination path.

An ORIGINATED law is a fact the daemon conjectured itself — **not** a re-decision of published work. It
carries no source citation; instead it must PASS the full mechanical novelty gate (invariant #4:
novelty settled by retrieval + a decision procedure, never a judge), and it carries that PASS as its
``novelty_attestation``.

**Fail-closed.** :func:`attest_novelty` returns ``None`` unless the gate returns ``Verdict.PASS`` — so an
originated law can NEVER be emitted for a claim the gate finds trivial (``is_trivial`` /
coefficient-degenerate, ADR 0061), KNOWN (``contains_equivalent`` formal-hash match), or a structural
restatement (``structural_known``, ADR 0032). Origination changes only PROVENANCE (report-only); the
proof is still kernel-checked and ``kernel_verified`` is still written only by
``LeanVerifier.discharge``.

**Honesty.** The attestation certifies novelty *per the daemon's mechanical gate and its known-results
corpus* — the daemon's own conjecture, not a re-decision of a cited source. It is NOT a claim of
absolute mathematical novelty: a false-NOVEL (a textbook fact absent from the corpus) is possible and is
the accepted error direction (ADR 0032). The caveat is carried in the attestation itself.
"""
from __future__ import annotations

from typing import Optional

from leibniz.propositio import Propositio
from leibniz.types import ClaimSignature, ClaimType, Verdict
from leibniz.verifiers import normalize_statement


def claim_signature(theorem_src: str, claim_type: ClaimType, subject: str, relation: str) -> ClaimSignature:
    """The structural fingerprint the novelty gate compares — ``formal_hash`` from the normalized Lean
    statement, plus canonical subject/relation. `contains_equivalent` keys on the hash."""
    return ClaimSignature(claim_type=claim_type, subject=subject, relation=relation,
                          formal_hash=normalize_statement(theorem_src))


def attest_novelty(prop: Propositio, novelty_gate) -> Optional[dict]:
    """Run the FULL mechanical novelty gate on ``prop``; return an attestation dict iff it says NOVEL
    (``Verdict.PASS``), else ``None`` (fail-closed — an originated law MUST be gate-novel).

    The gate runs (all kill-only, no judge): ADR 0061 coefficient-degenerate → ``is_trivial`` tactic
    ladder → ``contains_equivalent`` (formal-hash corpus match) → ``structural_known`` (ADR 0032
    congruence signature). Any hit ⇒ the claim is trivial / KNOWN / a restatement ⇒ not originatable."""
    assert prop.signature is not None, "attest_novelty needs prop.signature (see claim_signature)"
    edge = novelty_gate.check(prop)
    if edge.verdict is not Verdict.PASS:
        return None
    return {
        "verdict": "novel",
        "producer": edge.producer,                       # "NoveltyGate"
        "method": "retrieval + decision procedure (invariant #4); no judge",
        "checks_passed": ["coefficient_degenerate", "is_trivial", "contains_equivalent", "structural_known"],
        "neighbors": (edge.detail or {}).get("neighbors", []),
        "caveat": ("Novel per the daemon's mechanical novelty gate and its known-results corpus — the "
                   "daemon's own conjecture, not a re-decision of any cited source. NOT a claim of "
                   "absolute mathematical novelty; a false-NOVEL (a textbook fact absent from the corpus) "
                   "is possible and is the accepted error direction (ADR 0032)."),
    }

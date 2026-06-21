"""The six-stage pipeline, inherited from Newton's loop shape.

    survey -> conjecture -> formalize -> derive -> demonstrate -> promulgate

Each stage is a small object with one method. Stages only ever *advance* a
Propositio or quarantine it; the verdicts live in the gates and verifiers, never
in the stages themselves. This keeps the trust boundary legible: the stages move
work; the gates decide.

Cheap-refutation-first ordering is realized by FORMALIZE running the SMT cheap
refute and the novelty/non-triviality gate *before* DERIVE spends proof compute,
and by DEMONSTRATE running the faithfulness gate before sealing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from leibniz.adapters import LeonardoAdapter, ProviderAdapter
from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.gates.novelty import NoveltyGate
from leibniz.propositio import (
    Demonstratio,
    Enuntiatio,
    Expressio,
    Propositio,
)
from leibniz.types import (
    ClaimSignature,
    ClaimType,
    FinishReason,
    Role,
    Verdict,
)
from leibniz.verifiers import LeanVerifier, SMTVerifier, normalize_statement


@dataclass
class Survey:
    """Leonardo seam: find live edges of the domain + analogical stepping stones."""

    leonardo: LeonardoAdapter

    def run(self, domain: str) -> list[str]:
        edges = self.leonardo.survey_frontier(domain)
        seeds: list[str] = []
        for e in edges:
            seeds.append(e)
            seeds.extend(self.leonardo.cross_domain_analogies(e))
        return seeds


@dataclass
class Conjecture:
    """LLM-as-variation-operator. Proposes an Enuntiatio. Proposal only."""

    provider: ProviderAdapter

    def run(self, seed: str) -> Propositio:
        draft = self.provider.propose(Role.CONJECTURE, seed)
        en = _parse_enuntiatio(draft, seed)
        return Propositio(enuntiatio=en, behavior_descriptor=_descriptor(seed))


@dataclass
class Formalize:
    """Draft the Lean statement, check it compiles, then run the CHEAP gates:
    SMT cheap-refute, then novelty/non-triviality, then faithfulness. All before
    any proof compute."""

    provider: ProviderAdapter
    lean: LeanVerifier
    smt: SMTVerifier
    novelty: NoveltyGate
    faithfulness: FaithfulnessGate

    def run(self, prop: Propositio) -> Optional[Propositio]:
        draft = self.provider.propose(Role.FORMALIZE, prop.enuntiatio.statement)
        expr = Expressio(theorem_src=draft)
        if not self.lean.validate_statement(expr):
            prop.quarantine(FinishReason.MALFORMED)
            return None
        expr.normalized_hash = _normalized_hash(self.lean, expr)
        prop.expressio = expr
        prop.signature = _signature(prop)

        # cheap refutation first
        cr = self.smt.cheap_refute(prop.enuntiatio.falsifiable_claim)
        prop.record(cr)
        if cr.verdict is Verdict.FAIL:
            prop.quarantine(FinishReason.REFUTED)
            return None

        nov = self.novelty.check(prop)
        prop.record(nov)
        if nov.verdict is Verdict.FAIL:
            return None  # gate already quarantined with KNOWN/TRIVIAL

        faith = self.faithfulness.check(prop)
        prop.record(faith)
        if faith.verdict is not Verdict.PASS:
            return None  # GAMED / UNFAITHFUL / DEFER -- do not pay for proof

        return prop


@dataclass
class Derive:
    """Draft a proof script. The expensive stage; only reached by survivors."""

    provider: ProviderAdapter

    def run(self, prop: Propositio) -> Propositio:
        assert prop.expressio is not None
        script = self.provider.propose(Role.PROOF_DRAFT, prop.expressio.theorem_src)
        prop.demonstratio = Demonstratio(
            proof_obligation=prop.signature.relation if prop.signature else "claim",
            proof_src=script,
        )
        return prop


@dataclass
class Demonstrate:
    """Kernel check. The sole MECHANICAL proof verdict."""

    lean: LeanVerifier

    def run(self, prop: Propositio) -> Propositio:
        assert prop.expressio is not None and prop.demonstratio is not None
        ev = self.lean.discharge(prop.expressio, prop.demonstratio)
        prop.record(ev)
        return prop


@dataclass
class Promulgate:
    """Commit to the Codex iff promotable; else leave quarantined. Promotion is
    not publication -- publishing is a separate operator-tier action."""

    def run(self, prop: Propositio, promotable: bool) -> Propositio:
        if promotable:
            prop.promulgated = True
            prop.finish_reason = FinishReason.PROMULGATED
        elif prop.finish_reason is None:
            prop.quarantine(FinishReason.UNPROVEN)
        return prop


# --- tiny parsers/derivers; real versions use structured LLM output -----------

def _normalized_hash(lean, expr: Expressio) -> str:
    """Prefer the backend's elaborator-canonical structural hash (R1c) so that
    alpha-renamed / notation-different statements of the same theorem collide;
    fall back to the textual hash for fakes or statements that don't elaborate."""
    norm = getattr(getattr(lean, "backend", None), "normalize_statement", None)
    if norm is not None:
        h = norm(expr)
        if h:
            return h
    return normalize_statement(expr.theorem_src)


def _parse_enuntiatio(draft: str, seed: str) -> Enuntiatio:
    return Enuntiatio(
        statement=draft.strip() or seed,
        claim_type=ClaimType.COMPLEXITY_BOUND,
        falsifiable_claim=f"exists input violating: {draft.strip() or seed}",
    )


def _descriptor(seed: str) -> tuple[float, ...]:
    """Map a seed to a 2-D behavior descriptor in [0,1)^2 (sub-area, technique).
    A real version derives these from the statement's mathematical features."""
    h = abs(hash(seed))
    return ((h % 97) / 97.0, ((h // 97) % 89) / 89.0)


def _signature(prop: Propositio) -> ClaimSignature:
    assert prop.expressio is not None
    en = prop.enuntiatio
    return ClaimSignature(
        claim_type=en.claim_type,
        subject=en.statement.split()[0].lower() if en.statement else "unknown",
        relation=en.claim_type.value,
        formal_hash=prop.expressio.normalized_hash,
    )

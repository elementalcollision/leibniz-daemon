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

import json
from dataclasses import dataclass
from typing import Optional

from leibniz.adapters import LeonardoAdapter, ProviderAdapter
from leibniz.imports import resolve_imports
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
    max_repairs: int = 0  # R4.2: autoformalizer import/statement repair attempts

    def run(self, prop: Propositio) -> Optional[Propositio]:
        draft = self.provider.propose(Role.FORMALIZE, prop.enuntiatio.statement)
        expr = _parse_expressio(draft)
        expr, compiled = _compile_with_repair(
            self.provider, self.lean, prop.enuntiatio.statement, expr, self.max_repairs
        )
        if not compiled:
            prop.quarantine(FinishReason.MALFORMED)
            return None
        expr.compiles = True
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


def _compile_with_repair(provider, lean, statement: str, expr: Expressio, max_repairs: int):
    """Compile the statement; on failure first try a cheap MECHANICAL import-repair
    (ADR 0012 — validate/repair imports against the real Mathlib index), then hand
    the Lean error back to the autoformalizer to fix imports/statement (R4.2). Falls
    back to a single plain compile when the backend/provider lack the repair hooks
    (the demo's fakes), so existing behavior is unchanged. Returns (expr, ok)."""
    compile_fn = getattr(getattr(lean, "backend", None), "compile_with_error", None)
    if compile_fn is None:
        return expr, lean.validate_statement(expr)
    repair_fn = getattr(provider, "repair_formalization", None)
    ok, err = compile_fn(expr)
    if not ok:  # ADR 0012: mechanical import-resolve before the costlier LLM repair
        resolved = tuple(resolve_imports(list(expr.imports)))
        if resolved != tuple(expr.imports):
            expr = Expressio(
                theorem_src=expr.theorem_src,
                imports=resolved,
                established_domain=expr.established_domain,
            )
            ok, err = compile_fn(expr)
    attempts = 0
    while not ok and repair_fn is not None and attempts < max_repairs:
        attempts += 1
        try:
            fixed = repair_fn(statement, expr.theorem_src, err)
        except Exception:
            break
        new_expr = _parse_expressio(fixed)
        if not new_expr.theorem_src or new_expr.theorem_src.strip() == expr.theorem_src.strip():
            break  # no useful change -> stop
        expr = new_expr
        ok, err = compile_fn(expr)
    return expr, ok


def _maybe_json(draft: str) -> Optional[dict]:
    """Parse a provider's JSON proposal (ADR 0005). Returns None for non-JSON drafts
    (the fakes / prose), so parsing degrades safely to the stub path."""
    try:
        data = json.loads(draft)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def _claim_type(name: Optional[str]) -> ClaimType:
    if name:
        try:
            return ClaimType(name)
        except ValueError:
            pass
    return ClaimType.COMPLEXITY_BOUND


def _parse_enuntiatio(draft: str, seed: str) -> Enuntiatio:
    data = _maybe_json(draft)
    if data and data.get("statement"):
        stmt = str(data["statement"])
        return Enuntiatio(
            statement=stmt,
            claim_type=_claim_type(data.get("claim_type")),
            falsifiable_claim=str(data.get("falsifiable_claim") or f"exists input violating: {stmt}"),
            claim_domain=data.get("claim_domain"),
            claim_property=data.get("claim_property"),
        )
    return Enuntiatio(
        statement=draft.strip() or seed,
        claim_type=ClaimType.COMPLEXITY_BOUND,
        falsifiable_claim=f"exists input violating: {draft.strip() or seed}",
    )


def _parse_expressio(draft: str) -> Expressio:
    data = _maybe_json(draft)
    if data and data.get("theorem_src"):
        imports = data.get("imports")
        return Expressio(
            theorem_src=str(data["theorem_src"]),
            imports=tuple(imports) if isinstance(imports, list) else ("Mathlib",),
            established_domain=data.get("established_domain"),
        )
    return Expressio(theorem_src=draft)


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

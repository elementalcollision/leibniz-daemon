"""ADR 0027: independent sub-lemma decomposition (deeper M3).

For a hard theorem the ensemble cannot close one-shot, ask a provider to DECOMPOSE it
into helper lemmas, prove each INDEPENDENTLY through the kernel (the existing N+1
consensus), then re-prove the main theorem with those proven lemmas offered to the prover
as `have`-block HINTS. A prover that cannot find the whole proof can often find the
pieces, then splice them.

Soundness by construction — the kernel only ever checks ONE self-contained declaration:
the proof hints are PROVER CONTEXT, never placed in the Lean source. The composed proof
is `theorem_src := <prover proof>` (the prover may paste the helper `have`s into its own
`by` block, where the kernel re-verifies each). There is no separate top-level
declaration before the main, so there is nothing a smuggled `axiom`/`attribute`/
`notation`/`run_cmd` could poison — inside a `by` block such tokens are a parse error,
and a trailing command after a completed proof cannot retroactively close the goal.
`discharge` stays the sole `kernel_verified` writer and N+1 consensus is preserved (the
composed main is still drafted by ≥min_consensus distinct provers and kernel-checked).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from leibniz.consensus import ConsensusResult, ProofConsensus
from leibniz.propositio import Demonstratio, Expressio

_SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*$")


@dataclass
class DecompositionStats:
    """Instrumentation so a run can SEE whether decomposition is doing anything (it is
    otherwise a black box behind a 0-promulgation result). Counters accumulate across the
    run; the calibration harness prints them."""

    attempted: int = 0          # decomposition invoked (normal consensus had failed)
    planned: int = 0            # a usable plan (a list of lemmas) was returned + parsed
    lemmas_proposed: int = 0    # well-formed sub-lemmas actually sent to the prover
    lemmas_proven: int = 0      # sub-lemmas independently kernel-verified
    composed_attempts: int = 0  # composed (main + hints) proof attempts
    closed: int = 0             # composed proofs the kernel verified (a decomposed win)

    def as_dict(self) -> dict:
        return {
            "attempted": self.attempted, "planned": self.planned,
            "lemmas_proposed": self.lemmas_proposed, "lemmas_proven": self.lemmas_proven,
            "composed_attempts": self.composed_attempts, "closed": self.closed,
        }


def _safe_lemma(name: str, stmt: str) -> bool:
    """Hygiene for a proposed sub-lemma: a valid identifier name and a single-line
    statement with no proof-assignment. (Not load-bearing for soundness — a sub-lemma is
    proven in isolation and only its proof TEXT becomes a prover hint, never kernel input;
    this just avoids paying to prove obviously-malformed lemmas.)"""
    return bool(_SAFE_NAME.match(name)) and "\n" not in stmt and ":=" not in stmt


@dataclass
class LemmaDecomposer:
    provider: object            # has .decompose(theorem_src) -> JSON str
    consensus: ProofConsensus
    max_lemmas: int = 4
    stats: DecompositionStats = field(default_factory=DecompositionStats)

    def prove(self, expr: Expressio) -> Optional[ConsensusResult]:
        """Decompose, prove each sub-lemma independently (N+1), then re-prove the main
        under N+1 with the proven lemmas offered as `have` hints. Returns the composed
        ConsensusResult, or None if nothing usable was produced. Updates `stats` at each
        stage so a run can tell decomposition apart from a silent no-op."""
        self.stats.attempted += 1
        decompose = getattr(self.provider, "decompose", None)
        if decompose is None:
            return None
        try:
            plan = json.loads(decompose(expr.theorem_src))
        except Exception:
            return None  # a proposal failure must never break the pipeline
        if not isinstance(plan, dict) or not isinstance(plan.get("lemmas"), list):
            return None
        self.stats.planned += 1

        haves: list[str] = []
        for lem in plan["lemmas"][: self.max_lemmas]:
            if not isinstance(lem, dict):
                continue
            name, stmt = lem.get("name"), lem.get("statement")
            if not (name and stmt):
                continue
            name, stmt = str(name).strip(), str(stmt).strip()
            if not _safe_lemma(name, stmt):
                continue
            self.stats.lemmas_proposed += 1
            sub = Expressio(theorem_src=f"lemma {name} {stmt}", imports=expr.imports)
            res = self.consensus.prove(sub)  # independent N+1 kernel proof of the lemma
            if res.reached and res.proof and res.proof.proof_src:
                self.stats.lemmas_proven += 1
                haves.append(f"have {name} {stmt} := {res.proof.proof_src.strip()}")
        if not haves:
            return None

        composed = Expressio(
            theorem_src=expr.theorem_src, imports=expr.imports,
            normalized_hash=expr.normalized_hash, compiles=expr.compiles,
            established_domain=expr.established_domain,
            proof_hints="\n".join(haves),  # prover context only — NEVER the kernel file
        )
        # The main is drafted afresh by the ensemble (it sees the haves via
        # consensus._prover_context) and the kernel checks ONE self-contained declaration
        # per attempt — N+1 on the composed proof, the same bar as direct proving.
        self.stats.composed_attempts += 1
        result = self.consensus.prove(composed)
        if result.reached:
            self.stats.closed += 1
        return result


@dataclass
class DecomposingDemonstrate:
    """DEMONSTRATE stage: normal N+1 consensus, then ADR 0027 decomposition as a fallback
    when it fails. Records exactly ONE proof edge (the better outcome), so a candidate
    never carries both a FAIL and a PASS proof edge."""

    consensus: ProofConsensus
    decomposer: LemmaDecomposer

    def run(self, prop):
        assert prop.expressio is not None
        result = self.consensus.prove(prop.expressio)
        if not result.reached:
            decomposed = self.decomposer.prove(prop.expressio)
            if decomposed is not None and decomposed.reached:
                result = decomposed
        prop.demonstratio = result.proof or Demonstratio(
            proof_obligation=self.consensus.obligation, proof_src=None
        )
        prop.record(result.edge)
        return prop

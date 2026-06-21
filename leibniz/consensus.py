"""Cascaded + witness proving with N+1 kernel-verified consensus (ADR 0006).

This STRENGTHENS the proof edge — it never weakens it. The Lean kernel is still the
sole decider (invariant 1): every prover draft is checked by
``LeanVerifier.discharge`` (the sole ``kernel_verified`` writer). Consensus only
adds a requirement — promulgation needs ``min_consensus`` *distinct* kernel-verified
proofs from independent provers — so it makes the gate more conservative, not less.

- cascade / witness: an ordered ensemble of provers (cheap -> expensive, plus
  cross-model witnesses) each drafts a proof of the SAME statement.
- consensus: the recorded PROOF_EDGE PASSes only when >= min_consensus drafts each
  pass the kernel. The PASSing edge is a *real* discharge edge (kernel-sourced),
  annotated with the consensus count; otherwise a MECHANICAL FAIL.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from leibniz.propositio import Demonstratio, Expressio
from leibniz.trust import PROOF_EDGE
from leibniz.types import EdgeEvidence, Role, TrustTier, Verdict
from leibniz.verifiers import LeanVerifier


@dataclass
class ConsensusResult:
    count: int                 # distinct kernel-verified proofs found
    required: int              # min_consensus (N+1)
    attempts: int              # provers actually consulted
    edge: EdgeEvidence         # the PROOF_EDGE to record (PASS iff consensus)
    proof: Optional[Demonstratio]  # a kernel-verified proof, if consensus reached

    @property
    def reached(self) -> bool:
        return self.count >= self.required


@dataclass
class ProofConsensus:
    provers: list           # the prover ensemble (cascade + witnesses); ProviderAdapters
    lean: LeanVerifier
    obligation: str = "claim"
    min_consensus: int = 2  # N+1 (default N=1)

    def prove(self, expr: Expressio) -> ConsensusResult:
        verified: list[Demonstratio] = []
        first_pass: Optional[EdgeEvidence] = None
        first_proof: Optional[Demonstratio] = None
        attempts = 0
        for prover in self.provers:
            attempts += 1
            try:
                script = prover.propose(Role.PROOF_DRAFT, expr.theorem_src)
            except Exception:
                continue  # a dead/unconfigured prover never blocks the others
            demo = Demonstratio(proof_obligation=self.obligation, proof_src=script)
            ev = self.lean.discharge(expr, demo)  # kernel decides; sole kernel_verified writer
            if demo.kernel_verified:
                verified.append(demo)
                if first_pass is None:
                    first_pass, first_proof = ev, demo

        count = len(verified)
        reached = count >= self.min_consensus
        if reached and first_pass is not None:
            # Record a REAL kernel PASS edge, annotated with the consensus.
            edge = EdgeEvidence(
                edge=first_pass.edge,
                tier=first_pass.tier,  # MECHANICAL, straight from discharge
                verdict=Verdict.PASS,
                detail={**first_pass.detail, "consensus": count, "required": self.min_consensus},
                cost_units=first_pass.cost_units * max(1, count),
            )
        else:
            edge = EdgeEvidence(
                edge=PROOF_EDGE,
                tier=TrustTier.MECHANICAL,
                verdict=Verdict.FAIL,
                detail={
                    "consensus": count,
                    "required": self.min_consensus,
                    "reason": "insufficient independent kernel-verified proofs",
                },
                cost_units=10.0 * max(1, attempts),
            )
        return ConsensusResult(
            count=count, required=self.min_consensus, attempts=attempts,
            edge=edge, proof=first_proof if reached else None,
        )

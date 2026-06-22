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


def normalize_proof(text: str) -> str:
    """Normalize a prover's raw output into a usable proof body (ADR 0012): strip
    markdown fences and any leading *restated* `theorem … :=` so the result starts
    at the tactic/term. `_join_proof` then attaches it to the real statement, so a
    correct proof isn't rejected on formatting."""
    s = (text or "").strip()
    if "```" in s:
        body = s.split("```", 1)[1].split("```", 1)[0]
        if "\n" in body:  # drop a leading ```lean / ``` language-tag line
            head, rest = body.split("\n", 1)
            if head.strip() == "" or head.strip().isalpha():
                body = rest
        s = body.strip()
    cut = s.find(":=")
    if cut != -1 and s[:cut].lstrip().startswith(("theorem", "lemma", "example")):
        s = s[cut + 2:].strip()
    return s


def _prover_identity(prover) -> str:
    """A stable identity for consensus de-duplication: a model is ONE independent voter
    however many proof STRATEGIES it runs. Unwrap strategy wrappers (e.g. the ADR 0024
    DecompositionProver, which only reshapes the prompt) to the underlying base, then key
    on the model name; fall back to object identity for adapters without a model (test
    doubles / hosted clients)."""
    seen: set[int] = set()
    while True:
        base = getattr(prover, "base", None)
        if base is None or id(prover) in seen:
            break
        seen.add(id(prover))  # guard against a pathological self-referential wrapper
        prover = base
    model = getattr(prover, "model", None)
    return f"model:{model}" if model else f"obj:{id(prover)}"


@dataclass
class ConsensusResult:
    count: int                 # distinct prover identities (models) with a kernel proof
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
    max_workers: int = 4    # ADR 0011: run the ensemble concurrently (I/O-bound)

    def _attempt(self, prover, expr: Expressio):
        """Draft + kernel-check one prover. Returns (demo, edge) if kernel-verified,
        else None. discharge stays the sole kernel_verified writer; each attempt is
        independent (stateless docker run per check), so this is thread-safe."""
        try:
            script = normalize_proof(prover.propose(Role.PROOF_DRAFT, expr.theorem_src))
        except Exception:
            return None  # a dead/unconfigured prover never blocks the others
        demo = Demonstratio(proof_obligation=self.obligation, proof_src=script)
        ev = self.lean.discharge(expr, demo)
        return (demo, ev) if demo.kernel_verified else None

    def prove(self, expr: Expressio) -> ConsensusResult:
        attempts = len(self.provers)
        if self.max_workers and attempts > 1:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(self.max_workers, attempts)) as ex:
                results = list(ex.map(lambda p: self._attempt(p, expr), self.provers))
        else:
            results = [self._attempt(p, expr) for p in self.provers]

        # Deterministic order (input order) -> stable "first" verified proof.
        verified = [(p, r) for p, r in zip(self.provers, results) if r is not None]
        # Count DISTINCT prover identities (models), NOT raw passing attempts: N+1
        # consensus is about INDEPENDENT provers (ADR 0006/0024 review). A model that
        # proves the goal by two strategies (e.g. one-shot + decomposition) is ONE voter,
        # so a single model can never self-satisfy the threshold.
        count = len({_prover_identity(p) for p, _ in verified})
        first_proof, first_pass = (verified[0][1][0], verified[0][1][1]) if verified else (None, None)
        reached = count >= self.min_consensus
        if reached and first_pass is not None:
            # Record a REAL kernel PASS edge, annotated with the consensus.
            edge = EdgeEvidence(
                edge=first_pass.edge,
                tier=first_pass.tier,  # MECHANICAL, straight from discharge
                verdict=Verdict.PASS,
                detail={**first_pass.detail, "consensus": count, "required": self.min_consensus},
                cost_units=first_pass.cost_units * max(1, count),
                producer=first_pass.producer,  # ADR 0013: preserve kernel provenance
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


@dataclass
class NoOpDerive:
    """Production DERIVE stage. Proof drafting moves into ConsensusDemonstrate's
    ensemble, so this only advances the survivor (its Expressio is already set)."""

    def run(self, prop):
        return prop


@dataclass
class ConsensusDemonstrate:
    """Production DEMONSTRATE stage: run the cascade/witness ensemble under N+1
    consensus, record the resulting PROOF_EDGE, and attach a kernel-verified proof
    when consensus is reached (else an unverified Demonstratio for the record)."""

    consensus: ProofConsensus

    def run(self, prop):
        assert prop.expressio is not None
        result = self.consensus.prove(prop.expressio)
        prop.demonstratio = result.proof or Demonstratio(
            proof_obligation=self.consensus.obligation, proof_src=None
        )
        prop.record(result.edge)
        return prop

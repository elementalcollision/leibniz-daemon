"""Agentic proof repair — a bounded draft → kernel-error → repair loop (ADR 0029).

Lever 3, option C. The measured bottleneck is prover REACH on non-trivial goals: the
ensemble drafts a proof, the kernel rejects it, and that is the end. The repair loop
turns that single shot into a conversation — it feeds the kernel's actual complaint back
to a frontier reasoner and lets it try again, a few bounded rounds. (HILBERT/LEAP report
the scaffold, not the raw model, is what closes goals; our own measurement agreed —
Aristotle, an agentic prover, closed goals a stronger raw model did not.)

Trust boundary — UNCHANGED (CLAUDE.md invariants 1, 2, 7):
- The reasoner only PROPOSES. ``LeanVerifier.discharge`` remains the SOLE writer of
  ``kernel_verified``; the loop calls it for the official stamp. The loop's own
  ``check_proof_with_error`` calls are advisory — they surface the error to repair against;
  discharge re-checks any candidate before it is stamped.
- N+1 consensus is PRESERVED, not bypassed. Repair runs only when the normal ensemble
  comes up short, and the repaired proof counts as exactly ONE more *distinct* prover
  identity. It can promulgate only if the base ensemble's distinct verified identities
  PLUS the repair identity reach ``min_consensus``. A single repaired proof never
  self-satisfies an N>=1 threshold. (At ``min_consensus == 1`` the operator has opted into
  single-proof promulgation, exactly as for any single prover.)
- The statement is fixed. ``repair_proof`` is prompted to change only the PROOF, never the
  theorem; and even if it tried, the kernel checks ``theorem_src := proof`` — a repaired
  body that "proves" a different claim simply fails to elaborate against the real header.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from leibniz.consensus import ProofConsensus, normalize_proof
from leibniz.propositio import Demonstratio, Expressio
from leibniz.types import EdgeEvidence, Role, Verdict
from leibniz.verifiers import LeanVerifier


@dataclass
class RepairStats:
    """Instrumentation for measuring the lever (ADR 0029 validation plan). Counts are
    advisory telemetry only; they never touch a verdict."""

    attempted: int = 0          # goals the repair loop was invoked on
    closed: int = 0             # goals it kernel-closed (a discharge PASS)
    repairs: int = 0            # repair rounds spent (excludes the initial draft)
    promulgated: int = 0        # goals where repair supplied the deciding consensus vote
    rounds_to_close: list = field(default_factory=list)  # round index each close happened at

    def as_dict(self) -> dict:
        return {
            "attempted": self.attempted,
            "closed": self.closed,
            "repairs": self.repairs,
            "promulgated": self.promulgated,
            "rounds_to_close": list(self.rounds_to_close),
        }


@dataclass
class ProofRepairer:
    """Draft a proof with a frontier reasoner, then repair it against the kernel's error
    for a few bounded rounds. Returns a kernel-verified (demo, edge) or None.

    ``provider`` must expose ``propose(Role.PROOF_DRAFT, ctx)`` and
    ``repair_proof(theorem_src, failed_proof, error)`` (AnthropicProvider). ``lean.backend``
    must expose ``check_proof_with_error`` (LeanReplBackend / LeanCliBackend); if it does
    not, the loop is a safe no-op (returns None)."""

    provider: object
    lean: LeanVerifier
    obligation: str = "claim"
    max_rounds: int = 2     # repair rounds AFTER the initial draft
    identity: str = "repair:anthropic"   # distinct consensus identity for this scaffold
    stats: RepairStats = field(default_factory=RepairStats)

    def prove(self, expr: Expressio) -> Optional[tuple[Demonstratio, EdgeEvidence]]:
        check = getattr(self.lean.backend, "check_proof_with_error", None)
        if check is None:
            return None  # backend can't surface errors -> repair is a no-op, never blocks
        self.stats.attempted += 1
        try:
            candidate = normalize_proof(self.provider.propose(Role.PROOF_DRAFT, expr.theorem_src))
        except Exception:
            return None
        for r in range(self.max_rounds + 1):
            if not candidate:
                break
            ok, error = check(expr, candidate)
            if ok:
                # Official kernel_verified write. discharge re-checks the SAME candidate
                # against the SAME backend and is the sole writer of the stamp.
                demo = Demonstratio(proof_obligation=self.obligation, proof_src=candidate)
                ev = self.lean.discharge(expr, demo)
                if demo.kernel_verified:
                    self.stats.closed += 1
                    self.stats.rounds_to_close.append(r)
                    return (demo, ev)
                error = "kernel rejected a proof the pre-check accepted"  # defensive; retry
            if r == self.max_rounds:
                break
            self.stats.repairs += 1
            try:
                candidate = normalize_proof(
                    self.provider.repair_proof(expr.theorem_src, candidate, error)
                )
            except Exception:
                break
        return None


@dataclass
class RepairingDemonstrate:
    """DEMONSTRATE stage that adds an agentic repair fallback (ADR 0029).

    The fallback ladder, recording exactly ONE proof edge (so a candidate never carries
    both a FAIL and a PASS proof edge):

        N+1 consensus  ->  (optional) ADR 0027 decomposition  ->  ADR 0029 repair

    It composes at the ``ConsensusResult`` level — neither ``consensus.prove`` nor
    ``decomposer.prove`` records an edge — so layering repair on top of decomposition adds
    no double-recording. When ``decomposer`` is None this is just consensus -> repair.

    N+1 is preserved: repair runs only when the prior stages came up SHORT, and the
    repaired proof counts as exactly ONE more *distinct* prover identity (``repairer.identity``,
    which never collides with a base prover's ``model:``/``obj:`` identity). It promulgates
    only if ``carried_distinct_count + 1 >= min_consensus`` — so at the default N+1=2 the
    base ensemble must already have ONE distinct kernel proof for repair to supply the
    second; a lone repaired proof never self-satisfies."""

    consensus: ProofConsensus
    repairer: ProofRepairer
    decomposer: object = None   # optional LemmaDecomposer (ADR 0027); .prove(expr)->ConsensusResult|None

    def run(self, prop):
        assert prop.expressio is not None
        result = self.consensus.prove(prop.expressio)
        if not result.reached and self.decomposer is not None:
            decomposed = self.decomposer.prove(prop.expressio)
            if decomposed is not None and decomposed.reached:
                result = decomposed
        if result.reached:
            prop.demonstratio = result.proof
            prop.record(result.edge)
            return prop

        repaired = self.repairer.prove(prop.expressio)
        if repaired is not None:
            demo, ev = repaired
            combined = set(result.identities) | {self.repairer.identity}
            if len(combined) >= self.consensus.min_consensus:
                self.repairer.stats.promulgated += 1
                edge = EdgeEvidence(
                    edge=ev.edge,
                    tier=ev.tier,            # MECHANICAL, straight from discharge
                    verdict=Verdict.PASS,
                    detail={**ev.detail, "consensus": len(combined),
                            "required": self.consensus.min_consensus, "via": "repair"},
                    cost_units=ev.cost_units * max(1, len(combined)),
                    producer=ev.producer,    # ADR 0013: preserve kernel provenance
                )
                prop.demonstratio = demo     # kernel-verified; attached only when promulgating
                prop.record(edge)
                return prop

        # No promulgation: record the prior (short) result. A repaired-but-not-promulgated
        # proof is captured in repairer.stats (measurement), but is NOT attached as a
        # verified demonstratio — the recorded FAIL edge is what the gate reads.
        prop.demonstratio = result.proof or Demonstratio(
            proof_obligation=self.consensus.obligation, proof_src=None
        )
        prop.record(result.edge)
        return prop

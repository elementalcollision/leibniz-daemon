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


def _canonical_model(s: str) -> str:
    """Canonicalize a prover identity / model id for N+1 distinctness (ADR 0024/0029).

    The repair scaffold around model M is just "M trying harder with kernel feedback" — a
    STRATEGY, so per ADR 0024 it is the SAME voter as a base prover running M, NOT a second
    independent one. To dedupe across access paths (e.g. opus via Anthropic `claude-opus-4-8`
    vs via OpenRouter `anthropic/claude-opus-4-8`), reduce to the bare model name. Non-model
    identities (`obj:`/`repair:` with no resolved model) are kept verbatim, so they stay
    distinct. Over-merging (two vendors sharing a bare name) is CONSERVATIVE — it can only
    make consensus harder, never weaker."""
    s = (s or "").strip()
    if s.startswith("model:"):
        s = s[len("model:"):]
    if s.startswith(("obj:", "repair:")):
        return s
    return s.rsplit("/", 1)[-1].lower()


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
    identity: str = "repair:frontier"   # fallback consensus identity when no model resolves
    stats: RepairStats = field(default_factory=RepairStats)
    last_model: Optional[str] = None     # model that produced the most recent verified proof

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
                    # Record WHICH model actually produced this proof (failover may have
                    # used a backup), so consensus can dedupe it against same-model base
                    # provers — ADR 0024: one model is one voter, however it proves.
                    self.last_model = (getattr(self.provider, "last_used", None)
                                       or getattr(self.provider, "model", None))
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

    N+1 is preserved. Repair runs only when the prior stages came up SHORT. The repair
    PANEL (ADR 0029 v2) is `[repairer, *panel]` — independent reasoners, each running its own
    draft→repair loop. A panel member's proof counts as one more *distinct* prover identity
    ONLY IF the model that produced it is not already a base verifier or an earlier panel
    closer (ADR 0024: one model, one voter — deduped by canonical model name). It promulgates
    only if ``len(distinct base verifiers) + len(distinct panel closers) >= min_consensus`` —
    so a single reasoner repairing what base-opus already drafted adds nothing, while two
    DISTINCT panel reasoners both closing the goal can satisfy N+1 on their own (each kernel-
    verified via `discharge`). A lone repaired proof never self-satisfies at N+1=2. With an
    empty panel this is exactly the single-reasoner v1 behaviour."""

    consensus: ProofConsensus
    repairer: ProofRepairer
    panel: tuple = ()           # ADR 0029 v2: additional DISTINCT-model repairers (independent votes)
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

        # Repair panel: run each independent reasoner until enough DISTINCT models have a
        # kernel-verified proof of THIS goal to satisfy N+1 (early-exit bounds the spend).
        min_c = self.consensus.min_consensus
        base_canon = {_canonical_model(i) for i in result.identities}
        closers: dict[str, tuple] = {}   # canonical model -> (demo, ev); deduped vs base + each other
        for r in (self.repairer, *self.panel):
            if len(base_canon) + len(closers) >= min_c:
                break
            out = r.prove(prop.expressio)
            if out is None:
                continue
            demo, ev = out
            model = _canonical_model(getattr(r, "last_model", None) or r.identity)
            if model in base_canon or model in closers:
                continue        # same model as a base verifier / earlier closer -> not a new vote
            closers[model] = (demo, ev)
        distinct = len(base_canon) + len(closers)
        if closers and distinct >= min_c:
            self.repairer.stats.promulgated += 1
            demo, ev = next(iter(closers.values()))   # attach one kernel-verified proof
            edge = EdgeEvidence(
                edge=ev.edge,
                tier=ev.tier,            # MECHANICAL, straight from discharge
                verdict=Verdict.PASS,
                detail={**ev.detail, "consensus": distinct,
                        "required": min_c, "via": "repair",
                        "repair_models": sorted(closers)},
                cost_units=ev.cost_units * max(1, distinct),
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

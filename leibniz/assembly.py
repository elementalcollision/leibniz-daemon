"""Production assembly (R4 exit test) — wire the REAL backends into a live daemon.

`demo.py` wires deterministic fakes; this wires the real stack:
- Lean 4.31 kernel (OrbStack container) + Z3 gaming-witness,
- structural-hash novelty corpus,
- Anthropic (Claude) for CONJECTURE/FORMALIZE,
- an OpenRouter prover ensemble with N+1 kernel-verified consensus (ADR 0006),
- Leonardo analogies + curated frontier (ADR 0007),
- the judged-faithfulness budget (ADR 0001 §5).

Nothing here decides — the kernel and the mechanical gates do (ADR 0001). The
provers/conjecturers only propose. Credentials come from the environment; call
`leibniz.env.load_env()` at the entrypoint before `build_daemon()`. `build_daemon`
itself makes NO network calls — it only constructs.
"""
from __future__ import annotations

import os

from leibniz.backends.lean_cli import LeanCliBackend
from leibniz.backends.smt_z3 import Z3Backend
from leibniz.budget import TrustBudget
from leibniz.consensus import ConsensusDemonstrate, NoOpDerive, ProofConsensus
from leibniz.corpus import CorpusBackend
from leibniz.daemon import Leibniz
from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.gates.novelty import NoveltyGate
from leibniz.gates.verification import VerificationGate
from leibniz.leonardo import LeonardoForgeAdapter
from leibniz.pipeline import Conjecture, Formalize, Promulgate, Survey
from leibniz.probes import default_probes
from leibniz.providers.anthropic_provider import AnthropicProvider
from leibniz.providers.openrouter_provider import OpenRouterProvider
from leibniz.selection import KFM, Archive
from leibniz.trust import TrustPolicy
from leibniz.verifiers import LeanVerifier, SMTVerifier


class SimpleRuntime:
    """Minimal in-memory RuntimeAdapter. (Chimera integration is a separate seam.)"""

    def __init__(self) -> None:
        self.memory: list = []

    def now_phase(self) -> str:
        return "WAKE"

    def remember(self, prop) -> None:
        self.memory.append(prop)

    def recall_recent(self, n: int) -> list:
        return self.memory[-n:]

    def witness(self, prompt: str, n_models: int) -> list[str]:
        return []


class ConservativeJudge:
    """OPEN_FORM faithfulness judge that refuses by default. We do not rely on a
    judge for autonomous promulgation; measurable claims go through the mechanical
    probe/gaming-witness, and OPEN_FORM falls back to DEFER/FAIL rather than a
    capricious pass."""

    def round_trip_agrees(self, prop) -> float:
        return 0.0


def prover_ensemble() -> list[OpenRouterProvider]:
    """The cascade + witnesses from LEIBNIZ_PROVER_MODELS (OpenRouter model ids)."""
    models = [m.strip() for m in os.environ.get("LEIBNIZ_PROVER_MODELS", "").split(",") if m.strip()]
    return [OpenRouterProvider(model=m) for m in models]


def build_daemon(*, frontier_limit: int = 2, analogy_limit: int = 1) -> Leibniz:
    """Assemble the real daemon. Makes no network calls; configure creds via env
    (load_env() first). frontier/analogy limits bound how many seeds a cycle runs."""
    lean = LeanVerifier(LeanCliBackend())
    smt = SMTVerifier(Z3Backend())
    novelty = NoveltyGate(CorpusBackend.from_json(), lean)
    faithfulness = FaithfulnessGate(smt=smt, probes=default_probes(smt), judge=ConservativeJudge())

    autoformalizer = AnthropicProvider(
        model=os.environ.get("LEIBNIZ_CONJECTURE_MODEL", "claude-opus-4-8")
    )
    consensus = ProofConsensus(
        provers=prover_ensemble(),
        lean=lean,
        min_consensus=int(os.environ.get("LEIBNIZ_PROOF_CONSENSUS", "2")),
    )
    policy = TrustPolicy()
    return Leibniz(
        runtime=SimpleRuntime(),
        survey=Survey(LeonardoForgeAdapter(max_seeds=frontier_limit, max_analogies=analogy_limit)),
        conjecture=Conjecture(autoformalizer),
        formalize=Formalize(autoformalizer, lean, smt, novelty, faithfulness, max_repairs=2),
        derive=NoOpDerive(),
        demonstrate=ConsensusDemonstrate(consensus),
        promulgate=Promulgate(),
        verification=VerificationGate(policy),
        kfm=KFM(Archive()),
        budget=TrustBudget(policy),
    )

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

from leibniz.backends import lean_repl
from leibniz.backends.lean_cli import LeanCliBackend
from leibniz.backends.smt_z3 import Z3Backend
from leibniz.budget import TrustBudget
from leibniz.consensus import ConsensusDemonstrate, NoOpDerive, ProofConsensus
from leibniz.corpus import CorpusBackend
from leibniz.cost import CostBudget
from leibniz.daemon import Leibniz
from leibniz.discovery import (
    _DEFAULT_FRONTIER,
    _DEFAULT_NOTEBOOK,
    DiscoveryNotebook,
    FrontierController,
)
from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.gates.novelty import NoveltyGate
from leibniz.gates.verification import VerificationGate
from leibniz.leonardo import LeonardoForgeAdapter
from leibniz.pipeline import Conjecture, Formalize, Promulgate, Survey
from leibniz.probes import default_probes
from leibniz.providers.anthropic_provider import AnthropicProvider
from leibniz.providers.huggingface_provider import HuggingFaceProvider
from leibniz.providers.openrouter_provider import OpenRouterProvider
from leibniz.runtime import PersistentRuntime
from leibniz.selection import KFM, Archive
from leibniz.trust import TrustPolicy
from leibniz.verifiers import LeanVerifier, SMTVerifier


class SimpleRuntime:
    """Minimal in-memory RuntimeAdapter for the demo/fakes. The real assembly uses
    `leibniz.runtime.PersistentRuntime` (ADR 0016); full external-Chimera wiring is
    still a drop-in behind the same Protocol."""

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


def _env_int(name: str, default: int) -> int:
    """Read an int env knob, falling back to `default` on absent/blank/garbage rather
    than aborting assembly on an operator typo (ADR 0023 review)."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def prover_ensemble(meter: object | None = None) -> list:
    """The prover cascade + witnesses for N+1 consensus. HuggingFace
    (`LEIBNIZ_HF_PROVER_MODELS`) is preferred — the specialized prover models
    (DeepSeek-Prover-V2 / Goedel class) live there — else OpenRouter
    (`LEIBNIZ_PROVER_MODELS`). Each prover meters real token usage (ADR 0014)."""
    max_tok = int(os.environ.get("LEIBNIZ_PROVER_MAX_TOKENS", "2048") or 2048)  # proof-draft budget
    hf = [m.strip() for m in os.environ.get("LEIBNIZ_HF_PROVER_MODELS", "").split(",") if m.strip()]
    if hf:
        return [HuggingFaceProvider(model=m, meter=meter, max_tokens=max_tok) for m in hf]
    models = [m.strip() for m in os.environ.get("LEIBNIZ_PROVER_MODELS", "").split(",") if m.strip()]
    return [OpenRouterProvider(model=m, meter=meter, max_tokens=max_tok) for m in models]


def _proof_verifier(cli_lean: LeanVerifier) -> LeanVerifier:
    """The verifier the consensus ensemble discharges through (ADR 0011).

    Prefer the REPL backend — Mathlib loads once per import-set instead of once per
    check (~3x throughput on Mathlib checks), which matters because the ensemble
    issues many checks per cycle. Fall back to the CLI verifier when the REPL image
    is absent, or when the operator pins it off via LEIBNIZ_LEAN_REPL=0. Either way
    `LeanVerifier.discharge` is the sole kernel_verified writer (CLAUDE.md inv. 1)."""
    if os.environ.get("LEIBNIZ_LEAN_REPL", "1") != "0" and lean_repl.available():
        return LeanVerifier(lean_repl.LeanReplBackend())
    return cli_lean


def build_daemon(*, frontier_limit: int = 2, analogy_limit: int = 1) -> Leibniz:
    """Assemble the real daemon. Makes no network calls; configure creds via env
    (load_env() first). frontier/analogy limits bound how many seeds a cycle runs."""
    lean = LeanVerifier(LeanCliBackend())
    smt = SMTVerifier(Z3Backend())
    novelty = NoveltyGate(CorpusBackend.from_json(), lean)
    faithfulness = FaithfulnessGate(smt=smt, probes=default_probes(smt), judge=ConservativeJudge())

    # ADR 0014: one cost meter, wired into every provider so real token usage is
    # priced and the daemon's USD cap reflects actual spend (not a flat estimate).
    cost_budget = CostBudget.from_env()
    autoformalizer = AnthropicProvider(
        model=os.environ.get("LEIBNIZ_CONJECTURE_MODEL", "claude-opus-4-8"),
        meter=cost_budget,
    )
    consensus = ProofConsensus(
        provers=prover_ensemble(meter=cost_budget),
        lean=_proof_verifier(lean),  # ADR 0011: REPL (import-cached) when available
        min_consensus=int(os.environ.get("LEIBNIZ_PROOF_CONSENSUS", "2")),
    )
    policy = TrustPolicy()
    forge = LeonardoForgeAdapter(max_seeds=frontier_limit, max_analogies=analogy_limit)
    _frontier_path = os.environ.get("LEIBNIZ_FRONTIER_PATH") or str(_DEFAULT_FRONTIER)
    # ADR 0023 (lever 1): persist + accumulate near-misses, and raise weaken throughput
    # so the weaken-and-retry loop keeps grinding the UNPROVEN frontier toward a proof.
    _notebook_path = os.environ.get("LEIBNIZ_NOTEBOOK_PATH") or str(_DEFAULT_NOTEBOOK)
    _nb_cap = _env_int("LEIBNIZ_NOTEBOOK_CAP", 12)
    return Leibniz(
        runtime=PersistentRuntime(),  # ADR 0016: SQLite memory + circadian phase
        survey=Survey(forge),
        domains=tuple(forge.domains()),  # D9 (ADR 0015): rotate across all frontier domains
        conjecture=Conjecture(autoformalizer),
        formalize=Formalize(
            autoformalizer, lean, smt, novelty, faithfulness, max_repairs=2,
            # ADR 0022: steer the contract into the faithfulness DSL so candidates can
            # be certified and reach proof (proposal-side; the gate still decides).
            max_contract_repairs=int(os.environ.get("LEIBNIZ_CONTRACT_REPAIRS", "1") or 1),
        ),
        derive=NoOpDerive(),
        demonstrate=ConsensusDemonstrate(consensus),
        promulgate=Promulgate(),
        verification=VerificationGate(policy),
        kfm=KFM(Archive()),
        budget=TrustBudget(policy),
        cost_budget=cost_budget,  # ADR 0011 cap, ADR 0014 metered by real usage
        # ADR 0018: outcome-conditioned conjecture; ADR 0023: resumed from + persisted
        # to disk so near-misses accumulate across runs for weaken-and-retry.
        notebook=DiscoveryNotebook.load(_notebook_path, capacity=_nb_cap),
        notebook_path=_notebook_path,
        weaken_k=_env_int("LEIBNIZ_WEAKEN_K", 3),
        # ADR 0018/0019: adaptive difficulty band, resumed from + persisted to disk.
        frontier=FrontierController.load(_frontier_path),
        frontier_path=_frontier_path,
    )

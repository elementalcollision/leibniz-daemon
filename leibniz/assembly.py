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
    load_novelty_exemplars,
    novelty_exemplar_properties,
)
from leibniz.gates.faithfulness import FaithfulnessGate
from leibniz.gates.novelty import NoveltyGate
from leibniz.gates.verification import VerificationGate
from leibniz.instance_config import InstanceConfig, resolve_instance_config
from leibniz.lemma_decomposition import DecomposingDemonstrate, LemmaDecomposer
from leibniz.leonardo import LeonardoForgeAdapter
from leibniz.pipeline import Conjecture, Formalize, Promulgate, Survey
from leibniz.probes import default_probes
from leibniz.proof_repair import ProofRepairer, RepairingDemonstrate
from leibniz.providers import ProviderUnavailable
from leibniz.providers.anthropic_provider import AnthropicProvider
from leibniz.providers.aristotle_provider import AristotleProver
from leibniz.providers.decomposition_prover import DecompositionProver
from leibniz.providers.failover_provider import FailoverProvider
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


def _resolve_prover(spec: str, default_url: str, default_key_env: str,
                    meter: object | None, max_tok: int) -> OpenRouterProvider:
    """Resolve one `LEIBNIZ_PROVER_MODELS` entry into an OpenAI-compatible prover (ADR 0028).

    A bare `model` uses the default gateway (`LEIBNIZ_PROVER_BASE_URL` or OpenRouter). A
    `model@gateway` entry routes that ONE model through a named gateway profile:
    `LEIBNIZ_GATEWAY_<GATEWAY>_URL` (REQUIRED — fail closed if unset, so a typo never silently
    routes to the wrong endpoint) and `LEIBNIZ_GATEWAY_<GATEWAY>_KEY_ENV` (default
    `<GATEWAY>_API_KEY`). The LAST `@` is the gateway delimiter, so `@` is reserved in a prover
    spec (real OpenRouter/HF prover ids do not use it). The model NAME (sans `@gateway`) is what
    N+1 keys identity on, so a
    model reached via two gateways is still ONE voter — routing is a transport detail, never a
    trust-bar change; the Lean kernel still re-verifies every draft."""
    if "@" in spec:
        model, gateway = (s.strip() for s in spec.rsplit("@", 1))
        gw = gateway.upper()
        url = os.environ.get(f"LEIBNIZ_GATEWAY_{gw}_URL")
        if not url:
            raise ProviderUnavailable(
                f"prover {spec!r} routes to gateway {gateway!r}, but LEIBNIZ_GATEWAY_{gw}_URL "
                f"is not set (ADR 0028 per-model routing) — set it or drop the '@{gateway}'."
            )
        key_env = os.environ.get(f"LEIBNIZ_GATEWAY_{gw}_KEY_ENV") or f"{gw}_API_KEY"
    else:
        model, url, key_env = spec, default_url, default_key_env
    return OpenRouterProvider(model=model, meter=meter, max_tokens=max_tok,
                              url=url, api_key_env=key_env)


def prover_ensemble(meter: object | None = None) -> list:
    """The prover cascade + witnesses for N+1 consensus. HuggingFace
    (`LEIBNIZ_HF_PROVER_MODELS`) is preferred — the specialized prover models
    (DeepSeek-Prover-V2 / Goedel class) live there — else OpenRouter
    (`LEIBNIZ_PROVER_MODELS`). Each prover meters real token usage (ADR 0014).

    ADR 0024: also add `LEIBNIZ_DECOMPOSE` lemma-decomposition variants of the first
    base provers (default 1) — a distinct proving STRATEGY (structured `have`/`suffices`
    proofs) that closes goals one-shot drafts miss. The kernel still solely decides; each
    variant is just another independent attempt under N+1 consensus.

    Lever 3 knobs: the OpenAI-compatible path takes `LEIBNIZ_PROVER_BASE_URL` +
    `LEIBNIZ_PROVER_KEY_ENV` so a STRONGER open model (e.g. Goedel-Prover-V2 via
    Featherless or a self-hosted vLLM endpoint, harness A) drops in by config; and
    `LEIBNIZ_ARISTOTLE` appends the Harmonic Aristotle agent prover (ADR 0028). Both still
    only PROPOSE — our kernel re-verifies every draft under N+1 consensus.

    Per-model gateway routing (ADR 0028): a `LEIBNIZ_PROVER_MODELS` entry may be
    `model@gateway` to route THAT model through a named gateway, so the ensemble can SPAN
    gateways — e.g. `Goedel-LM/Goedel-Prover-V2-32B@featherless` on a flat-rate Featherless
    plan alongside DeepSeek + opus on OpenRouter. N+1 keys identity on the model NAME (sans
    `@gateway`), so the same model via two gateways is still ONE voter — routing never touches
    the trust bar."""
    max_tok = int(os.environ.get("LEIBNIZ_PROVER_MAX_TOKENS", "2048") or 2048)  # proof-draft budget
    hf = [m.strip() for m in os.environ.get("LEIBNIZ_HF_PROVER_MODELS", "").split(",") if m.strip()]
    if hf:
        base = [HuggingFaceProvider(model=m, meter=meter, max_tokens=max_tok) for m in hf]
    else:
        models = [m.strip() for m in os.environ.get("LEIBNIZ_PROVER_MODELS", "").split(",") if m.strip()]
        # Lever 3 / harness A: point the OpenAI-compatible client at any gateway (default
        # OpenRouter); per-model `model@gateway` entries override it for one model.
        base_url = os.environ.get("LEIBNIZ_PROVER_BASE_URL") or OpenRouterProvider.url
        key_env = os.environ.get("LEIBNIZ_PROVER_KEY_ENV") or "OPENROUTER_API_KEY"
        base = [_resolve_prover(m, base_url, key_env, meter, max_tok) for m in models]
    n_decomp = _env_int("LEIBNIZ_DECOMPOSE", 1)  # how many base provers to also run decomposed
    if n_decomp > 0 and base:
        base = base + [DecompositionProver(p) for p in base[:n_decomp]]
    if os.environ.get("LEIBNIZ_ARISTOTLE", "").strip() not in ("", "0"):  # ADR 0028 (lever 3)
        base = base + [AristotleProver(meter=meter)]
    return base


# The repair loop's frontier reasoner fails over to these OpenRouter-hosted backups when
# the Anthropic primary is unavailable (outage/overload). Override via LEIBNIZ_REASONER_FALLBACKS.
_DEFAULT_REASONER_FALLBACKS = "z-ai/glm-5.2,moonshotai/kimi-k2.6,openai/gpt-5.5"


def _reasoner_backups(meter: object | None = None) -> list:
    """OpenRouter-hosted frontier backups (default GLM/Kimi/GPT) for failover, ADR 0029.
    Empty unless OPENROUTER_API_KEY is set and LEIBNIZ_REASONER_FALLBACKS is non-empty — so
    failover is off by default and behaviour is identical to a single primary."""
    raw = os.environ.get("LEIBNIZ_REASONER_FALLBACKS", _DEFAULT_REASONER_FALLBACKS)
    models = [m.strip() for m in raw.split(",") if m.strip()]
    if not models or not os.environ.get("OPENROUTER_API_KEY"):
        return []
    max_tok = int(os.environ.get("LEIBNIZ_PROVER_MAX_TOKENS", "2048") or 2048)
    return [OpenRouterProvider(model=m, meter=meter, max_tokens=max_tok) for m in models]


def frontier_reasoner(primary: object, meter: object | None = None) -> object:
    """A frontier reasoner with failover for the proof roles (PROOF_DRAFT/repair_proof),
    ADR 0029. The Anthropic `primary` drafts/repairs; if a call errors (outage/overload) it
    fails over to OpenRouter-hosted backups in order. Returns the primary unchanged when no
    backups are configured. All PROPOSE only — the Lean kernel still decides every candidate."""
    backups = _reasoner_backups(meter)
    return FailoverProvider([primary, *backups]) if backups else primary


def autoformalizer_with_failover(primary: object, meter: object | None = None) -> object:
    """The CONJECTURE/FORMALIZE autoformalizer with failover to OpenRouter backups (ADR 0029).

    A *sustained* Anthropic overload crashed an organic run mid-cycle in the CONJECTURE role —
    the proof role already failed over, but the proposal side did not. This extends the same
    protection: the backups apply the SHARED autoformalize prompts (so they conjecture,
    formalize, repair contracts/imports, and decompose identically), and every call still only
    PROPOSES — the faithfulness/novelty gates and the Lean kernel decide. No backups configured
    -> the primary is returned unchanged."""
    backups = _reasoner_backups(meter)
    return FailoverProvider([primary, *backups]) if backups else primary


def _proof_verifier(cli_lean: LeanVerifier, repl_image: str | None = None) -> LeanVerifier:
    """The verifier the consensus ensemble discharges through (ADR 0011).

    Prefer the REPL backend — Mathlib loads once per import-set instead of once per
    check (~3x throughput on Mathlib checks), which matters because the ensemble
    issues many checks per cycle. Fall back to the CLI verifier when the REPL image
    is absent, or when the operator pins it off via LEIBNIZ_LEAN_REPL=0. Either way
    `LeanVerifier.discharge` is the sole kernel_verified writer (CLAUDE.md inv. 1).

    ADR 0033: the REPL image is pinned per instance (`repl_image`) so PROD/UAT run their
    resolved kernel; absent, the audited default."""
    image = repl_image or lean_repl.REPL_IMAGE
    if os.environ.get("LEIBNIZ_LEAN_REPL", "1") != "0" and lean_repl.available(image):
        return LeanVerifier(lean_repl.LeanReplBackend(image=image))
    return cli_lean


def build_daemon(
    *, frontier_limit: int = 2, analogy_limit: int = 1, config: InstanceConfig | None = None
) -> Leibniz:
    """Assemble the real daemon. Makes no network calls; configure creds via env
    (load_env() first). frontier/analogy limits bound how many seeds a cycle runs.

    ADR 0033: `config` pins the per-instance Lean image (CLI + REPL) and corpus; when None
    it is resolved from LEIBNIZ_INSTANCE (PROD pins the audited artifacts, UAT/dev may
    override). build_daemon stays construct-only — the run entrypoint records provenance via
    `instance_config.write_provenance`."""
    cfg = config or resolve_instance_config()
    lean = LeanVerifier(LeanCliBackend(image=cfg.lean_image))
    smt = SMTVerifier(Z3Backend())
    # ADR 0033: pin the corpus per instance (PROD: audited; UAT/dev: may override).
    novelty = NoveltyGate(CorpusBackend.from_json(cfg.corpus_path), lean)  # ADR 0031 L2 retracted; exact-hash novelty
    faithfulness = FaithfulnessGate(smt=smt, probes=default_probes(smt), judge=ConservativeJudge())

    # ADR 0014: one cost meter, wired into every provider so real token usage is
    # priced and the daemon's USD cap reflects actual spend (not a flat estimate).
    cost_budget = CostBudget.from_env()
    autoformalizer_primary = AnthropicProvider(
        model=os.environ.get("LEIBNIZ_CONJECTURE_MODEL", "claude-opus-4-8"),
        meter=cost_budget,
    )
    # ADR 0029: the proposal-side autoformalizer fails over to OpenRouter backups on a sustained
    # Anthropic overload (which previously crashed a run mid-cycle in CONJECTURE). The proof-role
    # repairer below wraps the BARE primary in its own frontier_reasoner, so failover never nests.
    autoformalizer = autoformalizer_with_failover(autoformalizer_primary, meter=cost_budget)
    consensus = ProofConsensus(
        provers=prover_ensemble(meter=cost_budget),
        lean=_proof_verifier(lean, repl_image=cfg.lean_repl_image),  # ADR 0011 REPL; ADR 0033 pinned
        min_consensus=int(os.environ.get("LEIBNIZ_PROOF_CONSENSUS", "2")),
    )
    # DEMONSTRATE fallback ladder: N+1 consensus -> (ADR 0027) decomposition -> (ADR 0029)
    # repair. Each layer is opt-in by env and records exactly one proof edge.
    # ADR 0027: when normal consensus fails, prove helper lemmas independently, then
    # re-prove the main with them offered as `have` hints (the kernel still checks one
    # self-contained declaration; hints never enter the Lean source).
    decomposer = (LemmaDecomposer(provider=autoformalizer, consensus=consensus)
                  if _env_int("LEIBNIZ_LEMMA_DECOMPOSE", 1) > 0 else None)
    # ADR 0029: when the prior layers still come up short, a frontier reasoner repairs a
    # draft against the kernel's actual error, a few bounded rounds. The repaired proof
    # counts as ONE more distinct prover under N+1 (it never lowers the consensus bar).
    if _env_int("LEIBNIZ_PROOF_REPAIR", 0) > 0:
        rounds = _env_int("LEIBNIZ_REPAIR_ROUNDS", 2)
        repairer = ProofRepairer(
            # frontier reasoner with failover to OpenRouter backups on an Anthropic outage
            # (ADR 0029); PROPOSES only — the kernel still decides every candidate. Wraps the
            # BARE primary (not the already-failover autoformalizer) so failover never nests.
            provider=frontier_reasoner(autoformalizer_primary, meter=cost_budget),
            lean=consensus.lean,            # discharge + check_proof_with_error via the ensemble's verifier
            obligation=consensus.obligation,
            max_rounds=rounds,
        )
        # ADR 0029 v2: a repair PANEL of additional DISTINCT-model reasoners (OpenRouter), so
        # repair can satisfy N+1 on its own when two independent models close the same goal.
        # Each is a distinct consensus identity; the canonical-model dedup prevents any overlap
        # with the primary/base from double-counting. Opt-in via LEIBNIZ_REPAIR_PANEL.
        panel_models = [m.strip() for m in os.environ.get("LEIBNIZ_REPAIR_PANEL", "").split(",") if m.strip()]
        panel = ()
        if panel_models and os.environ.get("OPENROUTER_API_KEY"):
            max_tok = int(os.environ.get("LEIBNIZ_PROVER_MAX_TOKENS", "2048") or 2048)
            panel = tuple(
                ProofRepairer(
                    provider=OpenRouterProvider(model=m, meter=cost_budget, max_tokens=max_tok),
                    lean=consensus.lean,
                    obligation=consensus.obligation,
                    max_rounds=rounds,
                    identity=f"repair:{m}",
                )
                for m in panel_models
            )
        demonstrate = RepairingDemonstrate(consensus, repairer, panel=panel, decomposer=decomposer)
    elif decomposer is not None:
        demonstrate = DecomposingDemonstrate(consensus, decomposer)
    else:
        demonstrate = ConsensusDemonstrate(consensus)
    policy = TrustPolicy()
    forge = LeonardoForgeAdapter(max_seeds=frontier_limit, max_analogies=analogy_limit)
    _frontier_path = os.environ.get("LEIBNIZ_FRONTIER_PATH") or str(_DEFAULT_FRONTIER)
    # ADR 0023 (lever 1): persist + accumulate near-misses, and raise weaken throughput
    # so the weaken-and-retry loop keeps grinding the UNPROVEN frontier toward a proof.
    _notebook_path = os.environ.get("LEIBNIZ_NOTEBOOK_PATH") or str(_DEFAULT_NOTEBOOK)
    _nb_cap = _env_int("LEIBNIZ_NOTEBOOK_CAP", 12)
    # ADR 0034 Stage 1: resume the outcome notebook, then load the curated novel-yet-elementary
    # FLAVOUR anchors into it (proposal-side context only; not persisted to the ledger).
    _notebook = DiscoveryNotebook.load(_notebook_path, capacity=_nb_cap)
    _notebook.exemplars = load_novelty_exemplars()
    # ADR 0034 Stage 2: opt-in empirical pattern miner (LEIBNIZ_PATTERN_MINE = seeds/cycle, 0=off).
    # Seeded with the corpus signatures so it never re-mines a textbook fact the gate would
    # quarantine. Proposal-side; the gates + kernel still decide every mined candidate.
    _mine_k = _env_int("LEIBNIZ_PATTERN_MINE", 0)
    _miner = None
    if _mine_k > 0:
        from leibniz.pattern_mining import PatternMiner  # local import: stdlib-only, no extra deps
        from leibniz.structural import congruence_signature as _sig
        # Drop both corpus AND exemplar signatures from the minable pool: an exemplar is already
        # injected as steering context, so re-mining it would double-inject the same fact and
        # inflate apparent diversity without adding novelty (ADR 0034 Stage-2 review). Mining must
        # contribute NET-NEW patterns beyond what Stage 1 already shows.
        _exclude = {s for e in CorpusBackend.from_json(cfg.corpus_path).entries
                    if e.claim_property and (s := _sig(e.claim_property))}
        _exclude |= {s for cp in novelty_exemplar_properties() if (s := _sig(cp)) is not None}
        _miner = PatternMiner(_exclude)
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
        demonstrate=demonstrate,
        promulgate=Promulgate(),
        verification=VerificationGate(policy),
        kfm=KFM(Archive()),
        budget=TrustBudget(policy),
        cost_budget=cost_budget,  # ADR 0011 cap, ADR 0014 metered by real usage
        # ADR 0018: outcome-conditioned conjecture; ADR 0023: resumed from + persisted
        # to disk so near-misses accumulate across runs for weaken-and-retry.
        notebook=_notebook,
        notebook_path=_notebook_path,
        pattern_miner=_miner,           # ADR 0034 Stage 2 (None unless LEIBNIZ_PATTERN_MINE>0)
        mine_k=_mine_k,
        weaken_k=_env_int("LEIBNIZ_WEAKEN_K", 3),
        # ADR 0018/0019: adaptive difficulty band, resumed from + persisted to disk.
        frontier=FrontierController.load(_frontier_path),
        frontier_path=_frontier_path,
    )

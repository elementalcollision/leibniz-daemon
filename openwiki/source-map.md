---
type: Reference
title: Source Map
description: A map of the leibniz package modules to their responsibilities — the guarded trust core (types, trust, propositio, pipeline, daemon, gates, verifiers), the backends (lean_cli, lean_repl, smt_z3, walnut, coq_docker, isabelle_docker), the providers (anthropic, openrouter, aristotle, huggingface, prover, failover, router), the discovery/selection, and the ledger/ops layer (calculemus, runtime, instance_config, deploy).
tags: [source-map, modules, layout, file-map, responsibilities]
---

# Source Map

The `leibniz/` package is the daemon core. It is **pure stdlib by design** — the trust boundary stays legible and the extras (Z3, the Anthropic SDK, Lean, Aristotle) are optional, lazy, and env-gated. Importing `leibniz` pulls in only stdlib-backed modules; the real backends are never imported by importing the package.

## The guarded trust core

These modules are **PreToolUse-guarded** and byte-frozen against weakening (`tests/test_invariants.py`). Editing `tests/test_invariants.py` to make a change pass is the signal that a change is weakening the boundary — surface it to the operator instead.

| Module | Responsibility |
|---|---|
| `leibniz/types.py` | The vocabulary: `TrustTier`, `Role`, `ClaimType`, `Verdict`, `FinishReason`, `ClaimSignature`, `EdgeEvidence`. Total, no reference to an LLM. |
| `leibniz/trust.py` | `TrustPolicy` — the load-bearing invariant. `validate_edge`/`validate_path` raise `TrustViolation`. Pins `PROOF_EDGE`, `KERNEL_PRODUCER`, `FAITHFULNESS_EDGE`, `NOVELTY_EDGE`, the operator-owned `FAITHFULNESS_PRODUCERS` allowlist (ADR 0041). |
| `leibniz/proposito.py` | The `Propositio` triad: `Enuntiatio` (claim), `Expressio` (formal statement), `Demonstratio` (proof + `kernel_verified`/`seal`). The unit of work and record. |
| `leibniz/pipeline.py` | The six stages: `Survey`, `Conjecture`, `Formalize`, `Derive`, `Demonstrate`, `Promulgate`. Plus `_compile_with_repair` (ADR 0012 import-resolve + R4.2 LLM repair) and `_steer_contract` (ADR 0022). |
| `leibniz/daemon.py` | `Leibniz` — the circadian cycle + `run_cycles` discovery loop. `CycleReport`. Resilience (ADR 0029). |
| `leibniz/gates/faithfulness.py` | `FaithfulnessGate` — the adversarial gaming-witness spine + sound backends + per-`ClaimType` probes + the bounded JUDGED fallback. |
| `leibniz/gates/novelty.py` | `NoveltyGate` — non-triviality (`is_trivial`) + external dedup (`contains_equivalent`) + structural congruence (ADR 0032). |
| `leibniz/gates/verification.py` | `VerificationGate` — `is_promotable` (pure boolean over recorded evidence) + `finalize`. |
| `leibniz/gates/sound_backends.py` | `SoundFaithfulnessBackend`/`Certificate`/`CertificateRechecker` (ADR 0037) — the pluggable sound-checker seam. |
| `leibniz/verifiers.py` | `LeanVerifier` (sole `kernel_verified` writer via `discharge`) + `SMTVerifier` (cheap refute / gaming-witness; only kills). |

## Backends (`leibniz/backends/`)

| Module | Responsibility |
|---|---|
| `lean_cli.py` | `LeanCliBackend` — `lake env lean <file>` in the pinned `leibniz-lean:v4.34.0-rc2` container. `check_proof` rejects `sorry`/`sorryAx`. `normalize_statement` (R1c) — elaborator-canonical hash. `persistent` mode. |
| `lean_repl.py` | `LeanReplBackend` — a long-running container with `docker exec` + `check_proof_with_error` (surfaces the kernel's complaint for ADR 0029 repair). |
| `smt_z3.py` | `Z3Backend` — `find_counterexample`, `find_gaming_witness`, `decide_unsat` (tri-state). A sound arithmetic-predicate DSL (ADR 0021). Only kills. |
| `walnut.py` | `WalnutBackend` — FO over k-automatic sequences; decides (Büchi–Bruyère) soundly over **unbounded** n. `recheck_walnut_certificate`. |
| `coq_docker.py`, `isabelle_docker.py` | ADR 0048 — Coq/Isabelle deciders behind the same seam. |

## Providers (`leibniz/providers/`)

| Module | Responsibility |
|---|---|
| `__init__.py` | Shared prompt templates (`AUTOFORMALIZE_SYSTEM`/`_DSL`/`_PROMPTS`), `repair_*_prompt`, `decompose_prompt`, `ProviderUnavailable`, `ssl_context`, `USER_AGENT`. Single source of truth so failover backups build byte-identical prompts. |
| `anthropic_provider.py` | `AnthropicProvider` — Claude for CONJECTURE/FORMALIZE/PROOF_DRAFT + the repair hooks. |
| `openrouter_provider.py` | `OpenRouterProvider` — OpenRouter (OpenAI-compatible) gateway for the prover cascade + full repair failover. |
| `prover.py` | `ProverClient` — a hosted Goedel-Prover-V2/DeepSeek-Prover endpoint (`LEIBNIZ_PROVER_URL`). |
| `aristotle_provider.py` | `AristotleProver` — ADR 0028 lever-3 agentic prover (the scaffold, not the raw model, closes goals). |
| `huggingface_provider.py` | `HuggingFaceProvider` — ADR 0019 HF prover + live calibration. |
| `decomposition_prover.py` | `DecompositionProver` — wraps a base prover with the decomposition prompt (ADR 0024). |
| `failover_provider.py` | `FailoverProvider` — a primary/backup with live failover (ADR 0029). |
| `router.py` | `RoleRouter` — dispatches `PROOF_DRAFT` to the prover, everything else to the autoformalizer. |

## Consensus, repair, decomposition

| Module | Responsibility |
|---|---|
| `leibniz/consensus.py` | `ProofConsensus` — the cascaded/witness ensemble under **N+1 kernel-verified consensus**. `_prover_identity` (one model = one voter). `ConsensusDemonstrate`, `NoOpDerive`. |
| `leibniz/proof_repair.py` | `ProofRepairer`/`RepairingDemonstrate` — ADR 0029 agentic draft→error→repair loop; the panel of distinct-model repairers. N+1 preserved. |
| `leibniz/lemma_decomposition.py` | `LemmaDecomposer`/`DecomposingDemonstrate` — ADR 0027 independent sub-lemma decomposition with `have`-block hints (prover context only). |

## Discovery, selection, corpus, novelty

| Module | Responsibility |
|---|---|
| `leibniz/discovery.py` | `DiscoveryNotebook`, `FrontierController`, `difficulty`, `quality`, `weakening_seeds`, `steer`, the novelty-exemplar loaders. ADR 0018/0023/0034. |
| `leibniz/selection.py` | `KFM`/`Archive`/`Elite`/`Disposition` — MAP-Elites over a 3-axis behavior descriptor (sub-area × technique × complexity); curiosity-biased parent sampling; recombination. |
| `leibniz/corpus.py` | `CorpusBackend`/`CorpusEntry` — the R3 known-results corpus; `contains_equivalent` (exact hash) + `structural_known` (ADR 0032 congruence). Loads `corpus/known_results.json`. |
| `leibniz/structural.py` | `congruence_signature` — canonicalize a polynomial-congruence FORM (never truth); multivariate + loose phrasings. ADR 0032. |
| `leibniz/novelty_metrics.py` | READ-ONLY structural-diversity tripwire (ADR 0034 Stage 0). Measurement, never an arbiter. |
| `leibniz/pattern_mining.py` | ADR 0034 Stage 2 empirical pattern miner — true residue regularities by computation. Proposal-side, decides nothing. |
| `leibniz/probes.py` | The real `ClaimProbe`s (R2b) — `coverage_probe`; `default_probes`. The faithfulness gate's mechanical fast path. |
| `leibniz/imports.py` | `resolve_imports` (ADR 0012) — mechanical Mathlib import-resolve against `corpus/mathlib_modules.json`. |

## Budget, cost, ledger, ops

| Module | Responsibility |
|---|---|
| `leibniz/budget.py` | `TrustBudget` — the judged-faithfulness budget (0.15 fraction). `try_admit`. |
| `leibniz/cost.py` | `CostBudget` — USD cap (ADR 0011 coarse + ADR 0014 real token accounting). |
| `leibniz/pricing.py` | `estimate_usd` — per-model token pricing. |
| `leibniz/calculemus.py` | `Calculemus` — the Codex + the operator publish tier (R6). `render_propositio`, `render_public`, `colophon`. |
| `leibniz/calculemus_site.py` | Serialize the ledger to the codexcalculemus.com source (ADR 0017/0050). `law_payload` provenance vocabularies. |
| `leibniz/runtime.py` | `PersistentRuntime` — SQLite memory + clock phase + write-barrier (ADR 0016/0033). |
| `leibniz/instance_config.py` | `InstanceConfig`/`resolve_instance_config` — per-instance pinned Lean image + corpus (ADR 0033 Slice 3). |
| `leibniz/deploy.py` | `validate_profile` — the deploy-profile isolation guard (ADR 0033 Slice 4). |
| `leibniz/env.py` | `load_env` — load `.env` (gitignored). |
| `leibniz/assembly.py` | `build_daemon` — wire the real stack into a live `Leibniz`. Makes no network calls; only constructs. |

## The Walnut/Observatory tier

| Module | Responsibility |
|---|---|
| `leibniz/observatory.py` | `WalnutObservatory` — the non-Q.E.D. tier of Walnut-decided records (ADR 0038). Separate from the kernel Codex. |
| `leibniz/observatory_lint.py` | `lint_descriptor` (ADR 0039) — a machine-checkable property spec; brute-forced over a finite prefix. |
| `leibniz/walnut_conjecture.py` | The proposal side that feeds the Observatory (ADR 0038). Generates automatic-sequence claims; decides nothing. |

## Tools & seeds (ADR 0041)

| Module | Responsibility |
|---|---|
| `leibniz/tools/protocol.py` | `ToolDescriptor`/`ToolResult`/`Provenance` (HUMAN/INGESTED_DERIVED/SELF_BUILT). Re-exports the `Certificate`/`CertificateRechecker` (single source of truth with `sound_backends`). |
| `leibniz/tools/registry.py` | `ToolRegistry` — the gate-owned re-check + statement-template dispatch. State 1 (DEFER) → State 2 (decider registered). |
| `leibniz/tools/sandbox.py` | `SandboxedTool`/`SandboxTask` — untrusted code in docker isolation (the FunSearch generalization). |
| `leibniz/seeds.py` | `Seed`/`SeedKind`/`SeedStatus` — untrusted seeds from ingested research. `validate_seed` guards (ADR 0041 Phase 3). |
| `leibniz/seed_intake.py` | Route VALIDATED seeds to PROPOSER seams (ADR 0041 Phase 4). FLOOR raises the bar; TARGET steers; CONSTRUCTION → sandbox. |

## Top-level entrypoints

| Path | Responsibility |
|---|---|
| `demo.py` | Turn one circadian cycle with deterministic fakes; every gate fires. |
| `scripts/run_live.py` | One bounded circadian cycle with the real stack. |
| `scripts/build_corpus.py` | Build `corpus/known_results.json` (the R3 corpus). |
| `scripts/export_calculemus.py` | Serialize + kernel-re-verify the published ledger to the Calculemus site. |
| `tests/test_invariants.py` | The 11 byte-frozen trust invariants (the enforcement). |
| `docs/adr/0001..0050` | The decisions; `docs/architecture.md`, `docs/capability-ladder.md`, `docs/optimization-roadmap.md`. |

The full layout lives in `README.md` and `CLAUDE.md`; this page is a responsibilities map, not a file inventory.

---
type: Component
title: Providers
description: The proposal-role LLM providers — Anthropic (Claude) for conjecture/formalize, OpenRouter for the prover cascade, a hosted prover client, HuggingFace, and the failover/aristotle reasoners — all confined to proposal roles behind the RoleRouter.
tags: [providers, llm, anthropic, openrouter, prover, huggingface, failover, aristotle, role-router, proposal]
---

# Providers

The providers are the LLMs, confined to **proposal roles** only (ADR 0001). Every method returns a *draft*; none may adjudicate. The only place provider output is trusted as a verdict is the bounded `FaithfulnessJudge` residual, and even there it is budget-bounded.

## The roles an LLM may occupy

`leibniz/types.py::Role` — all are proposal roles (an LLM never adjudicates):

| Role | What it drafts |
|---|---|
| `SURVEY` | frontier edges + analogies (the Leonardo seam) |
| `CONJECTURE` | an `Enuntiatio` (human-readable claim) from a seed |
| `FORMALIZE` | a Lean `Expressio` (formal statement) from a claim |
| `PROOF_DRAFT` | a tactic script for the kernel to check |
| `ANALOGY` | cross-domain stepping stones (the da Vinci move) |
| `WALNUT_CONJECTURE` | an automatic-sequence FO claim for Walnut to decide (ADR 0038) |

## The provider stack

`leibniz/providers/`:

| Provider | Module | Role |
|---|---|---|
| `AnthropicProvider` | `providers/anthropic_provider.py` | CONJECTURE/FORMALIZE (primary autoformalizer), `claude-opus-4-8`. Returns structured JSON for those roles; a separate `_PROOF_SYSTEM` for PROOF_DRAFT so the kernel never gets `{"script": ...}`. Also provides `repair_proof`, `repair_formalization`, `repair_contract`, `decompose` (ADR 0029 failover). Lazy SDK import + `ANTHROPIC_API_KEY`. |
| `OpenRouterProvider` | `providers/openrouter_provider.py` | The prover cascade (DeepSeek-Prover-V2 / Goedel / a Claude witness) behind one key, `OPENROUTER_API_KEY`. Model id is per-instance so the same class serves every ensemble member. Uses shared prompts with `AnthropicProvider` so a failover backup builds byte-identical prompts. |
| `ProverClient` | `providers/prover.py` | A hosted prover endpoint for PROOF_DRAFT (`LEIBNIZ_PROVER_URL` / `LEIBNIZ_PROVER_KEY`) — Goedel-Prover-V2 / DeepSeek-Prover class. |
| `HuggingFaceProvider` | `providers/huggingface_provider.py` | A HuggingFace-hosted prover (ADR 0019). |
| `AristotleProver` | `providers/aristotle_provider.py` | ADR 0028: the Harmonic Aristotle agentic prover (lever 3) — closed goals a stronger raw model did not (the scaffold, not the raw model, closes goals). |
| `FailoverProvider` | `providers/failover_provider.py` | Wraps a primary + backup; fails over on `ProviderUnavailable` so a sustained Anthropic 529 doesn't crash a multi-cycle run. |
| `DecompositionProver` | `providers/decomposition_prover.py` | ADR 0024: reshapes the prompt for lemma decomposition; the SAME voter as its base (unwrapped by `_prover_identity`). |

## The role router

`leibniz/providers/router.py::RoleRouter` dispatches proposal roles: `PROOF_DRAFT` to the hosted prover, everything else to the autoformalizer (ADR 0005). The router is a `ProviderAdapter` — it only drafts.

## Shared prompts (single source of truth)

`leibniz/providers/__init__.py` holds `AUTOFORMALIZE_SYSTEM`, `AUTOFORMALIZE_DSL`, `AUTOFORMALIZE_PROMPTS` (CONJECTURE/FORMALIZE/PROOF_DRAFT templates) and the repair prompts (`repair_proof_prompt`, `repair_formalization_prompt`, `repair_contract_prompt`, `decompose_prompt`). Both `AnthropicProvider` and `OpenRouterProvider` use these so a failover backup builds byte-identical prompts — they cannot drift.

## Cost metering

Each provider meters real token usage into a `CostBudget` (`leibniz/cost.py`, ADR 0014): `record_usage(model, input_tokens, output_tokens)` priced through `leibniz/pricing.py`. The coarse fallback (`record_calls(n)`, ADR 0011) no-ops once real usage is flowing, so wiring the meter never double-counts. The `CostBudget` stops a multi-cycle run before it exceeds `LEIBNIZ_DAILY_USD_CAP` (cost governance, never a verdict).

See [Proof Consensus](proof-consensus.md) for how the prover ensemble composes and [Pipeline](../architecture/pipeline.md) for where each role fires.

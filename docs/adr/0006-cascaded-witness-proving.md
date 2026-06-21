# ADR 0006 — Cascaded + Witness Proving with N+1 Kernel-Verified Consensus (R4.1)

- Status: Accepted
- Date: 2026-06-21
- Related: ADR 0001 (only the kernel decides a proof), ADR 0005 (proposal providers).
  Operator directive: "cascaded provers and witness provers; N+1 consensus on
  proving even if it's costly." Routing: Anthropic direct for CONJECTURE/FORMALIZE,
  OpenRouter for the prover ensemble.

## Context

A single prover drafting a single tactic script, checked once by the kernel, is
sound (the kernel is the arbiter). But the operator wants defense-in-depth on the
most consequential edge: redundancy against a flaky prover, a backend integration
bug, or a degenerate proof, accepting the extra cost. The constraint is that this
must not become a vote that erodes the kernel's authority.

## Decision

**1. The kernel still decides; consensus only adds a requirement.** Every prover
draft is checked by `LeanVerifier.discharge` (the sole `kernel_verified` writer,
invariant 1). A statement is promulgatable on the proof edge **only if
`min_consensus` (N+1) distinct provers each produce a proof the kernel verifies.**
This is strictly *more* conservative than one verified proof — it can never weaken
the boundary, only make promulgation harder.

**2. Cascade + witnesses.** `consensus.ProofConsensus` runs an ordered ensemble of
provers (cheap → expensive cascade, plus cross-model witnesses) over the *same*
statement. Each is independent; a dead/unconfigured prover is skipped, never blocks
the others. The ensemble is configured by `LEIBNIZ_PROVER_MODELS` (OpenRouter model
ids) and `LEIBNIZ_PROOF_CONSENSUS` (the N+1 threshold).

**3. The recorded PROOF_EDGE is honest.** On consensus, the recorded edge is a
*real* discharge edge (MECHANICAL, kernel-sourced) annotated with the consensus
count. Below threshold — even with one verified proof — the edge is a MECHANICAL
FAIL ("insufficient independent kernel-verified proofs"). Consensus is computed
from `demo.kernel_verified` values written by `discharge`; nothing here writes
`kernel_verified` or fabricates a tier, so the boundary guards still hold.

**4. Routing.** CONJECTURE/FORMALIZE → `AnthropicProvider` (Claude, direct).
PROOF_DRAFT → an ensemble of `OpenRouterProvider` instances (one per model id).
Swapping a hosted endpoint for a rented A100 is an env change, not a code change.

## Consequences

- Cost scales ~linearly with ensemble size and is intentional ("even if costly").
- N (hence N+1) is operator-tunable; N+1 = 2 is the default. Setting it to 1
  recovers single-prover behavior; higher values buy more redundancy.
- Soundness does not *depend* on consensus (one kernel proof is already sound);
  consensus is robustness/assurance. The faithfulness gate (ADR 0002/0004) and
  novelty (ADR 0001) remain the other edges — consensus only hardens proof.

## Non-goals

- Provers voting on truth. They never decide; they propose, and the kernel checks
  each draft independently. "Consensus" means N+1 *kernel* verifications, not N+1
  model opinions.

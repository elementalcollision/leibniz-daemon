# ADR 0005 — Proposal Providers and the Structured Proposal Contract (R4)

- Status: Accepted
- Date: 2026-06-21
- Related: ADR 0001 (LLMs propose, never decide), ADR 0004 (structured faithfulness
  contract). Resolves operator decision D5 (hosted API first; rented GPU prover at
  scale).

## Context

R0–R3 built the mechanical gate on deterministic fakes. R4 puts real LLMs in the
*proposal-only* roles (`Role.{SURVEY,CONJECTURE,FORMALIZE,PROOF_DRAFT,ANALOGY}`).
The kernel still decides every proof and every gate stays mechanical, so model
choice is a cost/throughput decision, not a soundness one. Two things must hold:
proposals must be structured enough to feed the R2 faithfulness contract, and no
provider output may ever be trusted as a verdict.

## Decision

**1. Structured proposal contract (JSON per role).** Providers return JSON so the
proposal carries the machine-checkable fields the gates need:

- `CONJECTURE` → `{statement, claim_type, falsifiable_claim, claim_domain,
  claim_property}` — a full structured `Enuntiatio` (the last two are the ADR 0004
  predicates over `n`).
- `FORMALIZE` → `{theorem_src, imports, established_domain}` — the Lean statement
  plus the domain it actually establishes (so the faithfulness gate can compare it
  to `claim_domain`).
- `PROOF_DRAFT` → a Lean tactic script (raw string).

Parsers are **defensive**: malformed/absent JSON falls back to a safe stub, so a
bad proposal becomes a MALFORMED/DEFER downstream — never a crash, never a pass.

**2. Role routing.** `providers.RoleRouter` (a `ProviderAdapter`) sends
CONJECTURE/FORMALIZE/SURVEY/ANALOGY to an autoformalizer/Claude provider
(`AnthropicProvider`) and PROOF_DRAFT to a hosted prover endpoint
(`ProverClient`, a Goedel-Prover-V2 / DeepSeek-Prover class model behind an HTTP
seam). This matches D5: hosted API for development; swap `ProverClient`'s endpoint
for a rented A100 at scale — a config change, not a code change.

**3. Self-reported fields are held accountable, not trusted.** The autoformalizer's
`established_domain` is the model's *claim* about its statement; the R2 gaming-witness
and coverage probe are what verify it. A wrong/lying `established_domain` is caught
mechanically (GAMED / DEFER), so the proposal contract does not become a trust hole.

**4. Lazy + env-gated.** Providers import their SDK lazily and read creds from the
environment (`ANTHROPIC_API_KEY`; `LEIBNIZ_PROVER_URL` / `LEIBNIZ_PROVER_KEY`).
Absent creds → the provider reports unavailable and nothing calls out; the wiring
ships now and goes live when creds are added.

## Consequences

- The R4 exit test (promulgate ≥1 true, novel, non-trivial theorem end-to-end, no
  human on the critical path) needs both live creds **and** a real SURVEY source
  (Leonardo, deferred). Until then the provider→kernel path is exercised by a
  creds-gated integration test; the routing/parsing is covered by CI-safe tests.
- No new third-party dependency for the prover client (stdlib `urllib`); the
  `anthropic` SDK stays in the `propose` extra and is imported lazily.

## Non-goals

- Trusting any proposal output as a verdict (the kernel + gates decide).
- Running 32B-class prover models locally (D5: hosted/GPU endpoint).

---
type: Reference
title: Capability Ladder R0-R6
description: The build order — stand up the trust boundary before the intelligence. R0-R6 are substantially built; the project is in post-R6 optimization (the novelty frontier). Each rung is independently testable and leaves the daemon in a working state.
tags: [capability-ladder, r0, r1, r2, r3, r4, r5, r6, roadmap, build-order, trust-boundary]
---

# Capability Ladder R0–R6

The principle: **stand up the trust boundary before the intelligence.** A weak prover behind a sound gate produces few but trustworthy laws; a strong prover behind a weak gate produces a polluted ledger. The gate is built first. R0–R6 are substantially built and merged; the project is in **post-R6 optimization** (`docs/optimization-roadmap.md`). R1 shipped via Docker, not LeanDojo (`backends/lean_cli.py` / `lean_repl.py` against a pinned Lean 4.31 + Mathlib container; ADR 0003/0011). All exit tests remain valid as regressions; `LeanVerifier.discharge` is still the sole `kernel_verified` writer.

## R0 — Scaffold

The loop, the types, the gates, the trust policy, and a passing dry-run with deterministic fakes. No real Lean/Z3/LLM yet.

- `Propositio` triad with active `proof_obligation`
- Six-stage pipeline; cheap-refutation-first ordering
- Three gates (faithfulness, novelty, verification) with tier tagging
- `TrustPolicy` enforced at promotion
- KFM over a MAP-Elites archive
- `demo.py` turns one cycle; every gate fires

**Exit test:** `python demo.py` shows one `Q.E.D.` and one of each quarantine reason.

## R1 — Real kernel (the judge comes online)

Replace `FakeLean` with a Lean 4 + Mathlib toolchain behind `LeanBackend` (via a pinned **Docker** container — `backends/lean_cli.py`/`lean_repl.py`, ADR 0003/0011, not LeanDojo).

- `compile_statement` → real elaboration (syntactic validity for free)
- `check_proof` → real kernel verification; the only thing that may set `kernel_verified`; rejects `sorry`/`sorryAx`
- `closed_by_decision_procedure` → the `aesop`/`simp`/`decide`/`ring`/`nlinarith`/`omega`/`trivial` triviality test
- `normalize_statement` (R1c) → an **elaborator-canonical** structural hash (de Bruijn indices + fully-qualified constants) so alpha-renamed/notation-different statements collide

**Exit test:** a hand-written true theorem promulgates; a false one is `UNPROVEN`; a tautology is `TRIVIAL`.

## R2 — Faithfulness hardening (close the residual)

The research-hard rung. Make the gaming-witness real and write the first claim-type probes.

- Compile `falsifiable_claim` → a searchable Z3/Lean predicate; implement `_negate` for real (ADR 0004)
- `find_gaming_witness` over the structured contract (`claim_domain ∧ ¬established_domain ∧ ¬claim_property`)
- Probes for `COMPLEXITY_BOUND` and `CORRECTNESS_OVER_DOMAIN` (the two most common in analysis of algorithms)
- Wire the JUDGED fallback (round-trip + independent judge) for `OPEN_FORM` only, with budget tracking (R2c)

**Exit test:** a kernel-provable but unfaithful statement (e.g. a vacuous specialization) is caught as `GAMED` or `UNFAITHFUL`, *before* proof compute.

## R3 — Novelty corpus (stop rediscovering textbooks)

Stand up the known-results corpus as a real promotion gate.

- Index Mathlib + a curated analysis-of-algorithms set by `ClaimSignature`
- `contains_equivalent` / `nearest` over **structural** signatures (the elaborator-canonical hash), not prose embeddings
- The structural congruence match (ADR 0032) — polynomial-congruence **FORM**, never truth

**Exit test:** a re-derivation of the Ω(n log n) comparison-sort bound is caught as `KNOWN`.

## R4 — Proposal models (the variation operator)

Replace `FakeProvider` with real proposal-role models behind `ProviderAdapter`.

- CONJECTURE: an LLM as semantic variation operator over KFM-selected parents
- FORMALIZE: an autoformalizer (specialized formalizer preferred over raw prompting) → Lean statement, with mechanical import-repair (ADR 0012) + R4.2 LLM repair
- PROOF_DRAFT: a prover model (DeepSeek-Prover-V2 / Goedel-Prover-V2 / Leanstral class) drafting tactic scripts
- All confined to proposal; the kernel still decides
- An OpenRouter prover ensemble with **N+1 kernel-verified consensus** (ADR 0006); the ADR 0029 agentic repair panel; the ADR 0027 sub-lemma decomposition

**Exit test:** the daemon promulgates at least one true, novel, non-trivial theorem end-to-end with no human in the loop on the critical path.

## R5 — Selection & open-endedness (sustained novelty)

Make KFM and the archive do real work so the search keeps finding new ground.

- The 3-axis behavior descriptor (sub-area × proof technique × statement complexity)
- Curiosity-biased parent sampling toward sparse cells
- Recombination that genuinely combines parent features, not just mutates
- Stagnation/drift detection → re-seed SURVEY when a region is exhausted
- The closed discovery loop: KFM recombined parents + weakened near-misses + fresh survey seeds (ADR 0009)

**Exit test:** over N cycles, archive coverage grows and promulgated theorems span multiple sub-areas rather than clustering.

## R6 — The reading-room (*Calculemus*) + operator tier

Promotion ≠ publication. Stand up the public ledger and the operator-tier gate.

- Auto-render promulgated Propositiones (triad + kernel certificate + falsifiable claim) to the *Calculemus* site
- Operator-tier publish action (a separate mutation); the daemon promulgates to the Codex, a human promotes Codex → public; the PROD-only publish guard (ADR 0033)
- Provenance/colophon: what is held back and why

**Exit test:** a promulgated law appears in *Calculemus* with its proof open to inspection, only after an explicit operator publish.

## The throughline

R0–R3 build and harden the **trust boundary** (kernel, faithfulness, novelty). R4–R5 add the **intelligence** (proposal, selection) behind that boundary. R6 opens the **ledger**. Building in this order means the system is never capable of producing a fast-flowing stream of unsound or unfaithful laws — the gate exists before the firehose.

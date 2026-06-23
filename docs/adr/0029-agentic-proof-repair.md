# ADR 0029 — Agentic proof-repair loop (lever 3, option C) — DRAFT

Status: **Proposed (draft)** (2026-06-22)
Depends on: ADR 0006 (N+1 consensus), ADR 0011 (Lean REPL), ADR 0024/0027 (decomposition).

## Context

ADR 0027's instrumentation localized the wall to **prover reach**: drafts that *almost*
work don't get repaired, and decomposed sub-lemmas don't prove (3/22). The strongest,
most architecture-aligned lever is not a bigger model but a **scaffold**: the published
SOTA (HILBERT, arXiv 2509.22819 — Gemini 2.5 Pro + Goedel-V2 → 99.2% miniF2F, 70%
PutnamBench; LEAP → 100% Putnam-2025) finds that **a frontier reasoner driving a
specialized prover with compiler-error feedback and premise retrieval dominates the raw
prover**. Leibniz already owns the pieces: a frontier reasoner (Claude via
`AnthropicProvider`), prover adapters, and the Lean REPL for the error signal. Our
existing `repair_formalization` (ADR 0012) and `_steer_contract` (ADR 0022) are
proto-versions of exactly this loop, applied to other stages.

## Proposed decision (to refine before building)

A new DEMONSTRATE strategy, `RepairingProver` / a `RepairingDemonstrate` wrapper, that
turns single-shot proving into a bounded **draft → check → repair** loop:

1. **Draft.** A prover drafts a proof (the existing ensemble, or a stronger one from
   ADR 0028).
2. **Check.** `LeanVerifier.discharge` runs it (unchanged — sole `kernel_verified`
   writer). On PASS, done.
3. **Diagnose.** On failure, capture the kernel's **actual error diagnostics**
   (`LeanReplBackend`/`compile_with_error` already return them).
4. **Retrieve (optional).** Pull candidate Mathlib lemmas relevant to the goal/error
   (premise selection — LeanDojo-style, or name search over the corpus).
5. **Repair.** A frontier reasoner (Claude) gets `(statement, failed proof, kernel error,
   retrieved lemmas)` and proposes a corrected proof — a new provider role, e.g.
   `PROOF_REPAIR`.
6. **Loop** up to `max_repair_rounds` (small, e.g. 2–3), then give up → UNPROVEN.

Promotion still requires N+1 consensus on the final kernel-verified proof, and the loop
composes with ADR 0027 decomposition (repair each sub-lemma; repair the composed main).

## Why this stays trust-safe

- **Pure proposal-side.** The loop only generates candidate proofs; `discharge` decides
  every one. No edit to `trust.py`/`verifiers.py`'s `discharge`/the gates. The kernel
  error is an *input to the next proposal*, never a verdict.
- **Single self-contained declaration per check** (the ADR 0027 lesson): the repaired
  proof is `theorem_src := <proof>`, so a smuggled top-level command is a parse error —
  no preamble/poisoning surface. The repair prompt must NOT be allowed to alter
  `theorem_src` (only the proof body); enforce by reattaching the proof to the fixed
  statement, as `_join_proof` already does.
- N+1 consensus and the non-triviality/faithfulness gates are unchanged and still gate
  promotion.

## Open design questions (resolve before implementation)

- **Repair model.** Claude (frontier reasoner, we have it) vs. a specialized prover's own
  self-correction mode (Goedel-V2 has one). HILBERT suggests the frontier reasoner is the
  bigger lever; measure both.
- **Premise retrieval.** Worth the complexity now, or start with error-feedback only?
  (HILBERT credits retrieval materially; LeanDojo gives ~+4pp. Could phase it in.)
- **Cost/latency.** Each round = 1 frontier call + 1+ kernel checks. Bound rounds; fire
  only on candidates that pass the cheap gates (as decomposition does). Reuse the REPL
  import cache (ADR 0011) so per-round kernel checks stay cheap.
- **Interaction with ADR 0027.** Repair-then-decompose, or decompose-then-repair-each?
  Likely: try direct + repair first, then decomposition (repairing each piece).
- **Instrumentation first.** Mirror `DecompositionStats`: rounds attempted, repairs that
  changed the proof, repairs that closed — so efficacy is measurable from day one.

## Validation plan

- Unit (CI-safe): the loop drafts→diagnoses→repairs→re-checks with a faked prover + kernel
  (no network/docker); the statement is never mutated; rounds are bounded; one proof edge
  recorded; degrades to today's single-shot behaviour when repair is disabled.
- Gated (real kernel): a goal that fails one-shot but closes after a repair round.
- Live (billable): a calibration with the loop enabled, instrumented, vs. the ADR 0027
  baseline — does the non-trivial close rate rise?

## Status / next step

Draft only — no code yet. Recommend building after a measurement of options A (Goedel)
and B (Aristotle) tells us how much raw-model strength alone buys, so option C is scoped
against a known baseline.

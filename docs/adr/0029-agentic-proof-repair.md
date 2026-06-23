# ADR 0029 — Agentic proof-repair loop (lever 3, option C)

Status: **Accepted** (2026-06-23) — implemented in `leibniz/proof_repair.py`, opt-in via
`LEIBNIZ_PROOF_REPAIR`.
Depends on: ADR 0006 (N+1 consensus), ADR 0011 (Lean REPL), ADR 0013 (kernel provenance),
ADR 0024/0027 (decomposition), ADR 0028 (lever-3 options).

## Context

ADR 0027's instrumentation localized the wall to **prover reach**: drafts that *almost*
work don't get repaired, and decomposed sub-lemmas often don't prove. Our own lever-3
measurement agreed — a stronger *raw* model (Goedel-Prover-V2-32B via Featherless, harness
A) was marginal, while an *agentic* prover (Harmonic Aristotle, ADR 0028) closed goals our
ensemble could not. That matches the published SOTA: HILBERT (arXiv 2509.22819 — a frontier
reasoner driving a specialized prover with compiler-error feedback + premise retrieval) and
LEAP report that **the scaffold, not the raw model, is the lever**. Leibniz already owns the
pieces: a frontier reasoner (Claude via `AnthropicProvider`), prover adapters, and the Lean
REPL for the error signal. `repair_formalization` (ADR 0012) and `repair_contract` (ADR
0022) are proto-versions of exactly this loop applied to other stages.

## Decision

A bounded **draft → kernel-error → repair** loop, added as an opt-in DEMONSTRATE fallback.

**`ProofRepairer.prove(expr)`** (`leibniz/proof_repair.py`):
1. **Draft.** The frontier reasoner drafts a proof (`AnthropicProvider.propose(PROOF_DRAFT)`).
2. **Check + diagnose.** `backend.check_proof_with_error(expr, candidate) -> (ok, error)` —
   a new, *non-Protocol* backend method on `LeanReplBackend`/`LeanCliBackend` that returns
   the kernel's actual diagnostics. This is **advisory**: it never writes a verdict.
3. **Stamp (on ok).** `LeanVerifier.discharge` re-checks the candidate and is the **sole**
   writer of `kernel_verified` (unchanged). On a PASS it returns `(demo, edge)`.
4. **Repair (on failure).** `AnthropicProvider.repair_proof(theorem_src, failed_proof,
   error)` proposes a corrected `by …` block. Loop up to `max_rounds` (default 2), then
   give up (→ the candidate stays UNPROVEN).

**`RepairingDemonstrate`** is the stage wrapper. It runs the existing fallback ladder and
records **exactly one** proof edge:

> N+1 consensus → (optional) ADR 0027 decomposition → ADR 0029 repair

It composes at the `ConsensusResult` level (neither `consensus.prove` nor
`decomposer.prove` records an edge), so repair layers on top of decomposition with no
double-recording. When decomposition is off, it is simply consensus → repair.

Wired in `assembly.build_daemon`: `LEIBNIZ_PROOF_REPAIR>0` selects `RepairingDemonstrate`
(passing the existing `LemmaDecomposer` as the inner layer when `LEIBNIZ_LEMMA_DECOMPOSE>0`);
`LEIBNIZ_REPAIR_ROUNDS` sets the round bound. Off by default — today's behaviour is
unchanged unless the operator opts in.

## Why this preserves N+1 (the load-bearing decision)

A naive repair fallback would let a single repaired proof produce a PASS proof edge,
silently dropping the promulgation bar from N+1 to 1. We do **not** do that. The repaired
proof counts as exactly **one more distinct prover identity** (`repairer.identity =
"repair:anthropic"`, which by construction never collides with a base prover's `model:` /
`obj:` identity from `_prover_identity`). Repair runs only when the prior layers came up
**short**, and it promulgates only if:

    len(carried_distinct_identities ∪ {repair_identity}) >= min_consensus

So at the default N+1=2 the base ensemble must already hold **one** distinct kernel proof
for repair to supply the second — a lone repaired proof can never self-satisfy. At
`min_consensus == 1` the operator has explicitly opted into single-proof promulgation
(exactly as for any single prover). `ConsensusResult` gained an additive `identities`
(and `verified_proof`) field to make this counting exact rather than count-based.

## Why this stays trust-safe (CLAUDE.md invariants 1, 2, 7)

- **Pure proposal-side.** The reasoner only proposes; `discharge` decides every candidate.
  No edit to `trust.py`, `verifiers.py::discharge`, or the gates. The kernel error is an
  *input to the next proposal*, never a verdict. `tests/test_invariants.py` is byte-identical.
- **Statement is fixed.** `repair_proof` is prompted to change only the proof, never the
  theorem; and `_join_proof` reattaches the body to the real `theorem_src`, so a repaired
  body that "proves" a different/weaker claim simply fails to elaborate.
- **Single self-contained declaration per check** (the ADR 0027 lesson): the checked source
  is `theorem_src := <proof>`. Inside a `by` block a smuggled top-level command is a parse
  error — no preamble/poisoning surface.
- **Verified proof attached only when promulgating.** A repaired-but-not-promulgated proof
  is captured in `RepairStats` (for measurement) but is *not* attached as a kernel-verified
  `Demonstratio`; the recorded FAIL edge is what `VerificationGate.is_promotable` reads, so
  `kernel_verified`/Q.E.D. never disagrees with the gate.

## Resolved design questions

- **Repair model:** frontier reasoner (Claude) for both draft and repair in v1 — it is a
  distinct consensus identity from the specialized base provers and is the bigger lever per
  HILBERT. A specialized-prover drafter + frontier repairer is a possible v2.
- **Premise retrieval:** deferred. v1 is error-feedback only (the cheaper, larger lever);
  retrieval can phase in later behind the same loop.
- **Cost/latency:** bounded rounds (default 2); the REPL import cache (ADR 0011) keeps
  per-round checks cheap; repair fires only after the cheaper layers fail.
- **Interaction with ADR 0027:** decompose-then-repair — repair is the outermost, most
  expensive fallback.

## Validation

- **Unit (CI-safe, done):** `tests/test_proof_repair_r0029.py` — the loop drafts →
  diagnoses → repairs → re-checks with a faked prover + kernel (no network/docker); the
  statement is never mutated; rounds are bounded; provider errors never block; one proof
  edge is recorded; a lone repair cannot self-satisfy N+1; repair supplies the deciding
  vote only when one short; degrades to a safe no-op when the backend can't surface errors.
  `discharge` remains the sole stamper; `test_invariants.py` unchanged.
- **Gated (real kernel):** a goal that fails one-shot but closes after a repair round
  (`check_proof_with_error` exercised end-to-end). Pending image run.
- **Live (billable):** a calibration with `LEIBNIZ_PROOF_REPAIR=1` vs the ADR 0027 baseline
  — does the non-trivial close rate rise, and at what round distribution (`RepairStats`)?

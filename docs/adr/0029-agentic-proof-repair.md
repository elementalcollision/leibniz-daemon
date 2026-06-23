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

## Resilience — failover frontier reasoners

A single reasoner is a single point of failure: the first live measurement stalled when
Anthropic was mid-outage (opus 500s, sonnet 529s). The repairer's reasoner is therefore a
`FailoverProvider` — an ordered chain that returns the first non-empty success: the
Anthropic primary, then OpenRouter-hosted backups (`LEIBNIZ_REASONER_FALLBACKS`, default
`z-ai/glm-5.2, moonshotai/kimi-k2.6, openai/gpt-5.5`). Failover is transparent when the
primary is healthy (no behaviour/cost change) and only triggers on an exception or empty
output. Backups are added only when `OPENROUTER_API_KEY` is set. This changes only WHICH
frontier model drafts/repairs — every candidate still goes through `discharge`, so the
kernel decides regardless. `OpenRouterProvider` gained `repair_proof` so a backup can repair,
not just draft; the model that closed each goal is recorded for measurement honesty.

## Why this preserves N+1 (the load-bearing decision)

A naive repair fallback would let a single repaired proof produce a PASS proof edge,
silently dropping the promulgation bar from N+1 to 1. We do **not** do that. Repair runs
only when the prior layers came up **short**, and the repaired proof counts as one more
distinct prover identity **only if the model that produced it differs from every base
verifier**:

    distinct = len(carried_identities) + (1 if canonical(repair_model) ∉ {canonical(i) for i in carried} else 0)
    promulgate iff distinct >= min_consensus

The dedup is load-bearing and was added after the **first live run (A) exposed the gap**:
the base ensemble included opus *and* the repair reasoner's primary is opus, so a fixed
`"repair:*"` identity would have counted **base-opus + repair-opus as two voters when it is
one model** — exactly the double-count ADR 0024 fixed for `DecompositionProver` (a model's
strategies are one voter; the repair scaffold is a strategy). `ProofRepairer.last_model`
records which model actually produced the proof (failover-aware), and `_canonical_model`
reduces identities to a bare model name so the same model via different gateways
(`claude-opus-4-8` vs `anthropic/claude-opus-4-8`) collapses. Over-merging is conservative —
it can only make consensus harder.

So at the default N+1=2 the base ensemble must already hold **one** distinct kernel proof
**from a different model** for repair to supply the second — a lone repaired proof, or a
repair by a model already counted, can never self-satisfy. At `min_consensus == 1` the
operator has explicitly opted into single-proof promulgation. `ConsensusResult` gained an
additive `identities` (and `verified_proof`) field to make this counting exact.

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
  HILBERT. **Measured caveat (see Validation):** to *promulgate* under N+1=2 the repair model
  must be distinct from the base AND a second model must close the same goal. **v2 implemented
  — the repair PANEL** (`LEIBNIZ_REPAIR_PANEL`, comma-separated OpenRouter models): the stage
  runs `[primary, *panel]` as independent reasoners and counts *distinct* closers (canonical
  dedup), so two distinct models both closing a goal satisfy N+1 **on their own** — even with
  an empty base. Early-exits once enough distinct closers exist. A specialized-prover drafter
  + frontier repairer is another possible variant.
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
  edge is recorded; a lone repair cannot self-satisfy N+1; **a same-model repair adds no
  vote and a distinct-model repair supplies exactly one** (`_canonical_model` dedup);
  degrades to a safe no-op when the backend can't surface errors. `discharge` remains the
  sole stamper; `test_invariants.py` unchanged.

- **Targeted reach (live, `scripts/measure_repair.py`):** the in-house loop run directly on
  the daemon's real Lean near-misses (goals the ensemble formalized but never closed) — the
  head-to-head with Aristotle's 3/3 harvest. The scaffold closes **~half**: opus **6/11**,
  and during an Anthropic outage the failover backups **5/11** (by glm-5.2 / gpt-5.5 /
  kimi-k2.6, plus opus once it recovered) — **union 7/11**. **Every closed proof was
  independently re-verified — kernel PASS *and* non-trivial.** Round distributions
  (`[1,1,0,1,0,1]`, `[2,0,0,2,1]`) show **~half the wins come *from* repair rounds**, not
  the initial draft — the kernel-error feedback is the lever (HILBERT/LEAP confirmed).

- **Integrated funnel (live calibration, `LEIBNIZ_PROOF_REPAIR=1`):** repair fires as the
  outermost DEMONSTRATE fallback and **closes ~47% of the goals the ensemble + decomposition
  came up short on** (14/30, 19/39 across runs; ~half via repair rounds). The first such run
  **surfaced the N+1 integrity bug we then fixed** (a fixed `repair:*` identity double-counted
  base-opus + repair-opus — see "Why this preserves N+1"); the dedup is now load-bearing.

- **N+1 promulgation — the honest finding:** with the dedup, **sound repair promulgations at
  N+1=2 are ≈0** in the configs measured. Not because repair is weak (its reach is high), but
  because promulgation needs **two distinct models to close the *same* goal**: when opus is
  also a base prover the repair correctly adds nothing, and when the base is distinct
  (deepseek + glm) the specialized provers rarely close the *same* hard goals repair closes,
  so repair is the lone closer (1 < 2). **Takeaway:** repair is a large **reach** lever but
  not, on its own, a **promulgation** lever under N+1=2. The unlock is a *second distinct
  repair reasoner* (two independent repair votes — e.g. opus + gpt-5.5) or an operator
  lowering consensus — deferred to a v2 (N-of-M repair consensus). NB: a pre-fix calibration
  reported 9 "promulgations" that were the opus+opus double-count artifact and must be
  disregarded; the proofs were kernel-true but did not meet independent N+1.

- **Resilience (live):** an Anthropic outage mid-measurement (opus 500s, sonnet 529s)
  exercised `FailoverProvider` end-to-end — all four reasoners (opus/glm/kimi/gpt) closed
  goals; failover is transparent when the primary is healthy.

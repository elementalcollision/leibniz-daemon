# ADR 0028 — Lever 3: stronger proving (options + Aristotle integration)

Status: **Accepted** (2026-06-22) — Aristotle wired; harness A wired; option C drafted in
ADR 0029.

## Context

The instrumented decomposition run (ADR 0027) gave a decisive diagnosis: the binding
constraint is **prover reach**, not the gate, the conjecturer, or decomposition mechanics
(funnel: `attempted 11 · planned 11 · sub-lemmas 3/22 proven · composed 0/3 closed`). The
HF ensemble (DeepSeek-Prover-V2 class) reliably closes only decision-procedure-trivial
goals — which the non-triviality gate correctly filters — so genuinely non-trivial goals
close ~0–1/run. Lever 3 is a **stronger proving capability**.

A web-research sweep (4 streams, fact-checked) surfaced the current Lean 4 / Mathlib
landscape. Integration is always a `ProviderAdapter` (HTTP/SDK in → tactic script out);
the kernel re-verifies every draft under N+1 consensus, so a stronger (even closed,
hosted) prover **cannot weaken the trust boundary** — it only proposes.

## The options (2025-2026)

| Option | What | Access | Gain | Effort |
|---|---|---|---|---|
| **A. Stronger open model** | Goedel-Prover-V2 8B/32B; newer Pythagoras-Prover (~93% miniF2F) | self-host (RunPod A100 ~$1.19/hr; 8B fits one GPU) or Featherless (~$25/mo); OpenAI-compatible | Incremental (8B *beats* DSP-V2-671B; still ~14% on hard goals) | tiny (config) |
| **B. Hosted prover-agent** | **Harmonic Aristotle** — submit Lean+`sorry`, get verified Lean back | hosted API (`ARISTOTLE_API_KEY`); async, min–hrs/proof; paid | large (IMO-2025 gold, ~75% Putnam-2025) | small (provider) |
| **C. Agentic scaffold in-house** | draft → kernel error → frontier reasoner (Claude) repairs → retry, + Mathlib retrieval (HILBERT/LEAP pattern) | reuses Anthropic + a prover adapter + the kernel | largest, aligned with us (HILBERT 99.2% miniF2F / 70% PutnamBench; *the scaffold dominates the raw prover*) | medium (ADR 0029) |
| **D. Tactic-level search** | best-first/stepwise search via `lean-interact` (supports Lean 4.31); HybridProver sketch→refine | self-host plumbing | proven multiplier (HybridProver ~2× solve rate) | larger (off single-shot) |

Not options: Seed-Prover / AlphaProof (no public weights/API); natural-language "IMO"
pipelines (self-verified, **not** kernel-checked — violates the charter).

Sources: arXiv 2606.12594 (Pythagoras), blog.goedel-prover.com, arXiv 2504.11354
(Kimina), arXiv 2509.22819 (HILBERT), aristotle.harmonic.fun.

## Decision

1. **Wire option A by config (harness A).** `prover_ensemble` now reads
   `LEIBNIZ_PROVER_BASE_URL` + `LEIBNIZ_PROVER_KEY_ENV`, so the OpenAI-compatible client
   points at any gateway (Featherless / self-hosted vLLM) serving e.g. Goedel-Prover-V2.
   `scripts/measure_goedel.py` runs a calibration with it. Zero new model code.

2. **Integrate option B (Aristotle) as a provider.** `AristotleProver`
   (`leibniz/providers/aristotle_provider.py`, `propose` extra `aristotlelib`) submits the
   goal as a one-file Lean project, polls the async `AgentTask`, and returns the filled
   proof body. Appended to the ensemble by `LEIBNIZ_ARISTOTLE=1` (off by default). It only
   PROPOSES — `scripts/try_aristotle.py` submits a goal and **re-verifies the returned
   proof with our own kernel** (`LeanVerifier.discharge`), which is the trust check and
   the live validation of the submit→poll→get_files flow.

3. **Draft option C** as ADR 0029 (the highest-leverage, architecture-aligned path) for a
   later build.

## Trust posture

Every option keeps the boundary: the prover/agent proposes; `discharge` (unchanged, sole
`kernel_verified` writer) re-checks under N+1. A hosted agent's own "verification" is
irrelevant — worthless unless our kernel re-checks it. `trust.py`/`verifiers.py`/gates
untouched; `tests/test_invariants.py` byte-identical.

**Note on Aristotle + N+1:** Aristotle alone produces one verified proof per goal; with
the default `min_consensus=2` (distinct provers) it cannot self-satisfy consensus. A
solo-Aristotle experiment therefore needs `LEIBNIZ_PROOF_CONSENSUS=1` — still fully
kernel-verified, but without independent-prover redundancy. `try_aristotle.py` sidesteps
this (it just submits + re-verifies, no consensus).

## Open items (confirmed on first live run)

`aristotlelib`'s exact create→task→poll→retrieve flow has two spots pinned by
introspection but only fully confirmable live (the dashboard docs are auth-gated): whether
`create_from_directory` auto-starts the task (handled defensively via `get_tasks`/`ask`),
and that `get_files` returns the filled `.lean` (assumed; parsed by `_read_proof`). Also
unknown: whether Aristotle wants a bare `.lean` or a full lake project. The first
`try_aristotle.py` run resolves all three.

## Validation

- Unit (CI-safe): `AristotleProver` helpers + submit/poll/parse flow against a faked
  `aristotlelib`; ensemble appends Aristotle on `LEIBNIZ_ARISTOTLE`; base-URL/key-env
  configurable for harness A.
- Live (billable): `scripts/try_aristotle.py "<goal>"` — Aristotle proves, our kernel
  re-verifies. `scripts/measure_goedel.py` — a Goedel-backed calibration.

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

   **Per-model gateway routing (2026-06-24).** `LEIBNIZ_PROVER_BASE_URL` repoints the *whole*
   ensemble; to SPAN gateways, a `LEIBNIZ_PROVER_MODELS` entry may be `model@gateway`, routing
   that one model through `LEIBNIZ_GATEWAY_<GATEWAY>_URL` + `LEIBNIZ_GATEWAY_<GATEWAY>_KEY_ENV`
   (default `<GATEWAY>_API_KEY`; unset URL fails closed). Example — Goedel-Prover-V2 on a
   flat-rate Featherless plan alongside DeepSeek + opus on OpenRouter:
   `LEIBNIZ_PROVER_MODELS="deepseek/deepseek-prover-v2,Goedel-LM/Goedel-Prover-V2-32B@featherless,anthropic/claude-opus-4-8"`
   with `LEIBNIZ_GATEWAY_FEATHERLESS_URL` set + `FEATHERLESS_API_KEY` in env. N+1 keys identity
   on the model NAME, so a model reached via two gateways is still ONE voter — routing is pure
   transport and never touches the trust bar (`_resolve_prover`, adversarially reviewed).

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

## Confirmed live (2026-06-23) — end-to-end success ✅

`scripts/try_aristotle.py "theorem t (n : Nat) : 6 ∣ n*(n+1)*(n+2)"` ran the full loop.
Aristotle returned a complete proof (case analysis on `n % 6`, only the standard axioms
`propext`/`Classical.choice`/`Quot.sound`, no `sorry`) and **our own Lean 4.31 kernel
re-verified it (`kernel_ok=True`)** — the trust model demonstrated end to end: a hosted
agent PROPOSES, our kernel DECIDES.

Three live learnings, now fixed in code:
- **`aristotlelib` is async** — every `Project`/`AgentTask` method is a coroutine;
  `propose` drives them via `asyncio.run` (one loop per ProofConsensus worker thread).
- **`get_files` writes a tarball at a FILE path** (like the CLI's `--destination
  result.tar.gz`), not a directory; `_read_proof` extracts it (`extractall(filter='data')`).
- **Aristotle's Mathlib/Batteries are built for v4.28.0** — submitting our 4.31 toolchain
  forced Aristotle to self-correct down to 4.28 to build. The default submitted
  `lean-toolchain` is now **4.28.0**; the 4.28-produced proof still re-verifies on our
  4.31 kernel. Our re-verify uses `import Mathlib.Tactic` (our image lacks the root
  `Mathlib.olean` aggregate — building it in is the durable fix for full-import coverage).

## Validation

- Unit (CI-safe): `AristotleProver` helpers + submit/poll/parse flow against a faked
  `aristotlelib`; ensemble appends Aristotle on `LEIBNIZ_ARISTOTLE`; base-URL/key-env
  configurable for harness A.
- Live (billable): `scripts/try_aristotle.py "<goal>"` — Aristotle proves, our kernel
  re-verifies. `scripts/measure_goedel.py` — a Goedel-backed calibration.

## As-wired into the standing ensemble (2026-07-04)

Both levers are now live in the operator `.env`, with routing chosen by cost/latency profile:

- **Goedel-Prover-V2 (via Featherless) → STANDING ensemble member.** Featherless is flat-rate
  and OpenAI-compatible; Goedel-V2-8B beats DeepSeek-Prover-V2-671B on miniF2F. It is added
  through ADR 0028 per-model gateway routing — `LEIBNIZ_PROVER_MODELS` now lists
  `Goedel-LM/Goedel-Prover-V2-8B@featherless` alongside `deepseek/deepseek-prover-v2` and the
  `anthropic/claude-opus-4-8` witness (it **replaced** a redundant duplicate `deepseek` entry —
  two identical ids are one voter under N+1). Result: **three distinct kernel-verified voter
  identities** for the `LEIBNIZ_PROOF_CONSENSUS=2` bar. Config:
  `LEIBNIZ_GATEWAY_FEATHERLESS_URL=https://api.featherless.ai/v1/chat/completions`,
  `LEIBNIZ_GATEWAY_FEATHERLESS_KEY_ENV=FEATHERLESS_API_KEY`.
  *Verified end-to-end today:* Goedel-V2-8B proposed a parity proof of `6 ∣ n·(n+1)·(n+2)` and
  **our own Lean 4.31 kernel re-verified it (Q.E.D.)**. Operational note: Featherless returns a
  transient `503` on cold-start/capacity for larger requests — retry with backoff (the smoke
  harness and any standing use should tolerate it); a bare `max_tokens` probe warms the model.

- **Aristotle → ON-DEMAND escalation only, NOT standing.** It is a hosted proof *agent*: billable
  per goal and minutes→hours per run, so appending it to every routine proof is the wrong default.
  `LEIBNIZ_ARISTOTLE` is left unset in `.env` (documented toggle inline). Invoke it deliberately on
  hard goals / kernel near-misses, e.g. `LEIBNIZ_ARISTOTLE=1 python scripts/try_aristotle.py
  --from-memory 3`, or the targeted `scripts/terwilliger_f2b_aristotle.py`. Availability confirmed
  today (`ARISTOTLE_API_KEY` present, `aristotlelib` importable). The kernel re-verifies its output
  exactly as for any other prover — routing never touches the trust bar.

Reusable availability check (no billable Aristotle run; the Featherless leg is flat-rate):
`python scripts/smoke_provers.py`.

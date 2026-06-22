# ADR 0019 — HuggingFace prover backend + first live calibration (Accepted)

- Status: **Accepted** (implemented 2026-06-22)
- Date: 2026-06-22
- Related: ADR 0005/0006 (prover ensemble, N+1 consensus), ADR 0011 (Lean REPL),
  ADR 0014 (cost metering), ADR 0018 (discovery frontier).
  `leibniz/providers/huggingface_provider.py`, `leibniz/providers/__init__.py`,
  `leibniz/providers/openrouter_provider.py`, `assembly.py`,
  `scripts/calibrate_discovery.py`. Non-guarded. Roadmap: Tier 1 (live calibration).

## Context

To run the ADR 0018 frontier live we needed a working prover ensemble. Two blockers
surfaced:

1. **The OpenRouter prover slugs don't exist.** `LEIBNIZ_PROVER_MODELS`
   (`deepseek/deepseek-prover-v2`, …) 404 on OpenRouter — it hosts general DeepSeek
   *chat* models, not the specialized provers. The DeepSeek-Prover-V2 / Goedel-class
   models live on **HuggingFace**.
2. **macOS trust-store gap.** The `urllib`-based providers failed with
   `CERTIFICATE_VERIFY_FAILED` (framework Python's OpenSSL has no CA bundle), while
   the Anthropic SDK worked (it bundles certifi).

## Decision

1. **HuggingFace prover provider.** `HuggingFaceProvider` calls HF's router
   (`router.huggingface.co/v1/chat/completions`, OpenAI-compatible) with
   `HUGGINGFACE_API_KEY`. Proposal-only (returns a tactic draft the kernel checks),
   meters token usage (ADR 0014). Validated live: DeepSeek-Prover-V2-671B returns a
   real Lean proof of `a + b = b + a` in ~3.5s.
2. **Ensemble selection.** `assembly.prover_ensemble` prefers
   `LEIBNIZ_HF_PROVER_MODELS` (HuggingFace) when set, else falls back to
   `LEIBNIZ_PROVER_MODELS` (OpenRouter). HF is the intended prover home.
3. **certifi SSL context.** A shared `providers.ssl_context()` (certifi bundle, with
   a graceful fallback) is used by both `urllib` providers, so live runs don't depend
   on the shell trust store.
4. **Calibration harness.** `scripts/calibrate_discovery.py` seeds the real daemon
   from the curated arXiv feed, turns instrumented cycles (per-cycle frontier
   trajectory + disposition spectrum), enforces a USD cap, and emits a calibration
   recommendation.

All proposal-side; the kernel + Z3 still decide; `tests/test_invariants.py`
byte-identical.

## First live calibration (2026-06-22)

Feed: 101 curated records. Run: 2 cycles × 3 seeds, N+1=2 consensus, HF provers
(DeepSeek-Prover-V2-671B / V3.2 / R1), USD cap $5.

| metric | value |
|---|---|
| conjectured | 10 |
| reached proof | 10 |
| promulgated / kernel-verified | 0 / 0 |
| dispositions | `{unproven: 10}` |
| cost / time | $0.72 / 1055s |

**Findings.** The pipeline runs end-to-end on the real stack. The disposition
spectrum is *pure UNPROVEN* — nothing died at FORMALIZE, novelty, or faithfulness, so
**proving is the sole bottleneck**: research-paper-seeded conjectures sit above the
ensemble's reach (single attempt per prover, 2048-token proof budget). ADR 0018's
mechanisms fired (cycle 1 grew 3→7 seeds via recombination + weakening; `too_hard`
filled), but the frontier's thin-evidence guard correctly held the band at 0.45 across
only 2 cycles — **the controller needs ≥5 cycles to actually steer**.

## Consequences

- Leibniz can prove live against the real prover models it was always meant to use.
- The first measured discovery yield is 0, with a clean diagnosis (proving-bound, not
  formalize/novelty/faithfulness-bound) — the calibration baseline.

## Open questions / next experiments

- **Longer run (≥5 cycles)** so the frontier band adapts past the warm-up gate and the
  prover's reach is found empirically (then tune the default band to it).
- **Prover budget** — raise the proof-draft token budget and/or add proof attempts;
  the novel-yet-tractable band may be reachable only with more proof search.
- **Persist the frontier band** across runs (like ADR 0016 memory) so calibration
  accumulates instead of resetting to the default each run.
- **Faithfulness on prose claims** — all 10 passed faithfulness; verify the
  gaming-witness is biting on the structured contract, not passing vacuously on
  prose-only claims (ADR 0004).
- Clean up `.env` `LEIBNIZ_PROVER_MODELS` (invalid OpenRouter slugs); set
  `LEIBNIZ_HF_PROVER_MODELS` for production.

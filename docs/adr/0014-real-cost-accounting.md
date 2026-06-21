# ADR 0014 — Real (token-based) cost accounting (Accepted)

- Status: **Accepted** (implemented 2026-06-21)
- Date: 2026-06-21
- Related: ADR 0011 (proving throughput & cost — this completes its "precise
  follow-up"). `leibniz/pricing.py`, `leibniz/cost.py`, `leibniz/providers/*`,
  `assembly.py`. Non-guarded. Roadmap: Tier 3 (substrate maturity).

## Context

ADR 0011 shipped a USD cap (`LEIBNIZ_DAILY_USD_CAP`) but priced spend *coarsely*:
`CostBudget.record_calls(n)` multiplied a per-cycle call estimate by a flat
`per_call_usd`. That estimate is blind to model (Opus vs a cheap prover), to prompt
size, and to output length — exactly the variables that dominate real spend on the
"costly by design" N+1 consensus path. Before sustained autonomous discovery runs
(the eventual discovery-frontier work), the cap needs to reflect *actual* spend.

## Decision

1. **Meter real token usage at the provider.** Both providers already receive a
   `usage` block from their APIs; capture it. `AnthropicProvider` reads
   `msg.usage.input_tokens/output_tokens`; `OpenRouterProvider` reads the
   OpenAI-style `usage.prompt_tokens/completion_tokens`. Each provider gains an
   optional `meter` and reports usage best-effort (metering never breaks a
   proposal).
2. **Price through a single table.** `leibniz/pricing.py` holds `$ / Mtok`
   (input, output) per model, with a conservative `DEFAULT_PRICE` for unconfigured
   models (a new prover bills, never silently $0) and per-model env overrides
   (`LEIBNIZ_PRICE_<SANITIZED>=in,out`).
3. **`CostBudget.record_usage(model, in, out)`** accumulates exact spend and token
   totals. The coarse `record_calls(n)` becomes a **fallback that no-ops once real
   usage has been metered**, so wiring the meter never double-counts on top of the
   daemon's per-cycle estimate. The fakes/demo (no real usage) still use the coarse
   path unchanged.
4. **One meter, wired in `build_daemon`.** A single `CostBudget` is passed to the
   autoformalizer, every prover, and the daemon — so the cap sees the whole spend.

## Options considered

- Thread usage through every pipeline return value vs. a meter object the providers
  hold: **meter object** — localizes the change to the providers + assembly and
  keeps the pipeline/daemon signatures stable.
- Hard-coded prices vs. table + env override: **table + override** — prices drift;
  the operator can retune without a code change.

## Consequences

- The USD cap is now exact, not a guess; `$ / promulgation` is measurable
  (`spent_usd`, `input_tokens`, `output_tokens` on the budget).
- Trust unaffected: pricing only sizes a budget; it is never a verdict and touches
  no guarded file. `tests/test_invariants.py` byte-identical.
- The price table is a maintained artifact — stale prices mis-size the cap (not a
  soundness risk). Re-check on model/pricing changes.

## Open questions

- Surfacing per-cycle spend in `CycleReport`/`run_live` output (cosmetic; spend is
  already queryable on the budget).
- Prompt-caching / batch discounts are not modelled (the table is list price).

# ADR 0012 — Autoformalization Robustness: Mechanical Import-Resolver + Output Normalization (Proposed)

- Status: **Accepted** (implemented 2026-06-21)
- Date: 2026-06-21
- Related: ADR 0005 (providers), R4.2 (LLM import-repair); `pipeline.py`,
  `consensus.py`, a new resolver module. Non-guarded. Roadmap item #2.

## Context

The live run's dominant failure was MALFORMED from **stale Mathlib module paths**
(the autoformalizer used `Mathlib.Analysis.SpecialFunctions.Logb`, which no longer
exists in v4.31). R4.2 added an LLM repair loop that fixes this — but it costs a
full model round-trip for what is usually a mechanical "module moved" problem. We
also observed prover models occasionally wrap output in markdown fences / restate
the theorem, which the kernel then rejects on formatting, not logic.

## Decision (proposed)

1. **Mechanical import-resolver, tried before LLM repair.** Ship the real Mathlib
   module index (the ~8169 module names from the pinned image) as a committed data
   file. On a "module … does not exist" compile error: validate each requested
   import against the index; drop invalid ones; for a stale path, fuzzy-match by the
   final path segment(s) to the current module(s) and substitute. Only fall through
   to the (costlier) R4.2 LLM repair if the mechanical fix doesn't compile.
2. **Prover-output normalization.** Before discharge, strip markdown fences and any
   restated `theorem … :=` preamble from prover output so `proof_src` starts at the
   tactic (complements the R4.2 `_join_proof` fix).

## Options considered

- Resolver vs LLM-only repair: **resolver first, LLM fallback** — cheaper,
  deterministic for the common case; LLM handles genuine restatement.
- Ship the module index vs query the container each run: **ship it** (fast, offline;
  regenerate on toolchain bump, like the corpus hashes).

## Consequences

- Far fewer MALFORMED quarantines and fewer paid repair round-trips; candidates
  reach faithfulness/proof reliably (prerequisite for ADR 0009 to bear fruit).
- The module index is toolchain-versioned (regenerate with the Lean image, like
  `corpus/known_results.json`). Non-guarded.

## Open questions

- Fuzzy-match policy when several modules share a leaf name (include top-k vs ask).
- How aggressively to drop unresolvable imports (risking "unknown identifier").

<!--
Baseline finding for the FunSearch track: the LLM-free evolutionary loop (the harness the LLM proposer
drops into) measured as a probe. Informs the GO/NO-GO in docs/funsearch-decision-package.md.
Provenance: docs/results/funsearch_llmfree_probe.json. No trust-boundary change.
-->

# FunSearch LLM-free baseline — the harness works; the non-LLM loop beats nothing (as expected)

**Status:** measured, 2026-06-27. The island/evolutionary loop (`scripts/funsearch_loop.py`) — the exact
harness the billable LLM proposer will drop into — was run with a **deterministic, LLM-free proposer**
over the structural template space (prescribed-group constructions, the proven lever). No LLM, no GPU,
no spend.

## Result (`docs/results/funsearch_llmfree_probe.json`)

| cell | post-Rosin floor | loop best | via | beat? |
|---|---|---|---|---|
| A(14,6,6) | 42 | **42** | sub:7 | matches record |
| A(13,6,5) | 18 | 15 | fixcyc | no |
| A(17,6,4) | 20 | 17 | cyclic | no |
| A(21,6,4) | 31 | 30 | sub:7 | no (one short) |
| A(18,10,6) | 4 | 3 | affsub:13 | no |

**0 beats / 5 cells.** The loop is validated: it is deterministic, it **matches the record where the
structure suffices** (A(14,6,6)=42, where exact CP-SAT got 30 and heuristic search 25), and it
reproduces the known near-miss (A(21,6,4): 30 vs 31) — so a RED here is a real plateau, not a broken
loop. Novelty is judged against the **post-Rosin floor** (`effective_best_known` = max(snapshot, Rosin
2026)); every witness is `verify_cwc`-checked; nothing is promulgated.

## What this means for the GO/NO-GO

This is the **expected** RED, and it is the point: an evolutionary search over our *best deterministic
templates* reaches what those templates can express (≈ the structural sweep: matches many records, beats
none) and no further. It therefore **bounds what a non-LLM loop can do (0 beats) and sets the baseline
the LLM proposer must exceed to justify the spend.**

The LLM proposer's *only* source of additional reach is proposing **genuinely new construction code**
beyond our fixed templates (the FunSearch thesis — and the mechanism behind Rosin's 24 improvements,
which came from novel tabu-search / greedy-histogram strategies an LLM *wrote*, not from fixed group
families). So the GO/NO-GO question is sharpened to exactly one bet: *will an LLM, on un-swept cells,
write construction code that beats our structural baseline?* That is the modest-odds gamble priced in
the decision package — now with every cheap prerequisite (sandbox, evaluator, kernel re-check, oracle,
post-Rosin floor, harness, baseline) **built, sound, and measured**, so a GO spends only on the
irreducibly-uncertain part.

## Disposition

The non-billable FunSearch core is **complete and validated end to end**. The track is paused here for
the operator's GO/NO-GO on the billable LLM pilot (decision package §8). If GO, the LLM proposer slots
into this harness using the untrusted-code sandbox as its evaluator; if NO-GO, the harness + baseline
stand as a reusable, sound asset and the verification-amplification mode remains the strategic home.

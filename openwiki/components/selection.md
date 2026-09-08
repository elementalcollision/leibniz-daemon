---
type: Component
title: Selection (KFM)
description: KFM as a quality-diversity operator over a MAP-Elites archive — kill, recombine (the 'fuck' edge), commit, with curiosity-biased parent sampling toward sparse cells.
tags: [selection, kfm, map-elites, archive, curiosity, recombination, behavior-descriptor]
---

# Selection (KFM)

`leibniz/selection.py` implements KFM as a quality-diversity operator over a MAP-Elites archive (module docstring). KFM's Kill / Fuck / Marry dynamics map onto open-ended discovery:

| Disposition | Meaning |
|---|---|
| `KILL` | refuted/trivial/known/gamed/unfaithful/malformed/over-budget conjectures leave the population (quarantined) |
| `RECOMBINE` | the 'fuck' edge — promising-but-unproven conjectures are recombined into children (LLM-as-variation-operator, lineage tracked) |
| `COMMIT` | the 'marry' edge — proven-and-novel conjectures are committed to the Codex |

## The MAP-Elites archive

`Archive` is a grid keyed by a discretized 3-axis behavior descriptor (`descriptor(prop)` returns `(sub_area, technique, complexity)`):

- **sub-area** — `_unit_hash(f"{claim_type.value}:{subject}")`.
- **proof technique** — neutral (0.5) until a proof is drafted; then the index of the first recognized tactic (`induction`, `ring`, `omega`, `linarith`, `nlinarith`, `aesop`, `simp`, `decide`) normalized, or a hash of the proof.
- **statement complexity** — `min(0.999, len(src) / 240)`.

`consider(prop, quality)` inserts a `Propositio` if it beats the current `Elite` in its cell (the best per cell). `coverage()` is the fraction of the grid occupied. `neighbor_count(key)` counts occupied cells within Chebyshev distance 1.

## Curiosity-biased parent sampling

`select_parents(k)` ranks cells by `_curiosity(key, elite) = (1/(1+neighbor_count), quality)` — **sparser neighbourhood first** (push the frontier outward), quality as tie-break. This avoids re-mining a crowded cell. `recombination_seeds(k)` recombines the top-k parents pairwise into seeds for the next cycle's CONJECTURE (ADR 0009 — closing the KFM → SURVEY loop). `recombine(a, b)` produces a seed that genuinely combines two parents' features, not just mutates.

The daemon's `run_cycles` draws the next cycle's seeds from `kfm.recombination_seeds(recombine_k)` plus weakened near-misses plus a few fresh survey seeds. When the archive is cold (fewer than 2 elites), it falls back to a fresh SURVEY.

See [Discovery Loop](../architecture/discovery-loop.md) for how KFM closes the loop and [Pipeline](../architecture/pipeline.md) for the stages that produce the candidates.

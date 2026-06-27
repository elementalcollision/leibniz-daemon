<!--
Result of the operator-authorized LLM FunSearch pilot (the witnesses' highest-ceiling autonomous
lever). Provenance: docs/results/funsearch_pilot_result_q3cn.json, funsearch_pilot_targets.json.
Closes the autonomous record-beating track per the pre-registered stop rule. No trust-boundary change.
-->

# FunSearch LLM pilot — result: 0 beats over a valid 240-program tranche (track closes)

**Status:** measured, 2026-06-27. The operator-authorized, pre-registered LLM FunSearch pilot ran end
to end: **240 construction programs across 12 cells, 0 records beaten.** Per the pre-registered stop
rule, the autonomous record-beating track **closes**. This is a *bounded-tranche* RED, recorded as a
finding — not a universal impossibility claim.

## The run (valid and interpretable)
Model `qwen/qwen3-coder-next` (non-reasoning coder), CPU, every program executed in the untrusted-code
sandbox and scored by `verify_cwc`; novelty judged against the post-Rosin floor; a beat would have been
Lean-kernel re-checked. Health was good — **15–20 of 20 programs valid per cell**; the few
`invalid`/`sandbox_fail` cases were markdown-fence and non-ASCII (≤) artifacts and a couple of buggy
programs, not failed mathematics. Provenance: `docs/results/funsearch_pilot_result_q3cn.json`.

The "best structural" column below is the **max over both structural runs** (the automorphism sweep and
the richer-group run); `0` means the structural method returned **no valid code** for that cell (a
sweep-only cell the richer-group run did not cover). This is the honest baseline — an earlier draft
cherry-picked the weak cyclic-only `0` on the floor-2/3 cells while using the strong richer-group `30`
on A(21,6,4); the adversarial review caught it.

| cell | floor | LLM best | best structural¹ | LLM vs structural | vs record |
|---|---|---|---|---|---|
| A(18,10,6) | 4 | **4** | 3 (sweep+rg) | **exceeded** | matched record |
| A(17,10,6) | 3 | 3 | 0 (sweep-only) | **exceeded** | matched record |
| A(13,8,6) | 4 | 4 | 0 (sweep-only) | **exceeded** | matched record |
| A(19,10,6) | 4 | 4 | 0 (sweep-only) | **exceeded** | matched record |
| A(17,10,7) | 5 | 5 | 0 (sweep-only) | **exceeded** | matched record |
| A(11,8,5) | 2 | 2 | 2 (richgroup) | tied | matched record |
| A(13,10,6) | 2 | 2 | 2 (richgroup) | tied | matched record |
| A(15,12,7) | 2 | 2 | 2 (richgroup) | tied | matched record |
| A(17,12,8) | 2 | 2 | 2 (richgroup) | tied | matched record |
| A(17,14,8) | 2 | 2 | 2 (richgroup) | tied | matched record |
| A(13,8,5) | 3 | 3 | 3 (richgroup) | tied | matched record |
| A(21,6,4) | 31 | 29 | 30 (richgroup sub:7; sweep 28) | **below** | short by 2 |

¹ `0` = the structural orbit method produced no valid code for that cell.

**11/12 matched the record; 0 exceeded any record.** Against the daemon's *own best prior method*
(structural): the LLM **exceeded it on 5 cells, tied it on 6, and was below it on 1** — and the one it
lost was A(21,6,4), the single genuinely-open flagship cell, where the richer-group structural search
(30) still edges the LLM (29).

## What it means (honestly)
- **The lever works, and on some cells it out-reaches the fixed templates.** On 5 of 12 cells LLM-
  written constructions exceeded the daemon's best structural result — most clearly A(18,10,6) (4 vs 3,
  where both structural runs got 3), and the four sweep-only cells where the orbit method produced no
  valid code at all. The pipeline is sound end to end: propose → sandbox → verify → oracle → (kernel on
  a beat). But on 6 cells the LLM only *tied* the richer-group structural baseline (both matched the
  record — a tie, not a beat of the baseline), and on the flagship open cell it did *worse*. So "more
  capable than the templates" is partly true, not uniform.
- **It exceeded no record.** The same wall as every prior lever, now at the highest-ceiling autonomous
  method: *reaching/matching* records is tractable; *beating* them is not, within a bounded autonomous
  tranche. Tellingly, on the one genuinely-open flagship cell (A(21,6,4), floor 31) the LLM got 29 —
  below even the richer-group structural 30 — so a stronger proposer did not close the beat-gap there.
- **Caveats kept explicit (this is a bounded RED):**
  - One model, one CPU tranche, 240 programs, 12 cells. A larger budget / different model / GPU-island
    scale was *not* run (it would require a separate operator GO per the pre-registration).
  - Six target cells have floor 2 and the beat-surface was thin: on any cell whose record is actually
    optimal, no larger code exists, so a beat is impossible by construction (`verify_cwc` can never
    confirm one) and "matched" is the best achievable.
  - This does **not** prove no LLM construction can ever beat any cell; it is the measured outcome of
    the pre-registered tranche, which is exactly what the stop rule was written to act on.

## Disposition — the autonomous record-beating track is closed
Per the pre-registered stop rule (`docs/funsearch-pilot-preregistration.md`): **0 kernel-verified beats
after the full budget → close the track; record the RED; do not silently retry or expand the budget.**

The autonomous arc has now been pushed through **every** lever the witnesses named — exact (CP-SAT),
heuristic, structural (cyclic/affine/subgroups), richer-structural (multiplier/dihedral/fixed-point),
and **learned construction (LLM FunSearch)** — over 78 + 13 + 12 cells. **Matches many records; beats
none.** The daemon's honest standing is unchanged and now maximally tested: a *sound verification /
non-Q.E.D. decision* instrument that reaches and proves records behind an unbroken trust boundary, but
does not autonomously exceed them. The strategic home remains **verification amplification**.

Re-open only on a *separate* operator decision (GPU/island scale, a different proposer, or new
human-supplied frontier content to check). The reusable assets — sandbox, evaluator, harness, Lean
witness-checker, post-Rosin oracle — stand regardless. Trust boundary intact throughout;
`tests/test_invariants.py` byte-identical; no LLM ever decided.

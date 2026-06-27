<!--
Capstone of the post-R6 AUTONOMOUS discovery investigation (the operator's "push the autonomous track"
directive). Ties together three sound backends (Walnut, SOS, CWC record-factory) and the full
producer-side method sweep. Concludes the autonomous arc. Provenance: all docs/results/*.json below.
No trust-boundary change; tests/test_invariants.py byte-identical across the entire arc.
-->

# Capstone — the autonomous discovery arc: sound, measured, and concluded

**Status:** concluded, 2026-06-26. The autonomous track was pushed end-to-end across **three independent
sound backends** and, in the record-factory backend, across **every tractable producer-side method**. The
verdict is consistent and now definitive: **the daemon reliably produces correct, diverse mathematics
behind an unbroken trust boundary, and it does not autonomously reach novelty.** The binding constraint is
the *producer* — what it can encode and how it constructs — not soundness, prover reach, or compute.

This document closes the arc the operator directed ("push the autonomous track"). It does not relitigate
the per-probe findings; it states what the whole sweep adds up to and what carries forward.

## The arc in one table

| backend / domain | what was measured | beats / novel | the wall |
|---|---|---|---|
| **Walnut** (automatic-sequence FO) — built, run live ×3 | 11 sound, diverse, faithful decided records | 0 novel (12-agent panel: all textbook) | checkable properties of famous words *are* the studied ones |
| **SOS / Positivstellensatz** (∀x∈ℝⁿ) — probed | 24 conjectures, 2 arms, scored in-reach × box-OUT × non-textbook | 0 in GREEN intersection (both arms) | frontier objects leave the finite semialgebraic class |
| **CWC record-factory** (A(n,d,w) lower bounds) — built, swept | 78+13 cells × {exact, heuristic, structural, richer-structural} | **0 records beaten** | tractable cells already optimal; records need research-grade construction |

Three domains, three encodings, one outcome. The first two are detailed in
`docs/discovery-ceiling-cross-backend-finding.md`; this capstone adds the third and what it uniquely shows.

## What the record-factory backend added: a producer-*method* sweep

The Walnut and SOS probes showed the producer cannot *encode* frontier content in a backend-consumable
form. The CWC backend removed that excuse entirely — A(n,d,w) lower bounds **are** finite, self-contained,
Lean-checkable witnesses, and novelty is an objective lookup against a public table of record (Brouwer,
839 cells, automated oracle with ground-truth + monotonicity validation). Here the producer's *encoding*
is not the bottleneck; its *construction method* is. So we swept the method axis exhaustively:

1. **Exact** (CP-SAT max-clique, 8 workers, ≤90 s/cell): matched best-known, **proved several cells
   optimal** — but on A(14,6,6) a strong solver found only 30 vs the known 42. *A generic exact solver
   cannot even match a clever construction.* → 0 beats.
2. **Heuristic** (stochastic greedy + penalty/swap local search): *weaker* than CP-SAT (25 vs 30 on
   A(14,6,6)). This killed the "naive massively-parallel construction" sleeper — parallelizing a method
   that loses to CP-SAT won't reach records. → 0 beats.
3. **Structural** (automorphism-prescribed: cyclic / affine / cyclic subgroups; a G-invariant code is a
   union of G-orbits → tiny max-weight clique on the orbit graph): the decisive positive — on A(14,6,6),
   cyclic-orbit search reached the record **42 instantly** where exact got 30 and heuristic 25, and the
   broad sweep **MATCHED 41/78 (53%) of records**. → still 0 beats.
4. **Richer-structural** (affine multiplier-subgroups incl. dihedral; fixed-point cyclic): closed 6 more
   near-misses to MATCH and pushed A(21,6,4) to **30 vs 31 — one codeword short**. → still 0 beats.

**The new, genuine refinement of the ceiling thesis: structure is the lever.** Brute search (exact or
heuristic) plateaus far below records; the right *symmetry assumption* reaches them — but only up to the
record. Beating it requires the specific construction structure the record itself uses (quasi-cyclic,
algebraic, non-group, or learned), which the daemon's fixed group families cannot synthesize. The producer
constraint is real even when encoding is free: **matching is structural; beating is research-grade.**

## Why this is a real result, not a failure

- **The trust machinery is vindicated a third time.** CWC: a core-Lean `decide`-closed `A(n,d,w) ≥ M`
  theorem, **kernel-ACCEPTED** for a true witness (the first Q.E.D. of the whole arc) and
  **kernel-REJECTED** for a false one; every search output re-checked by `verify_cwc`; novelty by
  automated oracle, never LLM-judged. No LLM decided anything; `tests/test_invariants.py` byte-identical
  across all 22 PRs of the arc.
- **Two reusable, sound assets ship regardless of the RED:** the Lean witness-checker and the automated
  table-of-record oracle are exactly what a *human-proposes / daemon-soundly-checks* system needs.
- **A minor but real mathematical by-product:** several "non-exact" Brouwer cells were independently
  **proved optimal** (the search supplied the missing upper-bound proof).

## Disposition — the autonomous track is concluded

- **Autonomous record-beating: RED and closed across EVERY lever.** 0 beats across exact, heuristic,
  structural, richer-structural (78+13 cells), AND learned construction (LLM FunSearch, 12 cells / 240
  programs). The autonomous method space — including the witnesses' highest-ceiling lever — is genuinely
  exhausted; closest result is one codeword short, and even closing it yields a MATCH, not a beat.
- **The strategic home stands: verification amplification.** The daemon's defensible identity today is a
  *sound verification / non-Q.E.D. decision* instrument — it reliably produces correct, diverse, textbook
  mathematics and *proves* records behind an unbroken trust boundary. "Decided" and "sound" are not
  "novel," and the daemon now measures the difference honestly across three backends.
- **The last lever — FunSearch-style learned construction — was then pulled, and is RED too (2026-06-27).**
  Operator-authorized as a bounded CPU-first tranche. An LLM (`qwen/qwen3-coder-next`) proposed
  construction *programs*; each ran in an untrusted-code sandbox, scored by `verify_cwc`, judged against
  the post-Rosin floor, with any beat Lean-kernel re-checked. **240 programs over 12 pre-registered cells:
  0 records beaten.** The LLM matched the record on 11/12 and *out-reached* the daemon's own structural
  baseline on 5 cells — but exceeded no record, and on the one genuinely-open flagship cell (A(21,6,4))
  it did *worse* than the richer-group structural search (29 vs 30 vs record 31). Per the pre-registered
  stop rule the track **closes**. This is a bounded-tranche RED (one model, CPU, 240 programs), not a
  universal impossibility — re-open needs a separate operator GO (GPU/island, another model). Detail:
  `docs/funsearch-pilot-result-finding.md`; provenance `docs/results/funsearch_pilot_result_q3cn.json`.
  The reusable assets (untrusted-code sandbox, LLM-free evaluator, evolutionary harness, post-Rosin
  oracle cross-check) stand regardless.
- **Kernel bridge (task #54) stays gated.** Adding a fourth sound backend faces the same producer
  constraint, now confirmed three times; building it for discovery yield is not justified by these data.

## The re-open gate

The autonomous discovery track re-opens — without relitigating any of the above — when **one** of these
changes:
1. a producer-side encoder/self-check lifts the SOS novelty micro-probe to a non-empty GREEN intersection
   in the default arm (the gate in the cross-backend finding); or
2. the operator green-lights a *larger* FunSearch tranche — GPU/island scale, a different/stronger
   model, or a wider cell set — beyond the bounded CPU pilot that came back RED (2026-06-27); or
3. a human supplies frontier conjectures/constructions for the daemon to *soundly check* — the
   verification-amplification mode, which the built assets already support today.

Until then: the autonomous arc is complete, sound, honestly measured, and banked.

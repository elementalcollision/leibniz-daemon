<!--
Gate D0 (ADR 0041 producer-wall diagnostic) result. Provenance: docs/results/gate_d0_result.json.
Decision-determining for the ADR 0041 autonomous-discovery phases. No trust-boundary change.
-->

# Gate D0 — the producer is the wall, not the encoding (RED)

**Status:** measured, 2026-06-27. The ADR 0041 producer-wall / expressivity diagnostic ran and came back
**RED**: on 5 cells where the daemon's autonomous search fell short, an exact producer found the record
construction and the **Lean kernel verified all 5**. The binding constraint is producer
**strength/reach** — decisively *not* encoding/representation and *not* the checker.

## What was tested
For each of 5 open Brouwer cells where the daemon's autonomous *structural* search fell short of the
record, obtain a record-size code by **exact CP-SAT** (a stronger, non-heuristic producer) and re-verify
it with the **real Lean kernel** via `scripts/cwc_check.py`.

| cell | record | structural (daemon) | exact found | Lean kernel |
|---|---|---|---|---|
| A(13,8,5) | 3 | 0 | 3 | **KERNEL-VERIFIED** |
| A(13,8,6) | 4 | 0 | 4 | **KERNEL-VERIFIED** |
| A(13,6,5) | 18 | 13 | 18 | **KERNEL-VERIFIED** |
| A(17,6,4) | 20 | 17 | 20 | **KERNEL-VERIFIED** |
| A(21,6,4) | 31 | 30 | 31 | **KERNEL-VERIFIED** |

**5/5 records reached and kernel-verified — every one missed by the daemon's structural producer**,
including the flagship one-short cell A(21,6,4) (structural 30 → exact 31). Provenance (with the actual
witnesses): `docs/results/gate_d0_result.json`.

## The verdict — RED
The ADR's RED branch: *the kernel verifies constructions the daemon never found ⇒ the bottleneck is the
producer.* Concretely:
- **No representation/encoding gap for CWC.** Every record construction is a finite, kernel-checkable
  witness; GREEN (expressivity gap) is falsified — there is nothing for tool-building to "encode better."
- **The wall is producer strength/reach.** A stronger producer (exact CP-SAT) found all 5 records the
  daemon's bounded structural search missed.
- **But stronger producers MATCH, they don't BEAT.** Consistent with the full autonomous arc (exact
  CP-SAT + LLM FunSearch over 100+ cells): matched many records, **beat none**. Reaching is tractable;
  *exceeding* is research-grade. Autonomous **novelty stays RED**.

## Implication (decision-determining)
1. **Do not invest in tool-building to fix "representation."** There is no encoding gap; that lever is
   empty for CWC.
2. **Phases 5–6 (autonomous discovery / decider-admission) and the FunSearch GPU bet are NOT justified
   for autonomous *novelty* by these data.** A stronger producer reaches records but does not beat them;
   nothing here moves the beat-wall.
3. **The justified home is verification amplification.** A stronger or human producer supplies a
   construction; the daemon soundly verifies it. This is *demonstrated, working* capability — D0 just
   kernel-verified 5 records, and the end-to-end demo earlier kernel-verified a 42-codeword A(14,6,6).
   That is what Leibniz is today: a sound verification instrument for finite-witness mathematics.

The tool-using + research-seeding substrate (ADR 0041 Phases 1–4) remains valuable precisely for that
amplification mode — it lets external/stronger producers and ingested research feed the daemon's sound
checker. What D0 forecloses is the *autonomous-discoverer* narrative, exactly as the measure-before-build
gate was designed to settle.

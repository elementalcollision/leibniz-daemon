# ADR 0009 — Close the KFM → SURVEY Discovery Loop (Proposed)

- Status: **Proposed**
- Date: 2026-06-21
- Related: ADR 0001 (charter), capability-ladder R5; `selection.py` (KFM/Archive),
  `daemon.py` (`_settle`). Optimization roadmap item #1 (highest leverage).

## Context

The daemon runs end-to-end but rarely promulgates: live cycles produce conjectures
that are either trivial (caught by non-triviality) or too hard (UNPROVEN). The
machinery for open-endedness exists — a MAP-Elites `Archive`, `KFM.disposition`
(KILL/RECOMBINE/COMMIT), `KFM.select_parents` (curiosity-biased), `KFM.recombine`
— but the loop is **not closed**: `daemon._settle` computes the disposition and
then `pass`es; recombined/proven parents never re-seed `SURVEY`. So each cycle
starts cold and the daemon never *learns* where the provable, novel ground is.

## Decision (proposed)

Make discovery a feedback loop across cycles:

1. **Re-seed from the archive.** After `_settle`, draw curiosity-biased parents
   (`KFM.select_parents`) and produce next-cycle seeds via `KFM.recombine`, mixed
   with fresh `SURVEY` seeds. The daemon gains a multi-cycle loop (today's
   `circadian_cycle` is single-shot).
2. **Difficulty targeting.** Bias parent selection toward cells whose elites
   reached DERIVE / Q.E.D. (provable neighborhoods) *and* toward sparse cells
   (frontier) — the quality-diversity trade. Promulgated laws are the strongest
   recombination parents.
3. **Stagnation re-seeding.** When the archive stops growing for K cycles, re-seed
   `SURVEY` from the frontier/Leonardo (borrow Chimera's drift signal later).

## Options considered

- **(a) Re-seed from recombined/proven parents — proposed.** Turns the daemon into
  a learning discovery engine; reuses KFM/Archive already built.
- (b) Fresh survey every cycle (status quo). No learning; promulgation stays rare.
- (c) External fixed curriculum. Loses open-endedness; not the charter.

## Consequences

- Requires a real multi-cycle daemon loop + wiring `select_parents`/`recombine`
  into `Conjecture` seeding. Non-guarded (`daemon.py`, `selection.py`).
- **Exit metric:** over N cycles, archive coverage grows and ≥1 novel, non-trivial
  theorem promulgates with no human on the critical path (the R4 exit test).
- Pairs with ADR 0012 (so candidates reliably compile) and ADR 0011 (so volume is
  affordable).

## Open questions

- The recombination operator's strength (prose merge vs structured feature mix).
- How aggressively to bias toward provable vs novel (the QD knob).

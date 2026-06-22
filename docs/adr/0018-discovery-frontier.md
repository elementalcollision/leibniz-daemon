# ADR 0018 — The discovery frontier: steering toward the novel-yet-tractable (Accepted)

- Status: **Accepted** (implemented 2026-06-21)
- Date: 2026-06-21
- Related: ADR 0009 (KFM→SURVEY loop, selection-side), ADR 0005/0006 (consensus
  proving), R5 (KFM/MAP-Elites). `leibniz/discovery.py`, `leibniz/daemon.py`,
  `leibniz/providers/anthropic_provider.py`, `assembly.py`,
  `scripts/measure_discovery.py`. Non-guarded. Roadmap: Tier 1 (the mission).

## Context

The daemon runs end-to-end but rarely promulgates: conjectures land **trivial**
(killed by the novelty / decision-procedure gates) or **too hard** (the prover
exhausts its budget → UNPROVEN). The mission is *novel, tractable, kernel-proven*
theorems, so the central problem is hitting the narrow band of the
**novel-yet-tractable**.

Diagnosis of why that band is missed:

1. **The learning loop is open on the *proposal* side.** ADR 0009 closes it on
   *selection* (KFM recombines surviving stepping stones), but the conjecturer —
   where the text is actually generated — receives only a bare seed string. It
   never learns that shapes like X proved, shapes like Y were trivial/known, or
   shapes like Z were too hard. It repeats its mistakes.
2. **No difficulty calibration.** "novel + non-trivial + plausibly-true" is a blunt
   prompt with no provability signal; to escape *trivial* it drifts to *too hard*.
3. **Too-hard near-misses are wasted.** An UNPROVEN candidate often hides a provable
   lemma, but nothing weakens or decomposes it.
4. **Quality is `{1.0, 0.5, 0.0}`** — no gradient, so selection cannot steer toward
   the tractable frontier.

## Decision

Add a **proposal-side** discovery layer. Everything here shapes what is *proposed*
and how stepping stones are *scored*; it writes no trust edge and mints no verdict.
Every candidate it influences still runs the full cheap gates (Z3 refute → novelty →
faithfulness) and the kernel's N+1 consensus — **the kernel and Z3 still decide**, so
the trust boundary is untouched (`tests/test_invariants.py` byte-identical).

`leibniz/discovery.py`:

- **M1 — Outcome-conditioned conjecturing.** A bounded `DiscoveryNotebook` ingests
  each settled candidate's outcome and distils a steering block: *proven* shapes to
  emulate, *trivial/known* shapes to avoid, *too-hard* shapes to weaken. A
  kernel-proved shape counts as *proven* to emulate even if held back at promotion
  (OVER_BUDGET) — the proof was real, only the judged-faithfulness budget refused it.
  Fed into the CONJECTURE context (`steer()`), closing the loop where generation
  happens.
- **M2 — Frontier controller (curriculum thermostat).** `FrontierController` holds a
  target proof-SUCCESS RATE and steers the proposal band so its tractable tail
  overlaps the prover's (unknown) reach. It does **not** claim to centre on the reach
  — with a proposal spread the band edge overlaps it. Two robustness properties:
  *proportional homing* (step shrinks near the aim, so it settles smoothly instead of
  freezing at the first in-band rate) and *re-exploration* (if it pins a bound with
  zero success it jumps to the opposite half with a varying offset, so a narrow window
  is eventually straddled rather than pinned at 0% forever). It tracks **provability**
  (kernel-verified), not promulgation, so a budget-refused-but-proved candidate is a
  tractable difficulty, not a miss.
- **M3 — Weakening seeds (lemma mining).** UNPROVEN near-misses spawn strictly-weaker
  re-conjecture seeds (`weakening_seeds`), fed back through the *same gated pipeline*;
  a trivial weakening is caught by the gates, a provable non-trivial one is a real
  (if modest) discovery and a stepping stone. Bounded to **depth 1** — a weakening of
  a weakening is not re-weakened — which terminates the chain and kills any compounding
  loop.
- **M4 — Graded quality + mechanical difficulty.** `difficulty()` is a structural
  proxy (quantifiers, implication depth, operator density, length); `quality()` grades
  faithful-but-unproven stepping stones with a **tent peaking at a moderate (frontier)
  difficulty**, so a genuine near-miss outranks *both* a vacuous trivially-shaped
  statement and a wild open-problem shape (a plain `1 − difficulty` rewarded simpler
  text). Always in 0.40–0.60, strictly below a real proof.
- **M5 — Measurement.** `scripts/measure_discovery.py` is a deterministic simulation:
  (1) on a wide window far from the start, the thermostat lifts steady-state yield
  0% → ~50% while a static run stays at 0%; (2) on a *narrow* window the band
  overshoots, re-exploration recovers (finds a proof) where a plain deadband
  controller would pin the floor at 0% forever.

The daemon holds an optional `DiscoveryNotebook` + `FrontierController`; `_settle`
feeds outcomes back, `_run_seeds` steers each conjecture, `_next_seeds` adds
weakening seeds, `run_cycles` retunes the band per cycle. All optional — absent them
(deterministic fakes / cold start) the loop behaves exactly as before.

## Options considered

- Steer via the seed string vs. a new pipeline stage / new Role: **steer the seed
  context** — keeps the pipeline and providers unchanged, concentrates the new
  intelligence in `discovery.py` + daemon wiring, and keeps it provably proposal-only.
- A learned difficulty model vs. a structural proxy: **structural proxy** — cheap,
  deterministic, testable, and good enough to target a band and grade stepping stones.
- Weakening as a new stage vs. as seeds re-entering the loop: **seeds** — reuses the
  existing gated pipeline, so weakenings get the same novelty/faithfulness/kernel
  scrutiny as any conjecture (no special path that could leak junk).

## Consequences

- The proposal side now learns: the conjecturer is conditioned on what proved, what
  was trivial/known, and what was too hard, and targets an adaptive difficulty band.
- Too-hard near-misses are mined into provable weaker cousins instead of discarded.
- Selection steers toward the tractable frontier via a graded quality.
- Trust unaffected — proposal-side only; the gates + kernel still decide; no guarded
  file touched; invariants byte-identical.
- **Pollution is bounded to proposal memory, never the Codex.** A steered or weakened
  candidate that is trivial/known/unfaithful is quarantined by the gates exactly like
  any conjecture — it can occupy an archive cell or a notebook slot (a search-quality
  cost), but it can never be promulgated, because every candidate still runs the cheap
  gates and the kernel's N+1 consensus.

## Open questions

- The difficulty proxy is structural, not semantic; a learned/elaborator-informed
  estimate could target the band more precisely.
- Live calibration: the demo shows convergence in simulation; a sustained live run
  (with real providers + Lean) is the next measurement, and the window/step constants
  may want tuning against real prover reach.
- Decomposition (extracting a named lemma and proving it) is a deeper form of M3 left
  for future work.

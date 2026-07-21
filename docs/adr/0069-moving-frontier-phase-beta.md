# ADR 0069 — The moving frontier: Phase β of the autonomy plan

- Status: accepted
- Date: 2026-07-21
- Depends on: ADR 0068 (the heartbeat), ADR 0018/0019/0023 (steering loop + band + notebook
  persistence), ADR 0034 (genre-kill + exemplars), ADR 0033 (operator publish gate)

## Context

Phase α gave the daemon a pulse; Phase β makes the motion *forward* motion. The plan named
two gaps: (1) a static frontier — nothing retires mined-out ground or feeds new ground in;
(2) manual amplification — the daemon's proven best work (kernel-checking the finite core
of a fresh published result) begins with a human reading arXiv listings.

Investigating (1) surfaced that much of the steering machinery already exists —
`run_cycles()` rotates domains, recombines from the KFM archive, weakens near-misses, and
retunes + persists the frontier band and notebook — **but the Phase α beat called the bare
`circadian_cycle()`,** which takes a fresh survey every time and throws all of that away.
The largest single Phase β gain was wiring the beat to the loop that was already built.

## Decision

Three pieces, all proposal-side; zero new trust edges.

### β1 — the beat turns the full steering loop

`heartbeat.beat()` now calls `daemon.run_cycles(n)` instead of N× `circadian_cycle()`.
Each nightly beat therefore: rotates the survey across domains (D9), recombines
curiosity-biased parents from the archive, re-conjectures strictly-weaker variants of
recent UNPROVEN near-misses (ADR 0018 M3), retunes the difficulty band from outcomes
(ADR 0018 M2), and persists both band and notebook — so steering state accumulates
*across nights*, not just within a run. The journal entry gains a `steering` block
(genre_kill, dry_kill, too_hard count, band target): the morning read shows where the
frontier moved. Known limitation: the KFM archive itself is in-memory, so cross-beat
recombination cold-starts each night (within-beat recombination works; archive
persistence is future work).

### β2 — dry-ground retirement (`DiscoveryNotebook.dry_kill`)

The mirror of ADR 0034's `genre_kill`, which retires families *exhausted by success*.
`dry_kill` retires families exhausted by **failure to be new**: a coarse family
(`_family` — relop × modulus) that accumulates `dry_threshold` (default 4) KNOWN/TRIVIAL
outcomes while having **never once proven** here is declared dry ground, and the
conjecturer is steered to structurally different territory. Design points:

- Only KNOWN and TRIVIAL count as dryness — they are the novelty/triviality wall three
  origination hunts confirmed. REFUTED/GAMED/MALFORMED are proposer noise, not evidence
  about the ground.
- A family that has ever proven cannot be declared dry, and a later proof in a dry family
  **rehabilitates** it (removed from the list, dry evidence reset): productive-with-chaff
  ground stays open.
- Same discipline as the genre state: bounded list (`genre_capacity`), bounded histogram
  (`_FAMILY_CAP`), persisted in the notebook, defensive `from_dict`, and it only ever
  STEERS — the gates and the kernel still decide every candidate.

"Promote regions producing near-misses" remains statement-level (the existing ADR 0018 M3
weakening loop, now actually running nightly via β1); family-level promotion is deferred
until the journal shows it is needed.

### β3 — the external frontier feed (`leibniz/arxiv_feed.py`)

A periodic sweep of recent arXiv submissions in the daemon's domains (math.NT, math.CO,
math.AG, quant-ph — the KS-set precedent) proposing **amplification targets**. Each
abstract is scored by deterministic finite-core signals (exhaustive/computer search,
non-existence claims, classification/census, explicit certificates, named finite
structures, srg parameter tuples, explicit small orders); papers at/above the queue
threshold are appended to `.leibniz/amplification_queue.jsonl` and rendered into an
operator-readable `amplification_queue.md`, deduplicated against a bounded seen-set.

Trust posture, stated bluntly:

- **LLM-free and judgment-free.** Scoring is keyword/regex evidence; the only decision
  this code makes is *queueing*. A queued entry is a TARGET, not a result — nothing is
  verified, endorsed, or claimed by appearing in the queue, and the queue file says so.
- Amplification itself remains the established operator-driven act: formalize the finite
  core → kernel → ADR 0033 publish. The feed only replaces the *reading of listings*.
- Wired into the beat behind `LEIBNIZ_ARXIV_FEED=1`; one polite request per beat
  (stdlib urllib, identified User-Agent); any failure degrades to a journal note — the
  beat never depends on arXiv being up at 02:30.
- Future increment (not in β): validated queue entries flowing into cycles as
  `SeedKind.TARGET` steering seeds via the existing `seeds.py` guards.

## Consequences

- Nightly beats now *learn*: dry families retire, near-misses get ground down by
  weakening, the band follows the prover's reach, and the state survives between nights.
- The operator wakes to two queues: laws awaiting the publish word (`review_queue.md`)
  and fresh literature targets awaiting an amplification decision
  (`amplification_queue.md`).
- The scorer's recall is unknown and its precision will be tuned from use; the journal's
  `arxiv_feed` counts make its behaviour observable. Missed papers cost nothing (the old
  manual path still works); queued noise costs one operator glance.

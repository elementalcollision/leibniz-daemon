# ADR 0091 — The feed must see a paper before any signal can score it

- Status: **accepted — landed, measured against the live arXiv API and a labelled corpus**
- Date: 2026-09-07
- Depends on: ADR 0069 (the feed), ADR 0083 (queued targets steer the conjecturer), ADR 0084
  (finite-core parameter extraction), ADRs 0060/0065/0070 (the arithmetic procedures the scorer
  was blind to), ADR 0090 (which unblocked the paper this ADR is about)

## Context

The daemon has now kernel-decided and published arXiv 2607.19029 as a law. Its feed scored that
same paper **zero**. Fixing the scorer was the obvious response; measuring first found a second,
larger defect underneath it.

## Decision 1 — page the sweep, and say when it truncates

`fetch_recent` issued ONE request for the 80 newest entries, then client-filtered to a 4-day
window. Measured against the live API on 2026-09-07: **at least 121 papers existed in that same
window**, so the nightly beat swept about **66%** of what it claimed — with no log line, nothing in
the journal, and no way to tell an under-swept beat from a quiet night.

The loss was also **biased against exactly the papers the daemon can decide**. arXiv returns
newest-first across the whole category union, and quant-ph dominates by volume (27 of 80 leading
categories on that sweep, against 11 for math.NT), so the ~41 papers falling off the end were the
oldest in the window and disproportionately arithmetic.

`fetch_recent_detail` pages until the results run older than the cutoff — the real stopping
condition — and returns `{entries, seen, pages, truncated}`. `truncated` is True when paging stops
with everything still inside the window, i.e. more papers exist that were not fetched. `run_feed`
carries `swept`, `pages` and `truncated` into the beat journal. Measured after: 121 in-window
papers fetched, `truncated=False`.

**No signal set could have rescued a paper that was never fetched.** This is the more important
half of the ADR and it was invisible from the code.

## Decision 2 — give the scorer vocabulary for the daemon's own arithmetic procedures

Every one of the eight shipped signals named a finite **combinatorial** structure — strongly
regular graphs, Latin squares, Hadamard matrices, Steiner systems, cap sets. The daemon has three
arithmetic kernel decision procedures (ADRs 0060, 0065, 0070) and the scorer had no word for any of
them. That is why the covering-system paper scored zero, and the near-misses were all phrasing:

| the abstract said | the pattern wanted | result |
|---|---|---|
| "certified by" | `certificate\|witness` | no match |
| "minimum modulus" | `minimum (number\|size\|order\|counterexample)` | no match |
| "complete Gurobi computations" | `complete (list\|enumeration)` | no match |

Four signals added, one widened, threshold 3 → 4. The new ones name what the daemon decides
(covering systems, residue classes, multiplicative order), a modulus or lcm **stated with a
number**, an explicit parameter tuple, and solver evidence (Gurobi, SAT, ILP) — because a paper
whose hard part is a bounded computation is precisely what a kernel can re-decide.

A deliberate non-signal: a bare topic word does not score. "Least common multiple" with no number
is a *subject*, not an extractable core; the signal is a modulus stated **with a value**. That is
the same insight ADR 0084 already encodes in its parameter shapes, and without it every analytic
number-theory abstract in the sweep would queue.

## Method — and why the measured numbers here are the modest ones

710 recent papers were fetched, 108 stratified into a labelled sample (everything the old scorer
queued, the arithmetic families it was blind to, and random controls). Nine agents labelled them
against the daemon's *actual* fragment limits; a tenth re-labelled a fifth of them independently
and agreed **22/22**, so the ground truth is solid.

Four signal sets were then designed independently and each **measured, not estimated**. All four
reported strong numbers. **All four were overfit**, and the held-out test says so:

| proposal | train precision | held-out precision |
|---|---|---|
| widen-existing | 0.708 | **0.143** |
| solver-evidence | 0.944 | **0.375** |
| arithmetic-structure | **1.000** | **0.300** |
| precision-first | **1.000** | **0.667** |

The two that scored *perfectly* on the tuning set collapsed hardest, and carried the most patterns
matching a single paper. Held-out papers were pooled across proposals and labelled blind, with the
which-proposal-queued-which mapping kept in a separate file.

The set that shipped is not any of the four. It is 12 signals — small on purpose, since the 8-signal
proposal had zero single-paper patterns and the 36-signal one had five — each tied to something the
daemon can actually decide rather than to phrasing observed in the sample. In-sample it reaches
precision 0.62 / recall 0.88 against the old 0.46 / 0.35.

**The honest expectation is the held-out number, not the in-sample one**, and even that is
optimistic: this set was designed after looking at which patterns discriminated on the labelled
data, so it is fit on data too. Expect roughly one in three queued papers to be genuinely
amplifiable. The real validation is the next nightly beat.

## Consequences

The paper that motivated all of this now scores **8** against threshold 4, on four independent
signals, and would be queued.

Coverage rose from 80 to 121 papers per 4-day window — a 51% increase in what the daemon sees,
which matters more than the scoring change: on a live 30-day sweep the new signals alone moved the
queue from 9 papers to 10, because the missing papers were the constraint, not the missing words.

**No trust surface.** The feed is proposal-side: it queues TARGETS, and ADR 0083's steering block
tells the conjecturer in its own text that the gates decide. Nothing here can promulgate anything.

**What this does not do:** it does not touch `QUEUE_THRESHOLD`'s interaction with ADR 0082's drift
detector, which alarms on unconsumed queue growth — a higher queue rate will reach that alarm
sooner, which is arguably correct but unmeasured. It does not paginate `update_queue`'s seen-set
bound (`_SEEN_CAP = 4000`), which a sustained higher sweep will reach sooner. And it does not
address what the labelling exercise made obvious: of 108 recent papers in the daemon's own
categories, only 17 had a finite core it could decide at all. The binding constraint on discovery
yield is the supply of amplifiable results, not the feed's ability to spot them.

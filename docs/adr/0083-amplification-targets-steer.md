# ADR 0083 — Queued amplification targets steer the conjecturer

- Status: accepted
- Date: 2026-07-28
- Depends on: ADR 0069 (the arXiv feed), ADR 0041 Phase 4 (`seed_intake` — the proposer seams)

## Context

The feed has queued amplification targets nightly since ADR 0069 and **nothing consumed them**.
ADR 0069 named this as future work; ADR 0082's drift detector now alarms on it directly
("N amplification targets queued and unconsumed").

That gap matters more than it sounds. Amplification — taking a fresh published result with a
finite core and re-deciding that core in the kernel — is the daemon's *proven* value: eleven of
its published laws came that way, including a record, an open-existence resolution and a
published-conjecture disproof. Origination, by contrast, has hit a textbook wall three separate
hunts running. The one path with demonstrated yield was still entirely manual.

## Decision

`arxiv_feed.queued_targets(home, cap=6)` turns the highest-scoring queued rows into **VALIDATED
TARGET seeds**, which `seed_intake.seed_steering` renders into the CONJECTURE prompt. The daemon
carries them on `Leibniz.seed_targets`; `assembly` loads them behind the **same** switch as the
feed that fills the queue (`LEIBNIZ_ARXIV_FEED=1`); an absent or malformed queue yields `()`.

### Why VALIDATED is defensible for an untrusted abstract

Because of what a TARGET seed *is*. ADR 0041 Phase 4 fixed the routing: a TARGET only ever feeds a
PROPOSER, never a decider, and the block it produces says so in its own text — *"UNTRUSTED hints
… the gates still decide"*. Validation here is about **provenance**, not truth: the record carries
a real arXiv id, a link, and the finite-core signals that queued it. Nothing downstream trusts the
paper's claim. Every conjecture the hint inspires runs the full cheap-refute → novelty →
faithfulness → kernel chain, exactly as if the daemon had thought of it unaided.

Pinned by test: a TARGET can never become a `SandboxTask` (only CONSTRUCTION seeds run code, and
these never are); the steering block always declares itself untrusted; the seed stays last in the
composed prompt; the cap holds a growing queue out of the prompt; malformed rows are dropped.

## Consequences

The daemon now proposes *toward* fresh literature instead of only toward its own static corpus and
its own near-misses — the "moving frontier" ADR 0069 described but only half-built.

No trust surface: `seed_intake` adds no decider and touches no gate; `steer` gained an optional
block; `Leibniz` gained a data field. With the feed off, behaviour is byte-identical.

**What this does not do:** it does not make the daemon *amplify* a paper — it cannot fetch a PDF,
extract a finite core, or formalize one. It biases what the conjecturer reaches for. Whether that
converts into amplification-shaped conjectures is measurable in the journal, and if it does not,
the next increment is core extraction, not more steering.

# ADR 0015 — Corpus (D4) & domain (D9) expansion (Accepted)

- Status: **Accepted** (implemented 2026-06-21)
- Date: 2026-06-21
- Related: ADR 0001 (novelty by retrieval + decision procedure, never a judge),
  R1c structural hash, R3 corpus. `scripts/build_corpus.py`,
  `corpus/known_results.json`, `corpus/frontier.json`, `leibniz/daemon.py`,
  `leibniz/leonardo.py`, `assembly.py`. Non-guarded. Roadmap: Tier 3.

## Context

Two discovery inputs were toy-sized:

- **Novelty corpus (D4)** held **3** entries. The novelty gate decides KNOWN by
  matching a candidate's elaborator-canonical structural hash against the corpus
  (ADR 0001: retrieval + decision procedure). With 3 entries, virtually everything
  "looks novel" — the daemon would happily re-discover `a + b = b + a`. A real
  corpus of the facts a conjecturer most often re-derives is what makes novelty
  mean something.
- **Domains (D9)** were a single fixed `domain = "analysis_of_algorithms"`. Even if
  the frontier listed more, the daemon only ever surveyed the one.

## Decision

1. **Expand the curated corpus (D4).** Grow `build_corpus.py`'s `CURATED` set from
   3 to **34** canonical results — Nat/Int additive & multiplicative structure,
   order facts over a domain, parity invariants, growth/complexity bounds, a
   construction — and regenerate `corpus/known_results.json`. Provenance policy:
   **every result is re-stated in our own Lean** (no copyrighted prose
   redistributed); each entry need only *elaborate* (the builder appends `:= sorry`
   to take the structural hash); all are true. Re-run on a Lean/Mathlib toolchain
   bump (the hash is toolchain-specific).
2. **Rotate domains (D9).** Add `frontier.json` domains adjacent to the existing one
   (`arithmetic_and_number_theory`, `discrete_structures_and_combinatorics`) so the
   current conjecturer copes. `Leibniz` gains an optional `domains` tuple;
   multi-cycle `run_cycles` round-robins the survey across them
   (`active[i % len(active)]`). Empty `domains` ⇒ the single `domain`, unchanged.
   `build_daemon` populates it from `LeonardoForgeAdapter.domains()` (the frontier
   keys), keeping frontier-reading in one place.

## Options considered

- Corpus from a Mathlib dump vs. curated re-statements: **curated** — keeps
  provenance clean (our own Lean), keeps the set to the high-recurrence facts that
  actually get re-proposed, and avoids redistributing copyrighted statements.
- Survey *all* domains every cycle vs. **round-robin one per cycle**: round-robin —
  bounds per-cycle cost and still gives the KFM archive cross-domain breadth over a
  run.

## Consequences

- Novelty is now a real gate: 34 canonical results are recognized as KNOWN by
  structure, so the daemon stops claiming textbook facts as discoveries.
- Discovery surface broadens across three domains without a prompt change (the
  conjecturer is seeded by the specific frontier seed string).
- No trust surface touched — novelty remains structural (retrieval + decision
  procedure), the corpus carries no proofs, and `tests/test_invariants.py` is
  byte-identical. All non-guarded.

## Open questions

- Structural hashing catches *exact* re-statements, not morally-equivalent variants
  (`nearest()` stays informational). Semantic near-duplicate detection is future
  work.
- Domains beyond the algorithmic/arithmetic neighbourhood will need a less
  specialized conjecturer system prompt (deferred to the Tier 1 discovery tuning).

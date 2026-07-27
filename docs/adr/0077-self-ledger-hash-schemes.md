# ADR 0077 — Self-ledger entries carry every hash scheme they may be matched under

- Status: accepted
- Date: 2026-07-25
- Depends on: ADR 0052 (novelty against the daemon's own ledger)

## Context

ADR 0052 seeds the novelty gate with the daemon's own promulgated laws so it stops rediscovering
them — the HANDOFF §6 gap it demonstrated by re-deriving `n^4 % 5`.

Matching is by `formal_hash`. But a ledger row's stored `normalized_hash` was produced by whichever
normalizer was live when that law was promulgated, and `pipeline._normalized_hash` *prefers* a
backend's elaborator-canonical hash, falling back to the textual one. The production `LeanReplBackend`
has **no** `normalize_statement` — so when the daemon moved from the CLI backend to the REPL, the
scheme silently changed from elaborator-canonical to textual.

Measured on the live ledger: of 25 promulgated laws, **7** carry a textual hash and **18** carry a
legacy elaborator hash that no candidate computed today can ever equal. ADR 0052 was therefore dead
for the daemon's *oldest* laws — the exact gap it exists to close, quietly re-opened by a backend
swap. (The design review that surfaced this read the split in the opposite direction; the
measurement above is the corrected one.)

## Decision

`self_ledger_entries` emits an entry for the stored hash **and** for a freshly recomputed textual
hash whenever the two differ, so a row is matchable under either scheme and stays matchable across
any future normalizer change.

Safe by this function's own soundness argument, which the docstring already states: the novelty
gate is **kill-only** — it can quarantine, never promote — so seeding it with more knowns can only
prevent a rediscovery, never cause an unsound promulgation. Distinct statements still hash
distinctly under each scheme, so nothing becomes falsely KNOWN.

## Consequences

Laws matchable by a hash computed today: **7/25 → 25/25**. The daemon can no longer re-derive any
law it has already promulgated.

Ledger corpus entries grow from one per law to at most two (25 → 43 today) — bounded, in memory
only, and never written back.

This is a *compensating* fix, not a root fix: the root is that the hash scheme depends on which
Lean backend happens to be wired. Making `_normalized_hash` scheme-stable (or giving the REPL
backend a `normalize_statement`) would remove the divergence at the source; this ADR makes the
ledger robust to it either way, including for the 18 rows already written.

# ADR 0078 — The REPL gets a normalizer, and candidates carry every hash scheme

- Status: accepted
- Date: 2026-07-25
- Depends on: ADR 0052 (self-ledger novelty), ADR 0077 (the compensating ledger-side fix)

## Context

ADR 0077 fixed the *symptom*: ledger rows written under one normalizer were invisible to novelty
under another. It named the root and left it — the hash scheme depends on **which Lean backend is
wired**, because `pipeline._normalized_hash` prefers `backend.normalize_statement` and falls back
to the textual hash, and the production `LeanReplBackend` had no such method.

Two consequences, both real: alpha-renamed statements of the same theorem stopped colliding (only
the elaborator scheme collapses `n_pow4_mod5` and `n_fourth_mod_five` onto `e88176ebbc00c995`), and
the identity key silently moved when the daemon switched backends.

## Decision

**1. `LeanReplBackend.normalize_statement`** — byte-compatible with the CLI implementation: same
rename to a fixed private name, same dropped proof body, the same `leibnizCanon` traversal, the
same `sha256[:16]`. Verified against the live ledger value `e88176ebbc00c995`; alpha-renamed
statements collide again, distinct ones stay distinct, non-elaborating input returns `None` so the
textual fallback survives.

**2. Candidates carry every hash they could be KNOWN under.** Adding (1) alone would have been a
*regression*, and was measured as one: production flips to elaborator hashes, and ADR 0077's
ledger keys (`stored` + recomputed-textual) do not cover that scheme — dedup coverage
**25/26 → 18/26**. So `ClaimSignature` gains `alt_hashes`, `_signature` fills it with the textual
hash (pure string work, no kernel), and `contains_equivalent` matches on any carried key.

Measured after both: **26/26**.

### Why the extra keys are safe

The novelty gate is **kill-only** — it can quarantine, never promote — so additional keys can only
prevent a rediscovery, never cause an unsound promulgation. Each key remains an *exact structural
identity*, never a fuzzy match, so a genuinely distinct claim is still novel (pinned by test).
Signatures without `alt_hashes` behave exactly as before.

## Consequences

Root cause removed: the identity key no longer depends on which backend happens to be wired, and
a future normalizer change degrades to a missed dedup rather than a silent one.

Cost: one extra textual hash per candidate — string work, no kernel call. The alternative
considered was recomputing an elaborator hash for every ledger row at `build_daemon` (~26 kernel
calls per beat); this design pays per-candidate and negligibly instead.

ADR 0077 stays: its ledger-side dual keys and this candidate-side pair are complementary, and its
keys are what make the *already-written* rows matchable at all.

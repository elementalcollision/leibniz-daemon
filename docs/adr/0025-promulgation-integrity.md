# ADR 0025 — Promulgation integrity (ring-class non-triviality + proof persistence)

Status: **Accepted** (2026-06-22)
Extends: ADR 0013 (provenance), ADR 0016 (persistent runtime). Prompted by the ADR
0023/0024 calibration.

## Context

The weaken-and-retry calibration (ADR 0023) **promulgated 32 laws** — the first
promulgations end-to-end. A rigorous audit confirmed the verification path is **sound**
(true identities verify via `ring` under `import Mathlib.Tactic`; false statements and
`sorry` are correctly rejected; `discharge` remains the sole `kernel_verified` writer).
But it surfaced two integrity problems:

1. **The 32 are mathematically trivial.** Every one is a polynomial identity closable
   by `ring` (e.g. `(m+3)(m+5)+1 = (m+4)²`). They passed the non-triviality gate **only
   because its decision-procedure set lacked a (non)linear-arithmetic tactic**
   (`decide/simp/omega/trivial/aesop` — no `ring`/`nlinarith`). By the gate's own
   charter ("a statement a decision procedure closes on its own is vacuous"), these are
   trivial and should never have promulgated.
2. **Promulgated proofs were not persisted.** `PersistentRuntime` stored
   `kernel_verified` + `qed` but not `proof_src`, so a recalled/published law showed its
   proof as `(none)` — it could not be re-audited or re-verified from the ledger (the
   Codex export's `--check` needs the proof).

Neither was a soundness breach — the kernel genuinely verified true statements — but
both undermine the *quality and auditability* of what the daemon promulgates.

## Decision

1. **Raise the non-triviality bar.** Add `ring` and `nlinarith` to
   `DEFAULT_TRIVIAL_TACTICS` in both Lean backends (CLI + REPL, kept in sync). A
   statement either closes is now quarantined `TRIVIAL`, pushing the daemon toward
   theorems that need genuine proof (induction, case analysis, lemmas — where ADR 0024
   decomposition earns its keep). Each tactic needs a Mathlib import; absent one it
   simply errors and is treated as "did not close", so listing it is always safe.

2. **Persist the proof.** `memory` gains a `proof_src` column (with an idempotent
   `ALTER TABLE` migration for pre-existing DBs); `remember` writes it and
   `recall_recent` restores it into the reconstructed `Demonstratio`. INSERT/SELECT use
   explicit column names so a migrated DB (where the column is appended last) round-trips
   correctly.

## Why this is trust-safe

- **Non-triviality is strictly *more* conservative** — it only adds reasons to
  quarantine, never to promulgate. `is_trivial` (`verifiers.py`) and the gate logic are
  unchanged; only the tactic list in the backends grows.
- **Persistence writes no verdict.** `proof_src` is descriptive text. `kernel_verified`
  is still reconstructed via the `Demonstratio` constructor (replaying a stored verdict,
  as before — the single-writer guard binds `discharge`); adding a `proof_src` argument
  to that call changes nothing about who may *mint* a verdict.
- `tests/test_invariants.py` byte-identical; `trust.py`, `verifiers.py`, the gates'
  dispatch, and `test_boundary_guards.py` untouched.

## Consequences

- Promulgation will become **rarer and higher-quality** — ring/nlinarith-trivial
  identities are filtered. A re-run measures whether genuinely non-trivial theorems
  emerge; expect far fewer promulgations (possibly zero for a while — the honest state).
- Future promulgated laws carry their kernel-checked proof, enabling ledger re-audit and
  the Codex `--check` re-verification. (The 32 prior trivia keep no proof — they are
  trivial and will not be published.)
- Cost: the triviality check runs up to 2 extra tactics per candidate, but short-circuits
  on the first that closes and runs at the cheap-gate stage, saving the far more
  expensive consensus proving on trivia.

## Follow-ups (not in this ADR)

- The Lean images ship without the root `Mathlib.olean` aggregate (only components like
  `Mathlib.Tactic` are built). Fine for `Mathlib.Tactic`-scoped proofs, but `import
  Mathlib` fails — worth a Docker-image rebuild (`lake exe cache get` + `lake build`).

## Validation

- Unit (CI-safe): `ring`/`nlinarith` present in both backends and in sync; `proof_src`
  round-trips through `save`/recall; a pre-0025 DB migrates and stays readable, and new
  writes carry the proof.
- Gated (real kernel): `closed_by_decision_procedure` flags the exact escaped identity
  `(m+3)(m+5)+1=(m+4)²` as trivial.

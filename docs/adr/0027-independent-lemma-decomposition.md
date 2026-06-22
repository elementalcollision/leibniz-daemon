# ADR 0027 — Independent sub-lemma decomposition (deeper M3)

Status: **Accepted** (2026-06-22)
Extends: ADR 0006 (N+1 consensus), ADR 0024 (in-proof decomposition).

## Context

After ADR 0026 the daemon conjectures in the genuinely non-trivial band, but the
validation run left 23/24 such conjectures **unproven** — the ensemble (incl. ADR 0024's
in-proof `have` decomposition) could not close them one-shot. The remaining lever is to
**split a hard theorem into sub-lemmas, prove each independently, then compose**. A prover
that cannot find the whole proof can often find the pieces.

ADR 0024 asks one prover for a single `have`-structured proof. ADR 0027 goes deeper:
prove the sub-lemmas as *separate* goals (each through the full N+1 consensus), then
re-prove the main with those proven lemmas available.

## Decision (hints design)

- **`decompose()`** (provider) — proposes sub-lemma statements + a main-proof sketch.
- **`LemmaDecomposer`** — proves each proposed sub-lemma INDEPENDENTLY via the existing
  `ProofConsensus` (kernel-verified, N+1); then re-proves the main under N+1 with the
  proven lemmas offered to the prover as `have`-block **hints** (`Expressio.proof_hints`,
  surfaced by `consensus._prover_context`). The prover may paste any hints it needs into
  its own `by` block.
- **`DecomposingDemonstrate`** — the DEMONSTRATE stage: normal consensus first, then the
  decomposer as a fallback when it fails. Records **exactly one** proof edge (the better
  outcome). Wired by `LEIBNIZ_LEMMA_DECOMPOSE` (default 1).

## Why this is sound — by construction

The promotion rests on the kernel checking **one self-contained declaration** per
attempt, through the **unchanged** `discharge` → `check_proof`:

1. **`proof_hints` is prover context only — it never enters the Lean source.** The kernel
   file is exactly `imports + theorem_src := <prover proof>`, as for any direct proof.
   The proven sub-lemmas reach the prover as *suggestions*; whatever the prover writes is
   what the kernel verifies.
2. **A single declaration has no poisoning surface.** This is the crucial difference from
   the rejected "preamble" design (see below). With no separate top-level declaration
   before the main, there is nothing a smuggled `axiom` / `attribute` / `notation` /
   `run_cmd` / `instance` could install ahead of the goal. Inside a `by` block such tokens
   are a **parse error**; a trailing top-level command after a completed proof runs *after*
   the goal is already closed and cannot retroactively close a false goal (and a *leading*
   command before `:=` is a parse error). So a malicious hint or proof body can only make a
   proof **fail**, never make a false one succeed.
3. **`discharge` is unchanged** — still the sole `kernel_verified` writer; `sorry`/`sorryAx`
   are still rejected by `_kernel_ok`. **N+1 is preserved** — the composed main is drafted
   by ≥`min_consensus` distinct provers and kernel-checked; each sub-lemma was itself
   N+1-proven.
4. No edit to `trust.py`, `verifiers.py`'s `discharge`, the backends' file assembly, the
   gates, or `tests/test_invariants.py` (byte-identical).

## Rejected alternative — the "preamble" design (and why)

The first cut prepended the proven lemmas as **separate `lemma` declarations** before the
main in the kernel file, guarded by a keyword denylist. An adversarial review found this
**critically unsound**: a preamble declaration executes *before* the main, so it can
poison elaboration via `attribute [simp/instance]`, `notation`/`macro`, `run_cmd
Lean.addDecl`, etc. — **none of which contain a denylisted keyword** (the kernel does not
error on them). A denylist cannot cover Lean's open metaprogramming surface. The hints
design **eliminates the vulnerability class** rather than guarding it: there is no
separate declaration to poison.

## Consequences

- The daemon can attack hard goals by splitting them; a first *non-trivial, decomposed*
  promulgation becomes reachable. Cost: when normal consensus fails, decomposition adds
  one `decompose` call + (≤`max_lemmas`) sub-lemma consensus proofs + one composed proof —
  bounded by the USD cap, fired only on failures.
- Efficacy is empirical, measured by a re-run.

## Validation

- Unit (CI-safe): `_prover_context` offers the hints but keeps them out of the goal;
  `_safe_lemma` hygiene; the decomposer proves sub-lemmas then composes with `proof_hints`,
  drops unsafe lemmas, and handles a missing hook / bad JSON; `DecomposingDemonstrate`
  falls back on failure with exactly one PASS edge and skips decomposition when consensus
  already passed.
- Gated (real kernel): `proof_hints` carrying `axiom cheat : False` does NOT put `cheat`
  in scope (the proof fails) — hints never reach the kernel; and a genuine single-
  declaration proof that splices a `have` verifies.
- Live (billable, next): a re-run measuring whether decomposition closes any of the
  non-trivial conjectures the ensemble could not.

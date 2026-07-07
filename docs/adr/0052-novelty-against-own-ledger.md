# ADR 0052 — Novelty against the daemon's own ledger

**Status:** Accepted (2026-07-06). Complements ADR 0001 (charter — novelty is retrieval + a decision
procedure, never a judge), ADR 0031/0032 (corpus structural matching), and HANDOFF §6, which names
this exact gap. Touches the novelty gate (a promotion *gate*), so the soundness argument is spelled
out below.

## Context

The novelty gate settles novelty by **structure**: `CorpusBackend.contains_equivalent(sig)` is True
iff the candidate's elaborator-canonical `formal_hash` matches an entry in `corpus/known_results.json`
(Mathlib + a curated known set). That corpus is **external** — it contains what *other people* have
proven, not what *the daemon* has proven.

Consequence, observed live: on a second cycle the daemon re-conjectured `∀ n, n⁴ % 5 ∈ {0,1}` (as
`n_pow4_mod5`) — a law it had **already promulgated and published** an hour earlier
(`n_fourth_mod_five`). Both have the identical canonical hash `e88176ebbc00c995`, but the published
law was not in the external corpus, so novelty passed and the daemon **rediscovered itself**. With a
fixed proposer, this recurs every cycle and caps origination yield: the frontier keeps re-deriving
its own back-catalogue instead of exploring.

## Decision

Seed the novelty corpus with the daemon's **own promulgated laws**. At assembly time,
`build_daemon` loads every promulgated, kernel-verified law from the runtime DB (read-only) as a
`CorpusEntry` whose `formal_hash` is the law's stored `normalized_hash`, and passes them as `extra`
to `CorpusBackend.from_json`. A re-conjecture whose canonical statement matches a prior promulgation
then hits `contains_equivalent` and is quarantined **KNOWN**, exactly as an external textbook match
would be.

- Only **promulgated** (kernel-verified) laws seed the ledger — an *unproven* prior attempt must stay
  re-attemptable (it may become provable later), so quarantined/unproven rows are excluded.
- Both **published and held-back** promulgations count: a held-back law is still originated; the
  daemon should not re-derive it either.
- Load is **read-only** (`mode=ro`) and **fail-safe**: an absent/unreadable DB yields no entries and
  the gate degrades to external-corpus-only — never an error, never a locked DB.

## Why this is sound

The novelty gate is **kill-only**: `NoveltyGate.check` can *quarantine* a candidate (KNOWN / TRIVIAL)
but can **never promote** one — promotion happens later, only through `discharge` (kernel) and
`VerificationGate.is_promotable` / `TrustPolicy.validate_path`. Therefore seeding the gate with more
knowns can only **prevent** a promulgation, never **cause** an unsound one. Adding to the known set is
in the safe direction by construction.

The only failure mode is **false-KNOWN** — quarantining a genuinely *distinct* law because it wrongly
matches a ledger entry. This is a *yield* concern, not a trust breach, and it is excluded by the
matching primitive: `contains_equivalent` compares the **elaborator-canonical `formal_hash`**, so two
statements collide **iff** they are the same theorem up to α-renaming and notation. A different
theorem has a different hash (the same property ADR 0032 relies on: "a different congruence has a
different signature"). Distinct laws are never false-KNOWN.

`TrustPolicy.validate_path`, `VerificationGate.is_promotable`, and the "`kernel_verified` set only in
`discharge`" invariant are untouched; `tests/test_invariants.py` stays byte-identical. This ADR only
makes an existing kill-only gate see the daemon's own output in addition to the world's.

## Scope / limits

- **Snapshot at assembly.** The self-ledger is read once when `build_daemon` runs, so an
  intra-cycle rediscovery (promulgate law A, then re-conjecture A later in the *same* cycle) is not
  caught until the next assembly. The demonstrated, dominant gap — cross-run rediscovery — is closed;
  intra-cycle dedup is a possible follow-up (check the in-cycle promulgated set).
- **Read path only.** No change to how laws are written or promulgated; this only enriches what the
  novelty gate reads.

## Consequences

- The daemon stops re-deriving its own back-catalogue → higher genuine-novelty yield per cycle.
- `contains_equivalent`-KNOWN now fires for `ledger:*` entries as well as curated ones; the
  disposition is the same (`FinishReason.KNOWN`), so downstream accounting is unchanged.
- Closes the HANDOFF §6 "novelty against the ledger" item.

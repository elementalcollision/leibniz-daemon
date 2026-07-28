# ADR 0081 — The family key drops the modulus

- Status: accepted
- Date: 2026-07-28
- Revises: ADR 0034 (genre-kill), ADR 0069 (dry-ground), ADR 0073 (the widened key)

## Context

ADR 0034 made the modulus part of the family key, reasoning that a mod-2 fact and a mod-3 fact are
genuinely different mathematics. That is true, and it is also why genre-kill has never fired.

Measured over the 18 promulgated laws carrying a DSL contract: **14 are polynomial congruences**,
spread across **11 distinct families**, the largest holding exactly 3. The daemon looked productive
and diverse to the steering machinery while producing, in substance, one construction at eleven
different moduli.

The `_family` docstring already anticipated this tension — *"deliberately coarse… a too-fine key
would never fire across shapes"* — and then made the key fine along the modulus axis anyway.

## Decision

Drop the modulus from every layer of the key:

| shape | before | after |
| --- | --- | --- |
| congruence | `==\|3` | `==` |
| boolean combination | `and\|5` | `and` |
| named function | `factorial%5\|!=` | `factorial%\|!=` |

The **relop still distinguishes** families — `==`, `!=`, `in`, `and` remain separate genres,
because a residue-set characterisation really is a different kind of claim from an equality. Only
the parameter is dropped.

Persisted counts are **migrated**, not discarded: `_coarsen_key` folds legacy keys onto their
coarse form when a notebook is restored, so the evidence already accumulated keeps counting
instead of restarting. On the live notebook this collapses 6 families into 4 with counts summed
(`==|8` + `==|2` → `==`: 2).

## Consequences

**This is a much sharper instrument, and it will fire soon.** On the live histogram `!=` and `==`
are each within one or two proofs of `genre_threshold`, so the conjecturer should start seeing
`EXHAUSTED FAMILIES` entries within days rather than never. That is the point — but it means whole
swathes of congruence work get retired at once, and `genre_capacity` (6) is now a much larger
fraction of the reachable genre space.

**Dry-ground gets *less* likely to fire**, in exchange. A coarse family is more likely to contain
at least one proof, and a family that has ever proven can never be declared dry. Broad genres will
therefore be retired by success (genre-kill) rather than by failure (dry-kill), which is the right
way round for a family this coarse.

**The ADR 0034 reasoning is not wrong, it is differently weighted.** Mod-2 and mod-3 facts remain
different mathematics; this key is not a claim about mathematical identity, it is a steering
signal about *where the daemon has already been digging*. Proposal-side only: it changes the
conjecturer's prompt and decides nothing.

If the daemon subsequently starves — genres retired faster than it can find new ones — the lever
is `genre_threshold`, not a return to the fine key.

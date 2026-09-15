# Held-law sweep — 2026-09-15

**65/65 held laws re-discharge clean** under the guards in force at ADR 0101:
the ADR 0097 axiom check, the ADR 0098 kernel replay, and the ADR 0100 denotation checks.
Total wall-clock 8.8 min. Produced by `scripts/audit_held_laws.py`.

## Why it was run

ADR 0101 recorded that the 2026-09-15 beat ran pinned to `9484d5e` — four trust-boundary
ADRs behind `origin/main` — and promulgated a law. Nothing was published (publication is the
operator's ADR 0033 act), but the verdict came from a build with a demonstrated hole. Every
older law in the queue was minted by a build further still from the current guards, so each
stored `kernel_verified` was an unverifiable claim rather than evidence.

## Result

| | |
|---|---|
| laws swept | 65 |
| pass | **65** |
| fail | 0 |
| with `sorryAx` | 0 |
| axioms outside the allowlist | 0 |
| shadowing constants | 0 |
| vacuous statements | 0 |

Minted across: 2026-06 (10), 2026-07 (19), 2026-08 (24), 2026-09 (12).

## The sweep is not vacuous

A green result from a check that cannot go red is worthless, so both directions were measured.

**It discriminates.** Three distinct axiom footprints across the corpus, not one constant answer:

- 43 laws: `Classical.choice, Quot.sound, propext`
- 19 laws: `Quot.sound, propext`
- 3 laws: `propext`

**It goes red on the same code path.** Controls run through the identical
`independent_axiom_footprint` call the sweep uses:

| control | verdict |
|---|---|
| a real held law, untouched | **ok** |
| `by sorry` | refused |
| `by native_decide` | refused |
| `notation "False" => True` | refused — *statement elaborates to `True`* |
| `def False` in an open namespace | refused — *names shadowing constant `Foo.False`* |

## What this does NOT establish

- The runtime DB stores neither `imports` nor `preamble`, so every law was re-discharged
  against `Mathlib` (a superset) with an empty preamble. Passes are meaningful, but this did
  not reproduce each law's exact import set, and ADR 0100's preamble surface was not exercised
  — correctly, since nothing on the proposer path writes a preamble (measured, ADR 0099).
- It checks that each law's PROOF is mechanically sound. Whether the formal statement says
  what the natural-language claim says is the ADR 0002 faithfulness gate, and is the same
  residue ADR 0100 left open.
- Nothing was written back. All rows keep their original verdicts; re-verification is
  evidence, not a promotion.

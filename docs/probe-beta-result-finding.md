<!--
Probe β complete (all 3 pieces) + the record-beating result. Provenance:
docs/results/probe_beta_search_result.json, brouwer_cwc_lower_bounds.json. No trust-boundary change.
-->

# Probe β result — the record factory is built and sound; naive autonomous search beats nothing

**Status:** measured, 2026-06-26. **All three Probe β pieces are built and validated; the record-beating
search is RED (0 beats), with a minor genuine bonus (10 exactness proofs).** This is the witnesses'
best-remaining autonomous lever — *search over a finite object space with objective novelty (beat a public
table-of-record)* — taken end to end on binary constant-weight codes.

## What was built (all sound, all tested)
1. **Lean witness-checker (piece 1)** — a core-Lean, `decide`-closed `A(n,d,w) ≥ M` theorem; **kernel-
   ACCEPTED** for the Fano `A(7,4,3) ≥ 7` and **kernel-REJECTED** for a false witness. Genuinely Q.E.D.
   (the witness *is* the proof) — the first Q.E.D.-bearing result of the whole discovery arc.
2. **Automated table-of-record oracle (piece 2)** — Brouwer's A(n,d,w) lower bounds (839 cells), the α
   safeguard enforced (ground-truth + monotonicity validation; refuses a wrong snapshot; out-of-table →
   None). Novelty = `found > best_known`, by automated lookup, never LLM-judged.
3. **Record-beating search (piece 3)** — exact branch-and-bound max-clique on the compatibility graph
   (the max clique *is* A(n,d,w)) + the witness-non-triviality carve-out (`record_is_nontrivial = is_
   improvement`, wiring deferred until a beat exists).

## The record-beating run — RED, and why
Exact max-clique on the **10 smallest non-tight (non-exact) Brouwer cells**: **0 records beaten; 10/10
proved exact** (max-clique = best_known, optimality proved). Two things follow:

- **A minor genuine result:** all 10 are now **proved optimal** — an independent cross-check that
  Brouwer's lower bounds are tight (10/10), and for these "non-exact" cells it actually *supplies the
  missing upper-bound proof*. Small, but real and sound.
- **The structural wall, a fifth time:** the smallest non-tight cells are **already tight**; the
  genuinely-open (beatable) cells have `C(n,w)` too large for pure-stdlib exhaustive search. **Tractable =
  already solved; open = intractable for naive search.** This is the *same* wall as the prior four probes
  (genre A/B, Walnut run-3, SOS, zero-LLM enumeration), now in the record-factory domain.

## What it means
- **The pipeline works and is sound** — propose (untrusted search) → decide (verify + Lean kernel) →
  objective novelty (automated oracle) → non-triviality carve-out. It even produced a (minor) genuine
  result. The trust boundary held throughout; no LLM decided anything; `tests/test_invariants.py`
  byte-identical.
- **Naive autonomous record-beating does not reach novelty.** A real attempt needs a strong solver
  (CP-SAT/ILP — `ortools` unavailable here) **plus serious compute on the large open cells**, and the
  witnesses rated even that a modest-odds bet. The binding constraint is unchanged: the easy region is
  solved, the novel region is hard — independent of the trust machinery, which works.
- **The strategic home stands: verification amplification.** Pieces 1 + 2 (the Lean witness-checker and
  the automated oracle) are *exactly* what a human-proposes / daemon-soundly-checks system needs — so this
  build is not wasted even though piece 3 is RED.

## Strong-solver push (piece 3b, CP-SAT) — still RED, and now confirmed not a weak-solver artifact
The pure-Python max-clique was confined to tiny cells. The honest follow-up: **CP-SAT** (ortools, 8
workers, operator-local) on the *larger* non-tight cells pure-Python couldn't reach (C(n,w) 1001–1716),
25 s/cell. Result (`docs/results/probe_beta_cpsat_result.json`): **0 records beaten** — CP-SAT **matched**
best_known on all 6 cells and **proved 2 more exact** (A(14,6,4), A(13,10,6); cumulative **12 cells proved
exact**). So a strong multi-worker solver *reaches but does not exceed* Brouwer's bounds — the RED is **not
a weak-solver artifact**. Beating these records needs research-grade compute/constructions, not an
autonomous laptop run (the witnesses' "modest odds", resolving toward RED).

## Disposition
- Probe β: **complete and RED on record-beating**, now confirmed with a strong solver. The autonomous
  record-factory is built, sound, and measured; it reaches and *proves* records but does not beat them.
- The two reusable assets (witness-checker, table oracle) carry forward to verification amplification.
- Kernel bridge (task #54) unchanged.

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

**Extended sweep (20 non-tight cells, C(n,w) ≤ 4000, 90 s/cell, ~26 min):** still **0 records beaten**;
CP-SAT matched 19/20 and proved 5 optimal. The decisive datapoint: on **A(14,6,6) it found only 30 vs
Brouwer's known 42** in 90 s — *a strong solver could not even MATCH a known construction.* That is
evidence the binding constraint is **algorithmic/constructive, not raw laptop compute**: the records come
from clever constructions, so throwing a generic accelerator (GPU/Codon) at the *same brute search* would
not help — the lever would be smarter constructions / ML-guided search. (Provenance:
`docs/results/probe_beta_cpsat_sweep_result.json`.) This pre-answers Q1 of the acceleration witness brief.

## Construction-search pivot (piece 3c) — the witnesses' #1 lever, prototyped, also RED
The 7-model acceleration round was unanimous: the constraint is *algorithm/domain*, and we were using an
*optimality prover* to find *lower-bound witnesses* — the right objective is direct **construction
search** (find a big code; no optimality proof). I prototyped it on CPU (stochastic greedy + penalty/swap
local search; `scripts/probe_beta_construct.py`). It is *correct* — it reaches the known optima on small
cells (A(6,4,3)=4, A(7,4,3)=7, A(9,6,4)=3) — but on the larger open cells it is **RED, and notably
*weaker* than CP-SAT**: on **A(14,6,6) it found only 25 vs CP-SAT's 30 vs Brouwer's 42.** So *unstructured*
search — exact **or** heuristic — plateaus far below records. This **kills the "naive massively-parallel
construction" sleeper** (parallelizing a method that loses to CP-SAT won't reach records) and sharpens the
remaining autonomous lever to the **structured** forms the witnesses named — automorphism-prescribed
search (assume a symmetry group, collapse variables) and learned construction à la FunSearch — which are
substantial builds (FunSearch needs an LLM+GPU loop). Provenance:
`docs/results/probe_beta_construct_result.json`; synthesis: `docs/external-witness-round-acceleration-synthesis.md`.

## Disposition
- Probe β: **complete and RED on record-beating**, confirmed across a strong solver (CP-SAT) *and* a
  construction search. The autonomous record-factory is built, sound, and measured; it reaches and
  *proves* records but does not beat them. Records require **structure** (automorphism/algebraic/learned),
  not raw compute or unstructured search — the unanimous witness conclusion, now empirically corroborated.
- The two reusable assets (witness-checker, table oracle) carry forward to verification amplification.
- Kernel bridge (task #54) unchanged.

## Automorphism-prescribed search (piece 3d) — STRUCTURE reaches what unstructured search cannot
The witnesses' structural lever, built (`scripts/probe_beta_automorphism.py`): a G-invariant code is a
union of G-orbits, collapsing C(n,w) codewords to ~C(n,w)/|G| orbits → a small max-weight clique on the
orbit graph → union of selected orbits = a valid (Lean-checkable) code. **Headline: on A(14,6,6),
cyclic-orbit search reached the record 42 in 0.0 s** — where exact CP-SAT got 30 and heuristic
construction got 25. *Structure is decisively the lever.* Still **0 records beaten** (cyclic/affine matches
records whose construction shares that symmetry, falls below where the record uses a different structure),
but the orbit search is **~instant**, so the autonomous engine is a **broad sweep** (cyclic + affine +
cyclic subgroups × many open cells, best-over-groups) hunting a cell where the best prescribed-group code
exceeds Brouwer. Provenance: `docs/results/probe_beta_automorphism_result.json`. This is the arc's most
promising autonomous result: cheap, sound, and it reaches where exact/heuristic search plateaus.

### Broad automorphism sweep — 0 beats, but structure MATCHES 53% of records (the autonomous ceiling)
Sweeping all 78 tractable non-tight cells × candidate groups (cyclic + affine + cyclic subgroups
`sub:k`, best-over-groups, ~257 s): **0 records beaten; 41/78 (53%) MATCHED** the published record —
where unstructured search (CP-SAT/heuristic) plateaued far below. The subgroup sweep earned its keep (24
of the matches came from `sub:k`, not full cyclic). Near-misses: **1 short-by-1, 8 short-by-2**; 24 cells
short by >3 use structure beyond cyclic/affine/cyclic-subgroups (quasi-cyclic / algebraic / non-group).
**Capstone: the autonomous track REACHES records with the right (structural) method but does not BEAT
them** — beating needs research-grade construction structure (richer prescribed groups, or FunSearch-style
learned construction). Provenance: `docs/results/probe_beta_automorphism_sweep_result.json`.

### Richer-group sweep on the near-misses — 0 beats, one codeword short (definitive capstone)
Added richer prescribed groups (affine multiplier-subgroups incl. dihedral; fixed-point cyclic
`fixcyc`) and swept the 13 near-miss cells. **0 beats** — but the richer groups *closed 6 more
near-misses to MATCH* (`fixcyc` expresses the small "shortened" codes the orbit method missed) and pushed
**A(21,6,4) from short-3 to short-1 (30 vs 31)** — one codeword from a record, but not a record.
**Definitive capstone:** the autonomous record-beating track — pushed through exact (CP-SAT), heuristic
construction, structural (cyclic/affine/subgroups), and richer-structural (multiplier-subgroups /
dihedral / fixed-point) over 78+13 cells — **matches many records but beats none.** Beating Brouwer needs
FunSearch-style learned construction (GPU/LLM, modest odds) or research-grade construction insight, beyond
an autonomous laptop daemon. Provenance: `docs/results/probe_beta_richgroup_result.json`.

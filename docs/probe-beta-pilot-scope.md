<!--
Probe β pilot result (mechanism validation) + the full-build scope and pre-registered GREEN/RED.
The witnesses' best-remaining autonomous lever: finite-witness SEARCH with OBJECTIVE novelty
(beats a public table-of-record). Provenance: scripts/probe_beta_cwc_pilot.py (+ tests).
-->

# Probe β — finite-witness record factory: pilot result + full-build scope

**Status:** pilot run, 2026-06-26. **Mechanism VALIDATED; full build scoped & pre-registered (not yet
built).** Probe β is the one autonomous lever the four enumerate-and-decide probes never tested: replace
LLM theorem-*ideation* with **search over a finite object space whose novelty is OBJECTIVE** — a witness
that *beats a public table-of-record*. Untrusted search proposes; a checker decides; novelty = improves the
best-known entry. This restores the propose/decide split and gives the objective novelty criterion the
"non-named" enumerate probes lacked (Probe α's name-detector false-negatived 8/8 — the α lesson).

## Pilot (mechanism validation) — GREEN
Domain: binary constant-weight codes `A(n,d,w)` (witness = list of w-subsets; distance `2(w−|A∩B|)`).
`scripts/probe_beta_cwc_pilot.py` ran untrusted greedy+restart search on **8 cells whose optimum is
provably/derivably known** (matchings, packings, and the Fano/STS(7) Johnson-bound optimum), each result
checked by the reference verifier:

- **8/8 reached the known optimum**, including **A(7,4,3)=7 (the Fano plane)** — a genuine combinatorial
  design, not a trivial packing.
- The **verifier is sound on every code found** (it is the trust-critical re-check; pinned by
  `tests/test_probe_beta_cwc.py`: accepts Fano, rejects too-close pairs / wrong weight / duplicates /
  out-of-range symbols; the search is untrusted and only ever checked).

So the **end-to-end pipeline works** (search → verify → compare-to-oracle) and cheap search reaches known
optima for small cells. **What the pilot does NOT show:** it does not *beat* a record (the cells sit at the
optimum), the cells are small (cheap greedy will fall short at the larger cells where records are
beatable — that needs CP-SAT/ILP), and the oracle here is a hand-curated *provably-correct* slice, not the
automated table-of-record the full build requires.

## Full-build scope (the three pieces, in trust order)
1. **Lean witness-checker (the trusted re-check).** The Python verifier mirrored as a Lean theorem
   `A(n,d,w) ≥ M` whose proof is the explicit witness, kernel-checked by computation (`decide`/`native_
   decide` on the finite properties). This is the soundness root — ships behind an adversarial review like
   every TCB addition. **A β record is real only when the Lean kernel re-checks the witness** (and, unlike
   Walnut, this path is genuinely Q.E.D. — the witness *is* the proof of the existential).
2. **Automated table-of-record oracle (the α lesson, non-negotiable).** A parser of a real best-known
   table (Brouwer's constant-weight-code tables / Colbourn covering-array tables) → best-known lower bound
   per cell. Novelty = "beats this entry," judged by the automated lookup, **never** LLM-judged (Probe α
   showed a hand/LLM detector false-negatives). A wrong oracle poisons every claim.
3. **Untrusted heavy search.** CP-SAT / ILP / SAT (cvxpy is for SOS; here it's e.g. OR-Tools CP-SAT or a
   MaxSAT encoding) + symmetry breaking + local-search repair, on a pre-registered set of **non-tight**
   cells. LLM may propose encodings / symmetry breaks / restart schedules (proposal-only).

## Pre-registered full GREEN / RED
- **GREEN:** ≥1 cell where the pipeline produces a **Lean-kernel-checked witness that strictly beats the
  automated table-of-record's best-known lower bound**, confirmed by a domain expert as not already known.
  → a genuinely-novel, Q.E.D., autonomous result exists; the search track is alive.
- **RED:** after a pre-registered budget over the non-tight cells, **0** strict improvements (only
  matches/rediscoveries/known values) → record-beating needs more than this pipeline; conclude the
  autonomous search track and pivot wholly to verification amplification.
- **Caveat (honest):** even GREEN yields *computational-record* novelty (a better witness), not
  conceptual novelty — the human panel decides whether that counts (invariant 4). And matching ≠ beating:
  the pilot's 8/8 is reach, not improvement.

## Disposition
The pilot clears the mechanism gate, so the full build is *justified* but it is a real, heavier slice
(Lean checker + automated oracle + CP-SAT, partly billable/operator-run). **Verification amplification
remains the strategic home regardless** (witnesses' unanimous #1); Probe β is the budgeted *side*-track
that decides whether a narrow autonomous record-factory lives alongside it. Trust boundary untouched;
`tests/test_invariants.py` byte-identical.

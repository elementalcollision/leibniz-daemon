<!--
Results of the Tier 1 free-CPU exact ladder (validation plan, GATE-1). Audit/measurement only; no trust
touch; tests/test_invariants.py byte-identical. The numbers below match the committed per-cell artifact
docs/results/tier1_exact_ladder.json, which is a REGENERATION of the ladder (after the original JSON was
accidentally overwritten). The original authoritative run and the regeneration AGREE on the binding result
(0 beats, 0 bugs, 10 above-record) and differ only in the optimality split by one cell (original 21 proven
/ 40 reproduced; regen 22 proven / 39 reproduced) — expected CP-SAT parallel-search timing variance near
the per-cell budget boundary. The committed artifact is the regeneration.
-->

# Tier 1 results — exact ladder over the frozen OPEN band (GATE-1, 2026-06-30)

## Verdict: **GATE-1 = NO-REACHABLE-BEAT**
Neither a generic greedy producer nor exact CP-SAT set-cover beat **any** record across the **71 tractable
OPEN cells**. **0 beats** (confirmed at the raw-number level: no `found < best_known` on any cell, by either
producer). No reachable-and-beatable covering frontier exists on this band — so no record beat materialized,
and the deferred construction proof-edge (`LeanVerifier.discharge`, ADR 0045 §10) **stays dormant**: there
is nothing to make it non-dormant.

## What was run
- **Frozen OPEN-cell list (the one canonical list, threaded through both producers):** every cell with
  `best_known` strictly above the strongest cheap lower bound (R0.8's OPEN set) within a tractable band —
  `C(v,k) ≤ 2000`, `C(v,t) ≤ 5000`, `best_known ≤ 50` — **71 cells, spanning t=2..8, gaps 1..14.** This
  broadens the prior exact-producer finding (6 cells, t=2 only) by an order of magnitude and across t.
- **Ladder (cheapest first):** greedy reproduction probe (200 restarts, 5s/cell) → exact CP-SAT set-cover
  (120s/cell, 8 workers) on the cells greedy did not beat.
- Free-CPU, ~48 min/run, no docker, no LLM, no trust touch.

## Results (71 cells)
| verdict | count | meaning |
|---|---:|---|
| **BEAT** | **0** | no producer found fewer blocks than any record |
| **OPTIMAL (proven)** | 22 | exact CP-SAT proved record == optimum (record is tight; no beat is possible) |
| reproduced-not-proven | 39 | matched the record but did not prove optimality within 120s |
| above-record | 10 | solver could not even reach the record within 120s (hardest cells) |
| still-open | 0 | every cell at least matched its record |
| bugs (false-beat) | 0 | — |

- **Proven-optimal by t:** {t2:7, t3:7, t4:7, t5:1} — optimality proofs concentrate at low t.
- **Not-proven by t:** {t2:2, t3:10, t4:11, t5:15, t6:7, t7:3, t8:1} — the budget-limited remainder skews to
  higher t (more constraints → harder to *prove* optimal at a fixed budget).
- **above-record cells** (record, best the solver reached in 120s): C(14,11,7) 22→23, C(12,8,5) 26→27,
  C(13,9,5) 19→21, C(13,9,6) 39→41, C(12,5,3) 29→30, C(12,7,4) 24→25, C(12,6,4) 41→44, C(14,10,6) 29→35,
  C(13,8,4) 18→19, C(13,8,5) 42→46. These are search-weakness (our solver), **not** evidence the record is
  beatable.

## Reading
- **The binding result is `beats = 0`.** A beat would surface quickly even at a short budget (CP-SAT finds
  better-than-record solutions fast when they exist; the per-cell budget only limits *optimality proofs*,
  not beat *detection*). So raising the budget could move cells from "reproduced-not-proven" into "proven
  optimal" — but it **cannot manufacture a beat exact search already failed to find**.
- **22/71 records are now machine-proven optimal**; 39 more were matched-but-not-proven; 10 the free solver
  could not even reach. None is a beat.
- This is **GATE-1 RED** in the actionable sense: no reachable-and-beatable frontier on the tractable band,
  free producers plateau at-or-above the record everywhere. The proof-edge stays frozen (per ADR 0045 §10);
  Track D's producer swing remains unjustified here — now evidenced across 71 cells and 7 values of t, not 6
  cells at t=2.

## Implication for the next decision
The plan's billable Tier-3 swing precondition (`free_beats==0 ∧ gaps survive ∧ exact unsettled ∧ producers
plateau`) is *technically* met on the 49 not-proven cells — but the **expected value is low**: exact CP-SAT
plateaued *at* the record on 39 of them (strong evidence those records are good), and on the other 10 our
free search was simply too weak to reach the record (no evidence of beatable slack). A billable producer on
this band would most likely reproduce, not beat.

The honest fork for the operator:
1. **Stop the D-line here.** Declare the reachable+tractable covering band non-beatable for free; keep the
   amplification spine as the product; leave the proof-edge deferred. (Recommended — the evidence is now
   broad and consistent.)
2. **Escalate optimality proofs** (free): raise the exact budget / add symmetry-breaking on the 40
   reproduced-not-proven cells to convert more to proven-optimal. Tightens the "dead" claim; cannot produce
   a beat.
3. **Larger-headroom probe** (heavier/billable): attack OPEN cells *beyond* the tractable band (bigger
   C(v,k), bigger gaps) where exact is intractable and a stronger producer might find slack. This is the
   only path that could still yield a beat — operator-gated, billable, low-but-nonzero EV.

Artifact: `docs/results/tier1_exact_ladder.json` (frozen cell list + per-cell rows). Harness:
`scripts/tier1_exact_ladder.py` (deterministic; `--resume` and `--summarize-only` supported).

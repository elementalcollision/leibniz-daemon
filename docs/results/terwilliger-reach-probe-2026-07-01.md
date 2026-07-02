<!--
Task #99 (handoff ticket ①) — the beyond-Table-I discovery reach probe for the Terwilliger three-point
producer. Audit/measurement only; no trust touch; tests/test_invariants.py byte-identical.
-->

# Terwilliger reach probe — the beyond-Table-I discovery test (2026-07-01)

The three-point producer is validated at the audit tier (A(19,6) ≤ 1280 exact + kernel-attested, PRs
#216–#228). This probe asked the question that decides whether the F2b formalization spend has a discovery
payoff: **can the producer *discover* (tighten a current best-known upper bound), or only reproduce?**
Sweep: n = 20..30, d ∈ {6, 8, 10, 12} — 44 cells — against a checked-in, twice-independently-cross-checked
snapshot of Brouwer's table (targeting context ONLY, never a decider), cheap-first: float solve per cell
(CLARABEL → SCS ladder, 120 s hard cap per cell, acceptance gated on floor ≥ known lower bound), exact-LP +
kernel escalation for any floor strictly below the snapshot ub.

## Verdict: **DRY** — 0 certified tightenings; and the sharper finding is *where* the pipeline stops

| measure | result |
|---|---|
| cells swept | 44 (n=20..30 × d∈{6,8,10,12}; Brouwer's table ends at n=28, so n=29,30 gate on the monotonicity lb A(n,d) ≥ A(28,d)) |
| valid floats (floor ≥ known lb) | **9** — d∈{6,8} plus the single d=10 survivor A(21,10)→50; all n ≤ 27 |
| float candidates (floor < snapshot ub) | 2 — **both under-converged solver artifacts** (see below) |
| **certified tightenings** | **0** |
| false certifications / soundness alarms | **0** — one candidate actively refused by the exact-rational decider, one rejected fail-closed (see below) |
| reproduces Table I through the probe harness | A(20,8) → **274** exactly; A(25,8) → 5482 (Table I 5477, float-accuracy gap 5) |
| ties the published ub | A(21,6) → 4096 (= ub); A(22,6) → 6943 (ub 6941 — the missing 2 is AVZ's "2 mod 4" shave, beyond this SDP) |
| solve-leg failures (both solvers crash or floor < lb) | **35/44** — every d∈{10,12} cell with n ≥ 20 except (21,10); every d=6 cell with n ≥ 25; 5 of the 8 d=8 cells below n=28 ((21..24,8), (26,8)); everything at n ≥ 28 |

## The two "candidates" — the trust chain working as designed

1. **A(23,6): SCS floated 13626 < ub 13674.** Schrijver's own three-point value for this cell is 13766, so a
   float 140 below it is SCS under-convergence, not mathematics. Escalation: `certify_lp` needs the CLARABEL
   dual (`extract_dual`), which crashes at this cell → **no exact certificate obtainable → rejected
   fail-closed** (exception → not certified; no exact-rational arithmetic ever ran for this cell).
2. **A(27,8): CLARABEL floated 12445.9 (`optimal_inaccurate`) < ub 17099** (Table I itself is 17768 here —
   again impossible for the same SDP). Escalation: the exact rational LP *did* return a feasible dual
   certificate — with exact bound ≈ 5.9×10⁷, nowhere near 12445 → **not certified** (294 s).

Zero invalid floors were enshrined: the lb acceptance gate rejected every under-converged float (e.g.
A(20,10) CLARABEL "optimal" at 4.4 vs known A = 40), and of the two that slipped between lb and ub, one was
actively refused by the exact-rational decider and one died fail-closed before any exact arithmetic ran —
the decider's demonstrated coverage this run is 1 of 2 candidates, the other rejection being exception
handling that defaults to not-certified. The snapshot never decided anything; it only selected escalation
targets (and its lb gates which floats are accepted at all — a reject-only role).

## What this establishes

1. **The producer cannot currently discover beyond Table I — and the reason is now measured, not assumed.**
   The binding constraint is the **float solve leg** (unnormalized-β conditioning, the panel's Q-pit-2), not
   the exact-LP or kernel legs: CLARABEL crashes outright at (d=6, n≥23) and (most cells, n≥24); SCS returns
   `optimal_inaccurate` values up to ~88× below known lower bounds ((27,12): 1.45 vs lb 128; ~133× against
   the monotonicity lb at (29,8)). The frontier cells with genuine headroom —
   (27,12) ≤ 169 and (28,12) ≤ 288, whose published ubs are pre-SDP (AVZ 2001) — are exactly cells where
   *neither solver produces a usable float*. The discovery question is unreachable there today.
2. **Where the pipeline does solve (d∈{6,8}, n≲25), post-2005 methods already win.** Every valid float other
   than the two refuted/rejected candidates landed at or above the snapshot ub (GMS 2012 quadruple-SDP or
   exact values) — consistent with the honest prior: the 2005 three-point bound was already mined for these
   cells.
3. **d ≥ 10 formulation faithfulness is UNVALIDATED.** Table I's d=10 cells ((22,10)=87, (25,10)=503,
   (26,10)=886) cannot be reproduced with the current solve leg: a k_max-bisect diagnostic at (22,10) shows
   chaotic scatter across both solvers (k=0: CLARABEL 87.4 / SCS 0.4; k=1: CLARABEL 5.9 / SCS 95.9 — archived
   in `docs/results/terwilliger_reach_probe_diagnostic.json` with reproduction instructions) — the
   signature of extreme ill-conditioning rather than a deterministic transcription hole, but a d≥10-specific
   formulation bug **cannot be excluded from float evidence alone**. Until a reliable solve (or an exact
   feasible-point check) reproduces (22,10)=87, no d≥10 output of this pipeline should be trusted even at
   float tier. (All prior formulation-faithfulness validation was d ≤ 8.)
4. **Reproduction-banking:** A(20,8)=274 reproduces through the probe harness; A(25,8) lands within float
   accuracy of Table I. No new cells were banked as exact certificates (none needed for the verdict; the
   candidates were artifacts).

## Honest limitations

- Brouwer's table stops at n=28; n=29,30 have no published target in this source, and the solve leg fails
  there anyway (their few floats were rejected by the monotonicity lb-gate as under-converged).
- The per-attempt records in the JSON are the n-scaling profile: CLARABEL crash onset at ~4600 free variables
  ((23,6)); SCS never crashes but is not usable as a bound producer at these sizes (first-order accuracy).
- `ub_source` attributions in the snapshot are best-effort readings of the page's improvements prose
  (lb/ub values themselves were verified by two independent extractions; one attribution was corrected in
  review). A discovery claim would require independent re-verification of the snapshot value regardless.

## Implication for the direction (operator decision input)

- **F2b is infrastructure, not discovery-motivated, today.** The probe removes the "maybe the machinery
  discovers as-is" branch: without a solve-leg fix there is nothing new for F2b to certify. (F1/F2a remain
  valuable for what is already banked.)
- The cheapest path that could *reopen* the discovery question is the already-roadmapped **solve-leg fix**
  (normalized/rescaled β blocks and/or SDPA-GMP, panel D6 / Q-pit-2) — it would (a) put the pre-SDP-ub cells
  (27,12), (28,12) genuinely in reach of the question, and (b) unblock the d≥10 faithfulness validation
  ((22,10)=87 reproduction), which is a prerequisite for trusting any d≥10 discovery anyway.
- The alternative discovery routes from the scope doc (eq. (25) sharpenings; the Johnson-scheme build D1;
  post-2005 hierarchies) are unaffected by this probe's DRY — but all of them run through the same solve
  leg, so D6 likely comes first regardless.

Artifacts: `docs/results/terwilliger_reach_probe.json` (per-cell, per-attempt, escalations; the JSON's
`above_known_lb` field means only "not refuted by the known lower bound", never a validity claim),
`docs/results/terwilliger_reach_probe_diagnostic.json` (the solver-collapse / k_max-bisect diagnostic),
`docs/data/brouwer-snapshot-2026-07.json` (the cross-checked targeting snapshot).
Harness: `scripts/terwilliger_reach_probe.py`. Test: `tests/test_terwilliger_reach_probe.py`.

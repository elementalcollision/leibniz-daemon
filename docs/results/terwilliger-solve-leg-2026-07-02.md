<!--
Roadmap D6 / Q-pit-2 — the solve-leg fix the task #99 reach probe identified as the binding constraint, plus
the d>=10 formulation-faithfulness validation it unblocks. Audit/measurement only; no trust touch;
tests/test_invariants.py byte-identical.
-->

# Terwilliger solve-leg fix (D6 / Q-pit-2) + the d ≥ 10 faithfulness verdict (2026-07-02)

> **SUPERSEDED IN PART (same day — D2, task #103, PR #238):** resolution path (a) below landed and REFUTES
> two claims in this doc. (1) "target 87 does not certify at any tried precision" — it **does** certify:
> the k_max-truncated dual, zero-padded on the dropped blocks, is a feasible full-problem dual, and the
> exact LP through it certifies **A(22,10) ≤ 87.9734 → 87**, kernel-attested. (2) The 87.97 "stall
> attractor" was **not** a provable under-solve — it was the honest truncated optimum all along; the
> "proof" leaned on the pseudo-feasible 88.63 full-solve point, which the exact tier shows infeasible.
> Likewise "(26,10): still stalls … Recorded, not reproduced" is closed: **A(26,10) ≤ 886** certifies the
> same way. See `docs/results/terwilliger-anomaly-2026-07-02.md` + `docs/results/terwilliger_anomaly.json`;
> the text below is kept unedited as the measurement record.

The reach probe (task #99) measured that the three-point pipeline's binding constraint is the **float solve
leg**: CLARABEL crash onset at ~4600 free variables ((23,6)), SCS under-convergence up to ~88×, every
d ∈ {10,12} cell with n ≥ 20 failing both solvers, and chaotic k_max-bisect scatter at (22,10). This session
fixed the leg and ran the d ≥ 10 validation that was blocked behind it.

## The fix (two parts, both measured)

1. **Schrijver's own eq. (8) block normalization, restored for the float solve only.** The repo's integer β
   deletes the paper's `C(n−2k,i−k)^{−1/2} C(n−2k,j−k)^{−1/2}` factor (right for the exact/kernel legs; raw β
   spans 1..~10¹³ by n=26 — the measured Q-pit-2 wall). `terwilliger_sdp._block_exprs(normalize=True)` puts it
   back — a positive diagonal congruence, so **exactly** PSD-equivalent: the feasible set and optimum are
   untouched (guarded by `test_normalization_is_optimum_preserving`). A further per-block scalar (max
   coefficient → 1) was tried and **rejected**: it un-balances blocks against the untouched objective and
   measurably degrades solves (A(19,6): 1280.08 → 1289.46).
2. **SDPA-GMP backend** (`pip install sdpa-multiprecision`, operator-local, `find_spec`-gated) at
   measured-tight settings (`SDPA_TIGHT`: epsilonStar 1e-12, 350-bit; looser stops early — (20,8) "optimal" at
   277.1 instead of 274.09). The pairing matters and is encoded in `_solver_defaults`: SDPA needs the
   normalized blocks (raw β → SolverError); CLARABEL is *better raw* (its cone equilibration fights the
   congruence: 1280.08 raw vs 1281.09 normalized at (19,6)) and stays the byte-compatible fallback when sdpap
   is absent. `extract_dual` maps the normalized blocks' duals back to the unnormalized-β objects
   (Z = D·Z̃·D), so the exact-rational legs are unchanged.

## Success tests (the ticket's gate) — all pass

| cell | before (probe) | after | Table I |
|---|---|---|---|
| A(19,6) | 1280.08 `optimal_inaccurate` | **1280.036 `optimal`** → 1280 | 1280 ✓ |
| A(20,8) | 274.56 `optimal_inaccurate` | **274.086 `optimal`** → 274 | 274 ✓ |
| A(23,6) | **CLARABEL crash** | **13766.139 `optimal`** → 13766 (in ~10 s) | 13766 ✓ |

Exact-LP regression: `certify_lp(19,6,target=1280)` still certifies through the SDPA dual (12 s, P=1e12).

**Two new exact-rational certificates banked** (certify_lp escalation, dual_check-validated, same audit tier
as the A(19,6) cert; kernel render is one `kernel_verify_lp` call away):
- **A(23,6) ≤ 13766** (exact bound 13766.1899, P=1e14, LP leg ~52 s) — the second Table I record cell.
- **A(25,10) ≤ 503** (exact bound 503.7887, P=1e14, ~19 s) — **the first d ≥ 10 exact certificate**.

## d ≥ 10 formulation faithfulness — validated, with one measured anomaly

- **(25,10) = 503: reproduced exactly at both tiers** (float `optimal` 503.828; exact certificate above).
  With (19,6)/(20,8)/(23,6) also exact, the transcription is faithful wherever a converged solve exists —
  including d = 10. The reach probe's "d ≥ 10 UNVALIDATED" is closed.
- The task's suspicion (zero-substituted `x0i+x0j ≤ 1+x` γ-constraints spuriously strong for d ≥ 10) is
  **resolved as a non-bug**: the substituted constraint is provably valid for real codes whenever the (i,j,t)
  shape is combinatorially possible (average the pointwise boolean inequality 1a+1b ≤ 1+1a1b over the
  configuration space; `possible()` gates exactly that), and Schrijver's program contains the same constraints
  (eq. (10) zeroes impossible shapes; (iv) zeroes forbidden distances — checked against the paper).
- **(26,10): still stalls** (948.33 `optimal_inaccurate` vs Table I 886, Delsarte 1040.2). The stall is
  structural, not precision: identical to the last digit at 350/700/1200 bits. Recorded, not reproduced.
- **(21,12) = 8 exact** now solves cleanly (both solvers collapsed here in the probe diagnostic).

### The (22,10) anomaly — measured, characterized, open

Table I says 87 (Delsarte column 95 — ours matches: 95.3191). Our fixed leg gives, across solvers, k_max
truncations and parameter sets, values on **both** sides of the exact tier:

- **Exact tier (decides):** `certify_lp(22,10)` certifies **A(22,10) ≤ 88** (best exact bound 88.2463 at
  P=1e14); **target 87 does not certify at any tried precision**.
- Float stall attractor at **87.97** (floor 87!): hit by SDPA at k_max ∈ {2,3} and on a caps-augmented run
  that claimed `optimal` — both provably under-solves (a truncation cannot be below the full optimum; the
  added caps were satisfied by the higher-valued point). Two solver families reproduce this attractor.
- Float pseudo-optimum at **88.63**: a point auditing at −7e-19 block eigenvalue / 2.7e-10 linear violation —
  yet **0.38 above the exact certificate**. The certificate's multipliers reach 1.5e9, so 1e-10 violations
  are worth tenths of objective: **at this conditioning, no float-side audit is a bound in either
  direction** (this is the session's most important negative lesson; the harness JSON encodes it).
- **eq. (25) constant-weight caps cannot bridge 88 → 87**: at the relevant points A₁₀ = 66.4 < 72
  (Schrijver's own Table II cap) and every other weight's Johnson-chain cap is slack — and the paper states
  Table I was computed *without* (25) anyway.

What this does **not** say: that Table I is wrong. It says our transcription — exact at four other cells,
including another d=10 cell — certifies 88 and cannot see 87, while a demonstrated 2005-era failure mode
(double-precision stall at 87.97, floor 87; SDPT3/DSDP era) exists in this exact geometry. Resolution paths,
in cost order: (a) a better dual for the exact LP (the current one is capped by the stalled float dual);
(b) an independent three-point implementation cross-check (post-2005 practice — e.g. the split-Terwilliger
paper, arXiv:2203.06568 — bolts Best/MEL-type linear cuts onto the SDP, which are *outside* Schrijver's
published program and could account for 87 if his actual run included any); (c) ask the author/community.
Brouwer's table attributes (22,10) ≤ 87 to "Schrijver, personal communication, March 2004".

## The k_max ladder at (22,10), re-measured

Probe (chaotic): k0 CLARABEL 87.4 / SCS 0.4; k1 5.9 / 95.9. Fixed leg: **95.32 → 93.06 → 87.97 → 87.97 →
(full) 88.63** — clean except the full-problem uptick, which is the under-solve fingerprint above, not
scatter.

## Frontier cells (the probe's "genuine headroom") — now measured, and closed

- **(27,12): three-point = 170.667 = Delsarte exactly** (`optimal`). The published 169 (AVZ 2001, pre-SDP) is
  *better than the three-point bound here* — the k ≥ 1 blocks add nothing at this cell.
- **(28,12): 288.000 = Delsarte = published ub** — a tie, no headroom.

The discovery question at these cells is no longer solver-blocked — it is **bound-blocked**: the three-point
SDP itself has nothing to give there. Discovery needs a stronger bound (eq. (25) sharpenings help nothing at
d=12 frontier cells either — they are Delsarte-tight; the Johnson-scheme build D1 or post-2005 hierarchies).

## Artifacts / repro

`docs/results/terwilliger_solve_leg.json` (per-cell rows incl. audit violation profiles, the k_max ladder,
and the exact-certificate escalation) — regenerate with `python3 scripts/terwilliger_solve_leg.py`
(operator-local: cvxpy + numpy + sdpap + scipy; ~5 min; CI-skips clean). Solver/normalization changes:
`scripts/terwilliger_sdp.py` (`_block_exprs`, `_solver_defaults`, `SDPA_TIGHT`), dual un-scaling:
`scripts/terwilliger_cert.py::extract_dual`. Tests: `tests/test_terwilliger_sdp.py` (normalization
equivalence, defaults pairing, the (23,6) crash cell, (25,10) d≥10 faithfulness). Dependency:
`pip install sdpa-multiprecision` (wheels exist for the operator's cp310/cp314; gmp via brew).

# Terwilliger constant-weight (Johnson-scheme) build — D1, task #102 (2026-07-02)

**Verdict: GREEN through all three build rungs** (structure oracle / Table II faithfulness / exact+kernel
legs); reach-probe verdict recorded in the probe section below. Audit tier throughout
(`DUAL_CERTIFICATE_CHECKED`); no trust surface touched; `tests/test_invariants.py` byte-identical.

## What this is

The discovery-pivot ticket D1 (`docs/handoff-terwilliger-discovery-2026-07-02.md`): a *separate* algebra
build targeting Schrijver 2005 **Section III** — upper bounds on A(n,d,w) (binary constant-weight codes) via
the Terwilliger-style block-diagonalization of the S_w × S_v tensor algebra (v = n − w). The banked
unrestricted pipeline is reused wholesale; only the structure is new:

- **Variables** y^{t,s}_{i,j} on ordered triples of weight-w words with basepoint X: i = |X\Y|, j = |X\Z|,
  t = |(X\Y)∩(X\Z)|, s = |(Y\X)∩(Z\X)| (all pairwise distances are even: |X△Y| = 2i). Normalization
  eq. (62): μ / (|C|·binom(w; i−t,j−t,t)·binom(v; i−s,j−s,s)); either multinomial zero ⇒ not a variable
  (the `possible()` trap, enforced).
- **Orbit merge** (65)(iii): key = (sorted{i, j, i+j−t−s}, t−s) — |X△Y△Z| = w+2t−2s is permutation-
  invariant, so t−s survives in the key.
- **Blocks** (58)/(64): for every (k,l), k ≤ ⌊w/2⌋, l ≤ ⌊v/2⌋ with W_k∩V_l ≠ ∅, two PSD families on index
  set {max(k,l)..min(w−k,v−l)} with coefficient **β^{t,w}_{i,j,k} · β^{s,v}_{i,j,l}** — a product of two
  eq.(7) β's (the Phase-0-validated generator, evaluated at ground sets w and v). No new β transcription
  risk beyond the product structure itself, which the differential oracle below validates.
- **Objective** (67): Σ_i C(w,i)·C(v,i)·y^{0,0}_{i,0} = |C| (eq. 66).

## Code map (all new; banked scripts untouched)

- `scripts/terwilliger_cwc_beta.py` — structure + the free-CPU differential oracle.
- `scripts/terwilliger_cwc_dual.py` — mechanical dual; **`collected()` here is the authoritative
  stationarity spec for this family**; `dual_check` is the exact checker.
- `scripts/terwilliger_cwc_sdp.py` — cvxpy primal; `TABLE_II` (all 55 published cells) + `LOWER`;
  reuses `terwilliger_sdp._solver_defaults` (SDPA-GMP tight + eq.(58) normalization when `sdpap` present).
- `scripts/terwilliger_cwc_cert.py` — exact leg (reuses `terwilliger_exact_lp.exact_simplex` +
  `terwilliger_cert._round_psd`) and kernel leg (reuses `cert_psd_blocks`/`render_cert_lean`).
- `scripts/terwilliger_cwc_probe.py` — snapshot builder + reach probe (ticket-① protocol).
- `tests/test_terwilliger_cwc.py` (18 tests; solver legs CI-skip), snapshot
  `docs/data/brouwer-cwc-snapshot-2026-07.json`, results JSONs `docs/results/terwilliger_cwc_*.json`.

## Gate results (measured 2026-07-02, operator machine)

**Step 1 — structure oracle: GREEN** (`terwilliger_cwc_beta.json`). Every real constant-weight code's
blocks (both families, all (k,l)) exactly PSD across (n,w) ∈ {(4,2),(5,2),(6,3),(7,3),(8,4),(9,3)}
including Fano STS(7) and AG(2,3) STS(9); eq.(66) counting identity and (65)(iii) orbit-constancy exact on
every test code; the transposed-binomial corruption of the w-side β factor breaks PSD (teeth). Runtime 0.4 s.

**Step 2 — Table II faithfulness gate: GREEN 3/3** (`terwilliger_cwc_sdp.json`). SDPA-GMP floats:

| cell | our SDP | floor | Schrijver Table II | Delsarte col |
|---|---|---|---|---|
| A(17,6,7) | 228.999 | **228** | 228 | 249 |
| A(18,6,6) | 199.883 | **199** | 199 | 204 |
| A(17,6,8) | 280.666 | **280** | 280 | 283 |

plus 7/7 plumbing cells exactly at known optima (d=2 Johnson spaces 6/10/20; Steiner cells
A(6,4,3)=4, A(7,4,3)=7, A(8,4,4)=14, A(9,4,3)=12 — the SDP is tight there). No cell floors below a known
lower bound. This is the constant-weight analogue of the unrestricted build's (19,6)/(20,8) gate.

**Step 3 — exact + kernel legs: GREEN 7/7 + kernel sound** (`terwilliger_cwc_cert.json`). Exact rational
dual certificates (stationarity residuals exactly 0, blocks exactly PSD, multipliers ≥ 0) at all seven
cells; **A(17,6,7) ≤ 228 kernel-attested**: the real Lean 4.31 kernel accepts all 46 PSD blocks (largest
8×8) and rejects a corrupted-block control. Note **(17,6,7) certifies only at P=1e14** — the SDP optimum
228.999 leaves ~10⁻³ of rounding headroom below 229 (same precision-matters-for-the-bound behavior as the
unrestricted D6 cells); (17,6,8) needs P=1e10 (~14 s); small cells certify at P=1e6 in <0.1 s.

## Reach probe (step 4) — `terwilliger_cwc_probe.py`, `terwilliger_cwc_probe.json`

**Snapshot**: `docs/data/brouwer-cwc-snapshot-2026-07.json` — 820 cells parsed from Brouwer's
https://aeb.win.tue.nl/codes/Andw.html (fetched 2026-07-02, sha256 recorded), **validated before writing**
(Probe-α safeguard): ground-truth anchors, ub ≥ lb, lb monotone in n, **0 unparsed cells**, and a
cross-check against the independently-fetched 2026-06-27 validated lower-bound oracle
(`cwc_table_oracle.py`): **816 shared cells, 0 disagreements**. Page conventions encoded: unmarked ubs
(n ≤ 28) are AVZ 2000; sharper sources marked (`S` = Schrijver 2005, `Po` = Polak, …); single value =
settled; d=4 section is lower-bounds-only (dot = optimum); `-...` = no explicit ub. The snapshot is
**targeting context only, never a decider**.

**Sweep scope**: all 185 open cells (lb < ub) with d ∈ {6,8,10,12}, n ≤ 28, cheap-first by free-variable
count (max 537 vars — this family is far smaller per cell than the unrestricted one at equal n; no
Q-pit-2-class wall was hit). Acceptance gate: floor ≥ snapshot lb. Escalation (exact LP at P ≤ 1e14 →
kernel) fires only on floors strictly below the snapshot ub.

**RESULT — verdict `DRY` (sweep completed in-session after an interim partial flush):** 185/185 cells
attempted, **179 solved, 0 candidates, 0 invalid floors, 0 escalations**. Unsolved (honest scaling record):
5 per-cell time-caps (120 s) at the largest cells — (27,6,13), (28,6,13), (28,6,14), (28,8,13), (28,8,14) —
plus one SolverError at (28,8,12); all n ≥ 27, w ≥ 12. **Faithfulness bonus: 47/51 swept Table II cells
reproduce Schrijver's published value exactly through the harness** (including the still-standing `S`-record
cells (21,6,10)→2685 and (22,6,9)→3736 — so no loose-2005-float re-mining opportunity exists at these
cells). The 4 non-reproductions — (23,8,10)→1061 vs 1025, (26,10,13)→756 vs 754, (26,12,11)→78 vs 66,
(28,12,10)→88 vs 87 — are all `optimal_inaccurate` floats stalling ABOVE the table value (never below; the
floor ≥ lb gate held everywhere). Reading: the three-point constant-weight bound is
**reproduction-complete** in this range, and every open cell's current record (AVZ 2000 or later) already
sits at or below what the three-point SDP can give — discovery here is bound-blocked exactly like the
unrestricted family, pointing at D3 (post-2005 hierarchies) / eq.(25)-style sharpenings, not more solver.

## Facts a fresh session should not re-measure

- Structure sizes at the gate cells: (17,6,7) = 62 free vars, 23 block pairs, largest block 8; (17,6,8) =
  79 vars; (18,6,6) = 40 vars. Full-cert kernel leg: 46 blocks ≈ 30 s round trip including both controls.
- Solve times (SDPA-GMP tight): gate cells ≈ 2 s; probe cells 2–60 s up to ~460 vars; the 120 s cap fires
  only at the five largest cells (n ≥ 27, w ≥ 13, ~460–537 vars). `optimal_inaccurate` shows up on some
  d ∈ {10,12} cells — floats there are targeting data only (the exact leg decides, as always).
- The d=4 constant-weight family is excluded from the sweep by design (no ubs on the page; Table II has no
  d=4 cells; design-theory bounds dominate there).
- Brouwer page layout traps for the parser: `<td class=...>` variants (a bare `<td>` regex silently shifts
  columns — caught by the monotonicity+cross-check validators), transposed continuation tables for n ≥ 29
  (skipped; out of scope), double superscripts, dot-after-superscript optima.

## Trust posture

LLM judgment decided nothing here. Every bound claim = exact rational dual feasibility (`dual_check`,
free-CPU) with the kernel leg attesting PSD blocks on the real Lean 4.31 kernel; floats (SDPA/Clarabel) are
targeting/warm-start data only. The snapshot gates *targeting*, never soundness. Formulation faithfulness
for this family is empirical (Table II gate) exactly as for the unrestricted family (Table I gate) — the
bridge theorem (F2b) remains the only path past that, hence audit tier.

## Next steps

- **D2 (task #103)**: the (22,10) anomaly — unchanged, parallelizable.
- **D1 is DRY** → the discovery weight shifts to **D3** (post-2005 hierarchy scoping, task #104) and to
  eq.(25)-style sharpenings of the *unrestricted* build, which now have a live, validated A*(n,d,i) oracle
  (this snapshot) to draw caps from.
- The `S`-marked re-mine channel is now MEASURED CLOSED: the standing Schrijver-2005 record cells
  ((21,6,10) ub=2685, (22,6,9) ub=3736, …) reproduce exactly at float — his 2005 floors were not loose.
  Optional tidy-up, not discovery: exact+kernel-certify the 4 `optimal_inaccurate` cells at their Table II
  targets (same recipe as the gate cells, P ≤ 1e14).

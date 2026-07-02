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

**RESULT — PARTIAL SWEEP (landed honestly):** the session ended mid-probe; the artifact records **141 cells, 0 candidates, 0 escalations** with verdict `RUNNING` (its generated state — not a DRY claim). The three BUILD rungs above are complete and GREEN; finishing the sweep is queued as a follow-up (re-run `python3 scripts/terwilliger_cwc_probe.py`).

## Facts a fresh session should not re-measure

- Structure sizes at the gate cells: (17,6,7) = 62 free vars, 23 block pairs, largest block 8; (17,6,8) =
  79 vars; (18,6,6) = 40 vars. Full-cert kernel leg: 46 blocks ≈ 30 s round trip including both controls.
- Solve times (SDPA-GMP tight): gate cells ≈ 2 s; the probe's largest cells (n=28, w=13..14, ~500 vars)
  tens of seconds. `optimal_inaccurate` shows up on some d ∈ {10,12} cells — floats there are targeting
  data only (the exact leg decides, as always).
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
- **D1 follow-ups if the probe is DRY**: eq.(25)-style sharpenings now have a live A*(n,d,i) oracle (this
  snapshot); post-2005 hierarchy scoping is D3 (task #104).
- The `S`-marked cells (Schrijver-2005 records still standing: e.g. (21,6,10) ub=2685, (22,6,9) ub=3736)
  are the natural re-mine targets: a 2005 float floor can be loose; our exact leg certifies the true
  optimum's floor. The probe covers them in-scope.

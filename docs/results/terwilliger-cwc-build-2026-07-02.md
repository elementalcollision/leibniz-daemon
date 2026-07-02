# Terwilliger constant-weight (Johnson-scheme) build — D1, task #102 (2026-07-02)

**Verdict: GREEN through all three build rungs** (structure oracle / Table II faithfulness / exact+kernel
legs); **reach probe DRY** (full 185-cell sweep, 0 certified tightenings — the honest-expected outcome for
this less-mined family). Audit tier throughout (`DUAL_CERTIFICATE_CHECKED`); no trust surface touched;
`tests/test_invariants.py` byte-identical. Hardened by the D1 8-angle adversarial review (see the
"Adversarial review" section) — soundness tripwires, verdict honesty, kernel-attestation integrity, and
parser/snapshot completeness gates now match the sibling unrestricted build's discipline.

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
- `scripts/terwilliger_cwc_sdp.py` — cvxpy primal; `TABLE_II` (all 57 published cells) + `LOWER`;
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
dual certificates (stationarity residuals exactly 0, blocks exactly PSD, multipliers ≥ 0, and — the soundness
tripwire the float legs already carry — bound ≥ the known lower bound) at all seven cells. **A(17,6,7) ≤ 228:
exact-rational certified; its 46 PSD blocks are kernel-attested** — the real Lean 4.31 kernel accepts all 46
(largest 8×8), rejects a corrupted-block control, and a trivially-true liveness probe confirms the rejection
was the *kernel's* verdict (not a docker hiccup). **Scope of the kernel leg (honest):** it attests block
PSD-ness only; the stationarity system and the bound arithmetic Σγ−ν ≤ target are checked in exact Python
(`dual_check`), NOT by the kernel — the F2b bridge theorem remains the only path past that, which is why this
family stays audit-tier `DUAL_CERTIFICATE_CHECKED`, not Q.E.D. The artifact records
`kernel_attests_recorded_cert` so the attested blocks are provably those of the certificate whose bound it
reports. Note **(17,6,7) certifies only at P=1e14** — the SDP optimum 228.999 leaves ~10⁻³ of rounding
headroom below 229 (same precision-matters-for-the-bound behavior as the unrestricted D6 cells);
(17,6,8) needs P=1e10 (~14 s); small cells certify at P=1e6 in <0.1 s.

## Reach probe (step 4) — `terwilliger_cwc_probe.py`, `terwilliger_cwc_probe.json`

**Snapshot**: `docs/data/brouwer-cwc-snapshot-2026-07.json` — 843 cells parsed from Brouwer's
https://aeb.win.tue.nl/codes/Andw.html (fetched 2026-07-02; **sha256 computed from the page bytes**, not a
flag, and cross-checked against the recorded hash), **validated before writing** (Probe-α safeguard):
ground-truth anchors, ub ≥ lb, lb monotone in n, **an omission gate** (every old-oracle cell in a parsed
d-section must survive the new parse — closes the earlier silent drop of 23 `<td>`-labeled rows), **a ub
cross-check** (every published-cell ub ≤ its Schrijver Table II value — the only validator that touches the
ub side, which drives all targeting), **0 unparsed cells**, and a cross-check against the
independently-fetched 2026-06-27 validated lower-bound oracle (`cwc_table_oracle.py`): **839 shared cells, 0
disagreements**. Page conventions encoded: superscripts mark the ub/lb source (`S` = Schrijver 2005, `Po` =
Polak, `KKT`/`KT`/`Mo`/… later work); an *unmarked* ub has no uniform provenance (it can be a post-2005
improvement, e.g. A(18,6,6) ub 186 < Schrijver's 199 — so unmarked is NOT "AVZ 2000"); single value =
settled; d=4 section is lower-bounds-only (dot = optimum); `-...` = no explicit ub. The snapshot is
**targeting context only, never a decider**.

**Sweep scope**: all 185 open cells (lb < ub) with d ∈ {6,8,10,12}, n ≤ 28, cheap-first by free-variable
count (max 537 vars — this family is far smaller per cell than the unrestricted one at equal n; no
Q-pit-2-class wall was hit). Acceptance gate: floor ≥ snapshot lb; a valid solver *optimum* that floors
*below* the snapshot lb is a soundness alarm (a wrong transcription can under-bound), surfaced — not folded
into a generic solver-failure status. Candidacy is optimistic at the ub boundary (a true optimum a hair below
an integer ub floors up under the +1e-6 acceptance bump, so the raw-value floor is also tested; escalation is
cheap, a missed record is not). Escalation certifies against the **discovery threshold** (snapshot ub − 1,
the smallest strict tightening — never the loose float floor, which would report a certifiable record as DRY)
via exact LP at P ≤ 1e14 → kernel, and carries the same known-lb tripwire.

**RESULT — DRY (full sweep, 2026-07-02).** All 185 in-scope cells attempted; **179 solved** (170 clean
`optimal`, 9 `optimal_inaccurate`), 6 unsolved on the largest n=28 cells (5 time-cap at 120 s, 1
`no_valid_float`, ~440–537 vars). **0 candidates, 0 certified tightenings, 0 below-lb soundness alarms.** No
solved floor lands below its snapshot ub — the closest cells *reproduce* the published record exactly
(A(21,6,10) floor 2685 = ub 2685^S; A(22,6,9) floor 3736 = ub 3736^S), never beat it. This is the
honest-expected outcome: constant-weight is a less-mined family, and the post-2005 `S`/`Po`/`KKT` sources on
these cells already reflect SDP-class bounds our exact leg reproduces rather than improves. The new
faithfulness tripwire (`table_II_regressions`) flags **4 cells whose float floor exceeds the published Table
II bound — but all 4 are `optimal_inaccurate` (float non-convergence on d ∈ {8,10,12}), 0 at clean `optimal`
status**, so none is a formulation regression (a clean-optimal floor above the published bound would be; there
are none). The exact leg remains the decider; these floats are targeting data only. **No GREEN(candidate) —
nothing to surface to the operator.**

## Adversarial review (D1 8-angle, 2026-07-02)

The D1 build got the same 8-angle adversarial review PR #238 got (57-agent workflow: 8 angle-specific finders
→ dedup → per-finding refute/reproduce/tiebreak verification). **The central result survives**: no finding
refutes the three build rungs, the A(17,6,7) ≤ 228 certificate, or the DRY probe verdict. 24 findings were
confirmed; all confirmed code findings are fixed here (regression-gated: full local suite green; A(17,6,7)
kernel-attests; `tests/test_invariants.py` byte-identical; no trust surface touched). Highlights:

- **Decider soundness tripwire (the load-bearing fix).** The exact-LP decider certified on the one-sided
  `⌊bound⌋ ≤ target` with no *lower*-bound guard, while every float layer already refused sub-lb floors
  (`valid_bound`). A too-low (even mathematically impossible) exact bound would have certified GREEN. Now
  `certify_lp(…, lb=…)` refuses `⌊bound⌋ < lb` and raises a `soundness_alarm`; the probe's `escalate`/main and
  `cert.main` thread `tcs.LOWER` through. This is the exact class the #238 review found on the anomaly build.
- **Discovery-threshold escalation.** `escalate` certified against the *float floor*, so an exact certificate
  landing between the float floor and the snapshot ub — a genuine record — reported DRY. It now certifies
  against the discovery threshold (ub − 1); optimistic ub-boundary candidacy stops a hair-below-integer
  optimum from being floored away.
- **Verdict honesty.** New verdicts distinguish a decider that *ran and refused* (DRY) from one that
  time-capped/errored on a live candidate (`UNDECIDED`) and from a solved optimum below a known lower bound
  (`SOUNDNESS-ALARM`). `reproduces_table_II`, previously computed-but-unread, now aggregates `table_II`
  faithfulness regressions across the un-gated Table II range.
- **Kernel-attestation integrity.** The kernel leg re-derived a *second* certificate; it now attests the
  exact certified certificate's blocks (`kernel_attests_recorded_cert`), refuses a short block census
  (a dropped singular block ≠ `sound`), distinguishes a docker/daemon failure from a genuine kernel rejection
  via a liveness probe, and is crash-wrapped so a kernel-leg failure never erases the exact certificates.
  The doc/artifact claim is de-overstated: **the kernel attests block PSD-ness only** (stationarity + bound
  are exact-Python), F2b remains the bridge.
- **Faithfulness gate.** The step-2 gate went GREEN if a gate cell *crashed* (errored rows dropped from the
  denominator); it now gates on the configured cell sets.
- **Snapshot/parser completeness.** `<td>`-labeled rows were silently dropped (23 cells, all out of scope but
  invisible to every validator); the parser now accepts th-or-td labels, and `build_snapshot` adds an
  omission gate, an independent ub ≤ Table II cross-check, and real byte-computed sha256 provenance. Snapshot
  is now complete at **843 cells** with the in-scope 366 byte-identical (probe result unaffected).
- **Test teeth.** Added negative coverage for `dual_check`'s PSD/nonneg conjuncts (incl. an asymmetric-Z
  guard), a flagship artifact-consistency test pinning A(17,6,7)@P=1e14, and a stubbed kernel block-census
  test; fixed a vacuous `valid_bound` assertion.

**Deferred — dedup (coordinates with the pending #238-fixes chip "lift k_max rescue into shared modules").**
The five cwc scripts are ~700 lines of near-verbatim forks of the banked unrestricted pipeline, and the
`_load`-by-path pattern re-executes modules. This should fold into the *same* shared-module lift, parameterized
over a small structure object (`free_keys/canon/classify/obj_coeff/possible/valid_quads/block_pairs/block_idx`
+ a β-coefficient callback). **Load-bearing coordination note for that chip:** findings *decider-lb-tripwire*,
*escalate-float-floor*, *below-lb-evidence*, *verdict-undecided*, and *subprocess-crash* have **identical
analogues in the parent** `scripts/terwilliger_reach_probe.py` + `scripts/terwilliger_exact_lp.py` — the lift
must apply the same fixes there so the unrestricted probe stops emitting the same wrong verdicts/status.

## Facts a fresh session should not re-measure

- Structure sizes at the gate cells: (17,6,7) = 62 free vars, 23 block pairs, largest block 8; (17,6,8) =
  79 vars; (18,6,6) = 40 vars. Full-cert kernel leg: 46 blocks ≈ 30 s round trip including both controls.
- Solve times (SDPA-GMP tight): gate cells ≈ 2 s; the probe's largest cells (n=28, w=13..14, ~500 vars)
  tens of seconds. `optimal_inaccurate` shows up on some d ∈ {10,12} cells — floats there are targeting
  data only (the exact leg decides, as always).
- The d=4 constant-weight family is excluded from the sweep by design (no ubs on the page; Table II has no
  d=4 cells; design-theory bounds dominate there).
- Brouwer page layout traps for the parser: `<td class=...>` data-cell variants (handled by `<td[^>]*>`);
  **`<td>`-labeled rows** — the n-label as `<td>` not `<th>`, used for n=33–35 in the d=18 section — which a
  `<th>`-only label match dropped whole (now: first-cell th-or-td label + an omission gate that fails the
  build if any old-oracle cell in a parsed d-section vanishes); transposed continuation tables for n ≥ 29
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

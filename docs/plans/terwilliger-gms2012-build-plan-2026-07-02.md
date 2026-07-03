<!--
Build plan: GMS 2012 quadruple-distance SDP producer. Operator decision 2026-07-02 — commit to building
toward GMS, gated by a front-loaded 1-2 day spike. Grounded in the D3 scoping doc
(docs/results/terwilliger-d3-hierarchy-scoping-2026-07-02.md) and the proven D1 constant-weight ladder.
REVISED 2026-07-02 (review response) after a 6-reviewer external witness panel
(docs/results/terwilliger-gms-witness-review-2026-07-02.md): GATE 0 block-size probe added as the front kill
gate; Johnson≠Hamming caveat; iterative active-set + M0-by-hand notes; amplification-tier + horizontal-infra
framing. Audit tier throughout; no trusted-surface edit; tests/test_invariants.py stays byte-identical.
-->

# Build plan — GMS 2012 quadruple-distance SDP producer

**Decision (operator, 2026-07-02):** the GMS direction is directionally correct; **build toward it**, front-gated
by a cheap spike. This plan sequences a 1–2 day GO/NO-GO spike (Phase 0) and, on GO, the 4–6 week build
(Phases 1–6) via the same measure-before-build ladder that took D1 (constant-weight) to GREEN.

**Reference**: A. Schrijver, D. Gijswijt, H. Mittelmann, *Semidefinite code bounds based on quadruple
distances*, IEEE Trans. Inf. Theory 58 (2012) 2697–2705 (arXiv:1005.4959). The bound is
`A_4(n,d) = max { Σ x({v}) : x(∅)=1, M_S(x) ⪰ 0 for all S ∈ C_4 }`, block-diagonalized under the symmetry
group so the PSD constraints reduce to polynomially-many doubly-indexed `(k,l)` blocks.

**Load-bearing caveat — Johnson ≠ Hamming (added in review response).** This plan's central reuse claim is that
GMS's product-β blocks are "the same objects" our D1 constant-weight build already ships. That is **a hypothesis
GATE 0 must confirm, not a fact**. D1 (`terwilliger_cwc_beta.py`) is the **Johnson-scheme** (constant-weight)
quadruple: `block_idx(w,v,k,l)` returns a *single-index O(n) range* and D1 kernel-verified a 26×26 block — which
is our positive evidence that the **reduced** blocks are O(n), **not** the O(n²) the witness panel's alarm
implies (Fugu's 841×841, Qwen's >100×100 reason about the *unreduced* moment matrix, which the
block-diagonalization exists precisely to avoid forming). BUT GMS 2012 is the **Hamming-scheme** (unrestricted
binary) quadruple — reduction group S_n vs Johnson's S_w×S_v — so the `(k,l)` *indexing pattern* transfers while
the β formula, block dimensions, and multiplicities may differ. Whether the Hamming quadruple *also*
block-diagonalizes to O(n) is exactly what GATE 0 measures.

## Two objectives, one build — decide which BEFORE Phase 1

D3 measured that GMS's **discovery** EV is near-zero (its records are already the current best-known values —
most in the Brouwer n=20..28 snapshot, A(19,6)≤1237 at n=19; the only unmined cells sit behind the
exact-solver wall). But GMS as a **verification-amplification** producer — kernel-tier
re-derivation of the *current* records A(19,6)≤1237, A(20,8)=256, A(23,6)≤13674, A(22,10)≤84, A(25,10)≤466 —
is a legitimate, unconditional win. **The two objectives share Phases 1–5; they differ only in Phase 6 and in
the Phase 0 gates.** State the objective explicitly at kickoff:

- **DISCOVERY track** — requires Phase 0 GATE 1 + GATE 2 to pass. Target: the pre-SDP frontier cells.
- **AMPLIFICATION track** — Phase 0 is reduced to a single faithfulness pre-check (GATE 1′ below); no discovery
  gate. Target: re-derive + kernel-attest the published GMS records. GO on this basis alone (ADR-0046 tier).

## Phase 0 — the front gate (1–2 days, ZERO production code)

**GATE 0 runs FIRST and kills BOTH tracks** — the external witness panel (6 reviewers, 2026-07-02,
`docs/results/terwilliger-gms-witness-review-2026-07-02.md`) converged that the block-size/algebra fact must be
*measured*, not assumed, before any provenance or solver work. It is the cheapest gate and the one most likely
to be RED.

| Gate | Question | Method | Pass bar |
|---|---|---|---|
| **GATE 0** (BOTH tracks — run first) | Does the GMS *Hamming* quadruple β match our product-β, and do the **reduced** blocks stay O(n) (not O(n²))? | ZERO CPU: compute the actual GMS quadruple β at n=6 from GMS 2012 §III / the block-diagonalization eqs (arXiv:1005.4959) and diff against our product-β; then compute the reduced block-dimension profile for n=19..28 (number of `(k,l)` blocks and the dimension of each). | β matches within exact tolerance AND the largest **reduced** block stays within the ~26–30 kernel-verified ceiling. **RED if reduced blocks are O(n²)** (e.g. the (0,0) block ≈ (n+1)²) — then no-build unless a further factorization (LPS-2017 split-Terwilliger) shrinks them. |
| **GATE 1** (discovery only) | Are there ≥3 open cells whose *current* record is Schrijver-2005-or-earlier AND still `lb < ub`? | **Machine-scrape** the Brouwer table (do NOT trust remembered cells — see the provenance note below); attribute every (d∈{6,8,10,12}, n∈19..28) ub to its source paper (extend `docs/data/brouwer-snapshot-2026-07.json` provenance). | **≥3 such cells** (our evidence says ~0 outside the pre-SDP frontier). |
| **GATE 2** (discovery only) | Can the D6-fixed leg solve the headroom cells at THREE-POINT at all? | `run_numerical`/SDPA-GMP on A(27,12), A(28,12) with eq.(8) normalization + truncated-dual rescue. | At least one produces a **clean `optimal` float** ≥ lb. If three-point can't, quadruple (160×) can't. |
| **GATE 1′** (amplification track) | Does a small published GMS cell reproduce under our transcription? | Hand-build the quadruple β for **one** tiny cell (e.g. A(9,6) or A(10,6)) and float-solve; compare to the published/expected value. | Reproduces (validates the transcription before committing the full build). |

**Provenance note (why GATE 1 must be a machine scrape).** The witness panel's *remembered* open cells were
demonstrably unreliable, which is the whole argument for scripting the scrape: Gemini gave A(19,6)'s current ub
as Schrijver's 1280 (it is GMS's **1237**, and n=19 is outside our n≥20 snapshot); Deepseek and GLM proposed
A(20,8) and A(23,8) as open targets, but both are **exact/closed** in our snapshot (`lb=ub`=256 and 2048). Human
and LLM memory of the table is not a decider — only the scraped, source-attributed snapshot is.

**Deliverable**: `docs/results/terwilliger-gms-gate-spike-<date>.md` + the provenance-annotated snapshot. **GO/NO-GO**:
**GATE 0 gates everything** (both tracks); then DISCOVERY needs GATE 1 ∧ GATE 2, AMPLIFICATION needs GATE 1′. A
failed *discovery* gate does **not** kill the build — it re-points it at the amplification objective, which the
operator may still choose. A failed **GATE 0** does kill it (or forces the LPS-2017 split-Terwilliger detour).

## Phases 1–6 — the build (on GO; mirrors the D1 constant-weight ladder)

Every phase reuses the proven, **structure-agnostic** downstream legs unchanged; only the β/block front-end is new.

**Phase 1 — quadruple-β / block oracle (M, 2–3 d; reuse *gated by GATE 0*).** Adapt the D1 `(k,l)` doubly-indexed
machinery — `scripts/terwilliger_cwc_beta.py::block_pairs`, `block_idx(w,v,k,l)`, `r_block(w,v,k,l,…)` — to the
**Hamming-scheme** GMS quadruple β (see the Johnson≠Hamming caveat above; the reuse is structural pattern, not a
drop-in — GATE 0 confirms the actual formula/multiplicities first). **Exit test**: a real-code PSD differential
test + a corrupt-control (the D1/Phase-0 pattern), and a checked-in β oracle TSV. **Risk**: product-β magnitudes
≈ β² (~90-bit numerators) — carry exact integers, never floats, in the oracle.

**Phase 2 — SDP builder (M, 2–3 d).** New `(k,l)` primal builder over the quadruple variables, SDPA-GMP solve
(reuse `terwilliger_sdp.py`'s eq.(8) normalization + `_solver_defaults`). **Exit test**: solves the Phase-0
tiny cell to the expected float. **Risk (WALL 1)**: SDPA-GMP convergence on ~40k-multiplier, β²-conditioned
blocks is unproven at n≥22 — bound n in early phases; escalate precision P and normalization empirically.

**Phase 3 — Table faithfulness gate (S, 1 d).** Reproduce a *published* GMS cell exactly at float tier —
**A(20,8)=256** is the cleanest anchor (GMS proved it optimal). **Exit test**: `sdp_floor == 256`. This is the
GMS analogue of the three-point (19,6)/(20,8) and constant-weight Table II gates — **the go/no-go for the whole
transcription**. RED here = stop and debug the β/block, do not proceed.

**Phase 4 — exact-LP + dual_check (S, 1–2 d; FULL reuse).** Feed the SDPA dual through the **unchanged**
`certify_lp`/`exact_simplex` (`scripts/terwilliger_exact_lp.py`) and `dual_check` (the decider). **Exit test**: an
exact-rational certificate whose floor hits the target on the Phase-3 cell. **Risk**: exact-LP active-set size
is projected ~3–5× three-point (unmeasured) — measure it here; if the full tableau walls at ~40k multipliers,
the Bareiss/integer-simplex path is the fallback. **Panel advice + a known tension (review response):** all six
reviewers prescribe the iterative active-set route — float-solve → freeze the numerically-active constraints →
solve the *small square* rational system on them → verify stationarity/nonneg/PSD/bound → enlarge on violation
(a rational cutting-plane). This is NOT what `certify_lp` does today: it deliberately uses **all** non-ν columns
because static active-set *restriction* caused spurious infeasibility (the εI strict-PD margin needs the full
column set to absorb the perturbation). The *iterative* variant (enlarge-until-feasible, not restrict-once) is
the reconciliation and is worth prototyping here before assuming the fallback — but it must respect the εI
design, so treat it as a measured Phase-4 experiment, not a settled swap.

**Phase 5 — kernel render (M, 3–5 d).** Extend F1's per-k-slice chunking (`scripts/terwilliger_kernel_full.py::
render`/`build_data`) to **per-`(k,l)`** chunking. **Exit test**: a small-cell whole-quadruple-cert verifies on
the real Lean 4.31 kernel, with corrupted controls rejected (incl. the F1-review controls: scale>0, β-shape,
kernel-side Σγ fold). **Risk (WALL 2)**: quadruple cert source ≈1 MB (~220 stationarity theorems, two binomial
sums per product-β entry) — 6× the largest source the kernel has accepted; per-(k,l) chunking + heartbeat/budget
tuning is mandatory and unproven at this size. De-risk by rendering ONE `(k,l)` slice first (the Phase-0-of-F1
benchmark analogue). **M0 engine lemma (review response):** the `fromBlocks` PSD-iff lemma our first Aristotle
attempt failed to close (`terwilliger_f2b_aristotle.py`) is **hand-closeable in ~30 min** by reusing the F2a
`gram_pairing_nonneg` pattern (`scripts/terwilliger_f2a.py`) — unfold `PosSemidef` to the quadratic form,
`Sum.elim`-split the vector, `mulVec` of `fromBlocks A 0 0 D` factors to `(A.mulVec a, D.mulVec b)`, and the dot
product splits to a sum of two nonnegative terms (four reviewers gave this identical sketch). Do NOT block Phase
5 on the automated prover; and keep the weak-duality/render path quantifying over a block *family*
(`∀ b, PosSemidef (Z b)`, as F1/F2a already do) rather than constructing a monolithic `blockDiag`.

**Phase 6 — target run (M, 2–3 d).**
- **DISCOVERY**: reach probe on the GATE-1 cells (ticket-① snapshot protocol). GREEN(candidate) = stop and
  surface to operator before any announcement.
- **AMPLIFICATION**: certify + kernel-attest the published GMS records; bank each as a `DUAL_CERTIFICATE_CHECKED`
  cert (the A(19,6)/A(23,6)/A(25,10) pattern). Deliverable is the kernel-attested record set.

## Trust invariants (every phase)

Audit tier only. The new front-end proposes; `dual_check` (exact rational) + the Lean kernel decide. **No edit
to `leibniz/trust.py`, `leibniz/verifiers.py`, or `tests/test_invariants.py`** (must stay byte-identical).
Operator-local deps (cvxpy/sdpap/docker) `find_spec`-gated so CI skips clean. Process: branch
`terwilliger-gms-<phase>` → PR to main → CI (invariants lane) → operator merges. Each phase = its own PR with a
results doc + gated test; **give Phases 3 and 5 the 8-angle adversarial review** (the D2/#238 precedent — the
kernel-render and faithfulness seams are where soundness holes hide).

## Risk register (the D3 walls + witness-panel additions, with mitigations)

0. **Hamming quadruple block size (NEW #1 per the panel; decisive for BOTH tracks).** If the *reduced* GMS
   blocks are O(n²) rather than O(n), the largest block blows past the ~26–30 kernel ceiling and the build is
   dead (or needs the LPS-2017 split-Terwilliger detour). Our D1 Johnson evidence says O(n), but Johnson≠Hamming.
   Mitigation: **GATE 0 measures this first, at $0 CPU, before any solver or Lean work.** This is the highest-
   leverage gate in the plan.
1. **Exact-solver conditioning (decisive, discovery track).** The unmined cells are unsolvable at three-point
   today. Mitigation: GATE 2 is exactly this test — fail fast before Phase 1. No mitigation known if GATE 2 fails.
2. **Kernel elaborator recursion (~1 MB).** Per-(k,l) chunking (Phase 5); de-risk with a one-slice benchmark.
   The panel's added warning: it is *term reduction* (the `decide` on product-β sums), not source size, that
   kills — prefer offline-generated integer literals over inlining two binomial sums per entry into every theorem.
3. **SDPA-GMP on β² conditioning.** Bound n early; empirical precision/normalization tuning (Phase 2). The panel
   adds per-block diagonal preconditioning (a congruence, tracked back through the dual) on top of eq.(8).
4. **Exact-LP active-set growth.** Measure in Phase 4; the *iterative* active-set (respecting the εI margin) is
   the panel's mitigation; Bareiss/integer-simplex is the fallback.
5. **Effort overrun.** 10–15 person-days is the estimate; the measure-before-build gates cap the downside — any
   phase RED stops the spend.

## Strategic alternatives on record (not adopted)

- **Amplification lands at audit/Observatory tier, by our own trust model.** Re-deriving a table bound is *not
  novel* (invariant 4 — novelty settled by retrieval + decision), so a GMS reproduction is a real
  verification-amplification win but a `DUAL_CERTIFICATE_CHECKED`/Observatory result (ADR 0046), not a
  promulgated law. The panel (Qwen) is right to name this; it is consistent with our decided tier, not a
  surprise — but the plan should not oversell amplification as more than that.
- **Horizontal infrastructure (Kimi's fork).** Instead of a bespoke quadruple renderer, build a *generic*
  algebraically-structured-SDP certificate-ingestion pipeline that any Terwilliger-class bound could feed. Larger
  scope, more reusable, does not chase the (near-zero) discovery EV. Recorded as an operator fork, not adopted
  here — the GMS build is the narrower, better-scoped first step and would inform such a generalization.

## Effort & sequencing

**Phase 0: 1–2 days** (GATE 0 is hours of CPU and runs first). **Phases 1–6: ~10–15 person-days / 4–6 weeks** on
GO. Phases 1→2→3 are the critical path (faithfulness gate); 4→5 reuse proven legs; 6 is the payoff. Kill points,
in order: **GATE 0 (block size — the cheapest and most likely RED)**, GATE 2 (discovery solvability), Phase 3
(faithfulness), Phase 5 one-slice benchmark (kernel). External-review brief for this plan:
`docs/briefs/terwilliger-gms2012-external-review-brief-2026-07-02.md`; the witness panel that produced these
revisions: `docs/results/terwilliger-gms-witness-review-2026-07-02.md`.

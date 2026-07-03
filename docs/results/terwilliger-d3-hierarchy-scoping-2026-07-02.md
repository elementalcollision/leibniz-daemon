<!--
Discovery pivot D3 (task #104) — scoping the post-2005 SDP hierarchies. DOCS-ONLY go/no-go, no build.
Grounded in this repo's own measured results (reach probe, D6 solve-leg, F1 kernel, D1 constant-weight);
literature via a 3-agent research sweep. No trust surface touched; tests/test_invariants.py byte-identical.
-->

# D3 — post-2005 hierarchy scoping: is a stronger producer worth building? (2026-07-02)

**Recommendation: SCOPE-MORE — a 1–2 day two-gate de-risking spike, then decide. Not a blind build, not a halt.**

D1 and D2 established that the base Schrijver-2005 three-point family is **mined out** (unrestricted reach probe
DRY 0/44; constant-weight probe DRY, 179/179 reproduction-complete). D3 asks whether the **post-2005
hierarchies — where the current binary records actually come from — are worth building** as a stronger producer.

## The candidate formulations, ranked

| # | Formulation | Size delta vs three-point | Records it could NEWLY reach (vs current Brouwer table) | Build cost (no trust edit) | Risk |
|---|---|---|---|---|---|
| **1** | **GMS 2012** quadruple-distance SDP (four-point, product-β blocks) | ~150–200 block families vs 13 at n=26 (~160× more PSD entries); ~40k multipliers vs ~9.8k; product-β magnitudes ≈ β² → ~90-bit numerators. Largest block barely grows (27×27 vs 26×26) — **count and coupling explode, not block size**. | **Near-zero.** GMS's own wins (A(19,6)→1237, A(23,6)→13674, A(22,10)→84, A(25,10)→466, A(20,8)=256) are **already in Brouwer 2026** → a producer re-derives *published* values at higher trust tier (verification-amplification, not discovery). Only genuine headroom: the pre-SDP AVZ-2001 cells **A(27,12)≤169, A(28,12)≤288** that GMS never computed. | ~4–6 wks / 10–15 person-days. Downstream legs (`certify_lp`/`exact_simplex`, `_round_psd`, LDLT/kernel render) are **structure-agnostic and reused unchanged**. | **HIGH** |
| 2 | **LPS 2017** nonbinary q-ary quadruples | ~GMS after orbit reduction + a q≥3 alphabet dimension | Off the binary A(n,d) mission — opens a *new domain*; no binary discovery | GMS + q-ary layer + a **new nonbinary oracle** (unbuilt) → 6–8 wks | MED-HIGH |
| 3 | **Split-Terwilliger 2023** (m-component partition) | Intermediate — smaller blocks, cross-component constraints; lighter per cell than GMS | Marginal — published gain is a **single point** A(18,4) 6552→6551, in a d=4 family our sweep excludes by design | ~2–3 wks | MED (low yield) |
| 4 | **Laurent 2007** next level (Lasserre-style) | **Catastrophic** — O(n⁷) vars vs Schrijver's O(n³); moment-matrix blowup | Theoretically tightest, but **out of reach for practical n** by the paper's own account | Not buildable on our stack (>100× every measured ceiling) | **PROHIBITIVE / NO-GO** |

GMS 2012 is unambiguously the **right** formulation: it is where current binary records come from, its product-β
block structure (`β^{t,w}_{i,j,k}·β^{s,v}_{i,j,l}`) is the **same object already shipping in the D1
constant-weight build**, and no trusted surface changes. Feasibility is not the question — **discovery EV is**.

## The five walls (most decisive first)

1. **Exact-solver conditioning wall — the decisive one.** The only cells with headroom over the current table
   are A(27,12) and A(28,12). The reach probe *measured* that these are exactly where **neither CLARABEL nor
   SCS produces a usable float today at three-point size** (CLARABEL crash onset ≈4,600 free vars at (23,6); SCS
   up to ~88× below the lower bound). The quadruple SDP is ~160× larger with ≈β² conditioning. **Anti-correlation:
   where GMS can solve, it cannot discover (already published); where it could discover, it cannot solve.**
2. **Kernel elaborator recursion wall (all quadruple-class).** F1's whole-cert-in-kernel already hit the Lean
   elaborator recursion limit at n=19 (12,155 β entries, 219 KiB) and needed per-k-slice chunking. A quadruple
   cert is ~5–6× the source (~1 MB, two binomial sums per product-β entry, ~220 stationarity theorems vs 55);
   per-(k,l) chunking + heartbeat tuning is mandatory and unproven at ~1 MB (6× the largest source accepted so far).
3. **LPS nonbinary — missing oracle.** No q-ary table oracle exists; novelty could not be settled by
   retrieval+decision (trust invariant 4) until a DOI-pinned q-ary oracle is built and validated. q-ary
   faithfulness is entirely unvalidated.
4. **Split-Terwilliger — discovery yield, not engineering.** Its one published win is d=4, a family the sweep
   excludes; no measured even-d record. Building it risks a DRY identical to three-point.
5. **Laurent level-2 — prohibitive by construction.** O(n⁷) exceeds the exact-LP ceiling (~12k multipliers) and
   the kernel by >100×; not renderable or solvable at any n of interest.

## The measure-before-build spike (the actual next action, ~1–2 days, zero code)

Two gates that together decide GO/NO-GO on GMS — mirroring the project's own D0/B0/FunSearch stop-rule discipline,
where every producer-strength swing that skipped the gate came back RED:

- **GATE 1 (provenance).** Re-fetch the Brouwer binary snapshot; for every open cell (d ∈ {6,8,10,12}, n ∈ 19..28)
  attribute the current-ub source. Count cells whose record is **Schrijver-2005-or-earlier AND still has lb < ub**.
  Our evidence says this set is ~empty except the pre-SDP frontier. **GO needs ≥ 3 such cells.**
- **GATE 2 (solvability).** For A(27,12) and A(28,12), attempt the **three-point** solve with the D6-fixed leg
  (eq.(8) normalization + SDPA-GMP + truncated-dual rescue). If three-point cannot produce a clean `optimal`
  float at these two cells, the 160×-larger quadruple certainly cannot → **NO-GO on the discovery surface.**

**GO only if BOTH pass.** Then enter GMS via the proven D1-style ladder: product-β oracle → Table faithfulness
at a small cell (e.g. A(20,8)) → exact + kernel legs → reach probe. Otherwise the honest outcome is that GMS is a
**verification-amplification** asset (re-derive published records at kernel tier), not a discovery engine — an
operator call worth making explicitly, not by building 4–6 weeks blind.

## Confidence

**High-confidence (verified against this codebase; do not re-measure):** three-point mined out (both probes DRY);
GMS's binary wins already in Brouwer 2026 (the anomaly doc certifies the *superseded* three-point 87 while Brouwer
shows GMS's 84); the headroom cells A(27,12)/A(28,12) are unsolvable today; product-β structure is real and in
production (D1 GREEN through Table II); the kernel recursion wall is real (F1 chunking); downstream legs are
structure-agnostic. **Needs the spike (gates the decision):** the exact provenance count (never enumerated
cell-by-cell); whether the D6 leg solves A(27,12)/A(28,12) at three-point at all; and — only if build proceeds —
SDPA-GMP convergence on product-β blocks, exact-LP active-set growth, and ~1 MB chunked kernel elaboration.

## Recommendation to the operator

**SCOPE-MORE via the 1–2 day two-gate spike.** GMS is the right target and cheaply de-risked; committing 4–6 weeks
blind is negative-EV because the reachable cells are already published and the unmined cells sit behind the
pipeline's existing binding constraint at 160× scale. If the operator's goal is **verification amplification**
(kernel-tier re-derivation of the current records), GMS is a GO on that basis alone — a distinct, legitimate
objective that does not depend on either gate. That framing choice is the real decision D3 surfaces.

Research provenance: 3-agent literature+capacity sweep (GMS 2012 arXiv:1005.4959; Laurent 2007 Math. Prog. B 109;
LPS 2017 DCC 84; Tseng-Lai-Yu 2023 DCC 91) cross-checked against `docs/results/terwilliger-{reach-probe,
solve-leg,f1,anomaly}-*.md` and the D1 constant-weight build. No build; no trust surface touched.

<!--
External-agent brief: review + help tackle the GMS 2012 quadruple-distance build (the Phase-0 spike and the
4-6 week build). Self-contained — paste into an Aristotle project description, a Mathlib-Zulip thread, an
email to the review panel, or a fresh Leibniz session. Transmission is the operator's action.
Companion plan: docs/plans/terwilliger-gms2012-build-plan-2026-07-02.md.
-->

# Brief — help build/verify the GMS 2012 quadruple-distance code-bound producer

## Who is asking, and what exists

The **Leibniz** theorem-daemon produces **machine-verified** upper bounds on binary code sizes A(n,d): LLMs and
SDP solvers only *propose*; only the Lean 4.31 kernel and an exact-rational decision procedure *decide*. The
pipeline: solve an SDP (SDPA-GMP, high precision) → rationalize its dual → exact two-phase simplex finds the
nonnegative multipliers → `dual_check` (exact) certifies the bound → the Lean kernel re-verifies the PSD blocks
(per-block integer LDLT theorems). **Already built, measured, kernel-attested**: the full Schrijver-2005
**three-point** (Terwilliger) SDP — reproduces Table I exactly incl. A(19,6)≤1280, A(23,6)≤13766, A(25,10)≤503;
a constant-weight (Johnson-scheme) variant with the **doubly-indexed `(k,l)` product-block machinery already in
production**; the whole certificate (β vs eq.(7), stationarity, nonneg, bound, PSD) checked *inside the kernel*
(F1); and weak duality formalized in Lean/Mathlib (F2a). Trust boundary held byte-identical throughout.

## The decision we have taken

We measured that the base three-point family is **mined out** and that GMS 2012 (quadruple-distance) is the
**most plausible stronger** formulation — a *hypothesis* until our Phase-0 gates confirm it, not a settled fact.
We *suspect* GMS's product-β blocks `β^{t,w}_{i,j,k}·β^{s,v}_{i,j,l}` overlap with our constant-weight build's
`(k,l)` machinery — **please attack that claim**: our build is the *Johnson-scheme* (constant-weight) quadruple,
while GMS is the *Hamming-scheme* (unrestricted binary) quadruple (reduction group S_n vs S_w×S_v), so identify
any missing multiplicities, normalizations, orbit constraints, or block-size differences. We are committing to
**build toward GMS**, front-gated by a cheap GO/NO-GO spike. Two objectives share the build and differ only at
the ends: **DISCOVERY** (tighten a current record — high-risk, gated) vs **VERIFICATION-AMPLIFICATION**
(kernel-tier re-derivation of GMS's *published* records — a real win, but note it lands at our **audit/
Observatory tier**: re-deriving a table bound is not *novel* by our own decision procedure, so it is a
verification result, not a promulgated law). Full plan attached.

## What we ask of you

**(A) Review the Phase-0 spike design.** Is the two-gate decider right and minimal?
- GATE 1 (provenance): are there ≥3 open cells (d∈{6,8,10,12}, n∈19..28) whose *current* best-known ub is
  attributed to Schrijver-2005-or-earlier AND still `lb<ub`? Do you know of such cells we may have missed?
- GATE 2 (solvability): the only cells with headroom over the current table are the pre-SDP AVZ-2001 cells
  **A(27,12)≤169** and **A(28,12)≤288**, which GMS never computed. Is there a known reason the quadruple (or even
  three-point) SDP is or isn't solvable there at high precision?

**(B) Help tackle the four measured WALLS** (these gate the 4–6 week build; concrete help here is the highest
value):
1. **Block-diagonalization of the quadruple Terwilliger algebra — and the decisive block-size question.** We want
   the explicit `(k,l)`-indexed block reduction (the analogue of Schrijver's Propositions 2–5 for four-point):
   a clean, citation-backed statement of the quadruple β / change-of-basis we can transcribe and kernel-verify.
   **Critically: what is the dimension of the largest *reduced* PSD block as a function of n — O(n) or O(n²)?**
   Our Johnson-scheme build's reduced blocks are O(n) (single-index range, kernel-verified at 26×26), but we
   have not confirmed the Hamming quadruple reduces the same way; if the reduced blocks are O(n²) they exceed
   our ~26–30 kernel ceiling and we would need the LPS-2017 split-Terwilliger reduction. This is our #1 gate.
2. **SDPA-GMP conditioning** on ~40k-multiplier, β²-conditioned blocks at n≥22 — known precision/normalization
   recipes beyond Schrijver's eq.(8)?
3. **Exact-rational LP active-set growth** — projected 3–5× the three-point tableau (~12k multipliers today);
   integer-preserving (Bareiss) simplex advice welcome.
4. **Kernel elaboration of a ~1 MB certificate** (~220 stationarity theorems, two binomial sums per product-β
   entry) — 6× the largest source our Lean 4.31 kernel has accepted; we plan per-`(k,l)` chunking. For a Lean/
   Mathlib formalizer or an automated prover (Aristotle): can you close the **self-contained engine lemma**
   `(Matrix.fromBlocks A 0 0 D).PosSemidef ↔ A.PosSemidef ∧ D.PosSemidef` (Mathlib lacks it; our first automated
   attempt returned no proof), and its n-block generalization? That lemma is the reusable core of the kernel
   render.

**(C) Sanity-check the go/no-go economics.** We assess GMS's *discovery* EV as near-zero — its wins are already
the current best-known records (most in the Brouwer n=20..28 snapshot; the rest, e.g. A(19,6)≤1237, established
at n<20) — but its *amplification* value as real. Do you agree, and is there a cell or a method-gap we are
mis-attributing?

## Ground truth you can build against

- β oracle + validated conventions: `docs/results/terwilliger_beta_oracle.tsv`, the `(k,l)` machinery in
  `scripts/terwilliger_cwc_beta.py` (`block_pairs`, `r_block`), and the reused exact/kernel legs
  (`terwilliger_exact_lp.py::certify_lp`, `terwilliger_cert.py::{extract_dual,cert_psd_blocks,render_cert_lean}`).
- Measured ceilings: `docs/results/terwilliger-{solve-leg,f1,anomaly}-2026-07-02.md` and the D3 scoping doc
  `docs/results/terwilliger-d3-hierarchy-scoping-2026-07-02.md` (walls, size estimates).
- Payoff: three kernel-attested three-point certificates await nothing; the GMS build would add the quadruple
  records at the same trust tier.

References: Gijswijt–Mittelmann–Schrijver 2012 (IEEE IT 58, 2697; arXiv:1005.4959); Schrijver 2005 (IEEE IT 51,
2859); Laurent 2007 (Math. Prog. B 109, 239); Litjens–Polak–Schrijver 2017 (DCC 84, 87).

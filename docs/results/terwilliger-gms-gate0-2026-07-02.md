<!--
GATE 0 result — the front kill gate of the GMS 2012 quadruple-distance build
(docs/plans/terwilliger-gms2012-build-plan-2026-07-02.md). Read from the actual paper (arXiv:1005.4959),
not reviewer memory. Docs/measurement only; no trust surface touched; tests/test_invariants.py byte-identical.
-->

# GATE 0 — GMS Hamming quadruple block size: **RED**

**Verdict: RED. The GMS 2012 quadruple SDP's reduced PSD blocks are O(n²) — order 130–414 (S₂-halved 66–207)
for n=19..28 — versus our ~26–30 native-kernel integer-LDLT ceiling. The plan's per-block kernel-certification
path is unreachable on every in-range target cell. This kills the GMS build as written before any solver or
Lean work.**

This is the gate doing exactly its job: a $0-CPU, paper-grounded probe that catches the build-killer the
external witness panel split on — and it settles that split authoritatively.

## The finding, from the actual paper (arXiv:1005.4959 §4)

The single-word algebra block-diagonalizes to `k=0..⌊n/2⌋` blocks of dimension `(n−2k+1)` (eq. 12) — the
familiar three-point O(n) structure. The **quadruple** blocks (M_S(x), S of size ≤ 2) are different: the image
is *"the direct sum over k,l of the linear hull of the submatrices of `Γ_{α,k} ⊗ Γ_{β,l}` induced by the rows
and columns indexed by `(i,i')` with `i+i' ∈ [d,n]`"* (and an m-dependent constraint; a further S₂ action
splits each block sym/antisym, ~halving). **The rows/columns are indexed by PAIRS `(i,i')`** — a two-parameter
index — so the block order is O(n²), not O(n).

| n | d=6 largest (halved) | d=8 | d=10 | d=12 | three-point | kernel ceiling |
|---|---|---|---|---|---|---|
| 19 | 189 (95) | 174 (87) | 155 (78) | 132 (66) | ~20 | ~30 |
| 24 | 304 (152) | 289 (145) | 270 (135) | 247 (124) | ~25 | ~30 |
| 28 | 414 (207) | 399 (200) | 380 (190) | 357 (179) | ~29 | ~30 |

Even S₂-halved, the largest block is **66–207** across the target range — **2–7× past the kernel ceiling**, and
growing quadratically. No in-range target cell fits; only tiny faithfulness cells do (A(9,6)→halved ~17,
A(10,6)→~22, but A(12,6)→~35 already exceeds), and those correspond to no interesting published record.

## Why this refutes the earlier examination — Johnson ≠ Hamming, decisively

The review-response plan flagged Johnson≠Hamming as the load-bearing risk and my examination *guessed the
favorable side* (O(n), from the D1 constant-weight analogy). **GATE 0 shows that guess was wrong for the
Hamming case.** In the constant-weight (Johnson) build (D1, `terwilliger_cwc_beta.py`), fixed weight `w` links
`i` and `i'` into a single running index → O(n) blocks (`block_idx` returns one range; kernel-verified 26×26).
In the **unrestricted (Hamming)** case there is no fixed weight, so `i` and `i'` are independent → pair-indexed
O(n²) blocks. The witness reviewers who called O(n²) (Fugu's (n+1)², Kimi, Qwen) were **right for Hamming**;
Deepseek/GLM (and my examination) were right only for the Johnson case they were implicitly reasoning from.

## Independent corroboration (the paper's own compute cost)

GMS report their SDP solves ran *"from a few hours for the small cases to 1½ days for A₄(20,4), **13 days for
A₄(23,6)**"* and that *"standard double precision … was insufficient."* Thirteen days of high-precision SDPA for
one cell is exactly the signature of an O(n²)-block, O(n⁴)-variable program — consistent with these block sizes
and independent of our reading. The SDP is *float-solvable* (GMS did it); what is unreachable is the **exact
kernel LDLT certification** of order-hundreds PSD blocks, which is the entire basis of Leibniz's trust model.

## Scope / honesty

The block dimensions are a **dominant-count scoping estimate** — `#{(i,i') : k≤i≤n−k, l≤i'≤n−l, d≤i+i'≤n}`
(`scripts/terwilliger_gms_gate0.py`, CI-safe, `tests/test_terwilliger_gms_gate0.py`). The exact reduced orders
depend on the m-constraint and the S₂ split (applied here as a halving). But the **order (O(n², hundreds) and
the RED verdict are robust** to those refinements — even a further 2× reduction leaves the target-cell blocks
at 33–104, still 1.1–3.5× past the ceiling and quadratically growing. A definitive per-cell block order would
come from actually building the reduced blocks (a Phase-1 task) — but a kill gate does not need that: hundreds
vs 30 is unambiguous.

## Recommendation to the operator: **NO-GO on the GMS build as planned**

The kernel-certification path — what makes a Leibniz bound kernel-attested rather than solver-trusted — cannot
verify the quadruple blocks with the current native integer-LDLT checker, at any in-range target cell. Float-only
GMS reproduction adds nothing over GMS's published numbers, so there is no product without the kernel path.

Routes, in the operator's court (none is a quick win):
1. **LPS-2017 split-Terwilliger** — exploits more symmetry to shrink blocks. But we need a 2–7× reduction to
   reach ≤30, which split-Terwilliger is not known to deliver for these cells (Qwen flagged the same doubt); this
   is itself a fresh formulation build with its own GATE 0.
2. **A new large-block kernel-PSD-certification primitive** — verify order-hundreds PSD blocks without per-entry
   LDLT `decide` (e.g. a kernel-checkable compressed factorization, verified interval/rational Schur complement).
   This is a substantial *trust-primitive research* project, not a producer build — but it would generalize
   beyond GMS (it is the real blocker for any large-block SDP the daemon might want to kernel-attest).
3. **Abandon the quadruple bound**; the three-point family is banked and mined out, and D3 already showed the
   discovery frontier is elsewhere.

The honest synthesis: **GATE 0 saved the 4–6 week (realistically far longer — cf. GMS's 13-day solves) build.**
The productive next bet, if any, is route 2 (the large-block kernel primitive) as a *separate, generalizable*
research item — not the bespoke quadruple renderer. This vindicates the measure-before-build discipline: the
cheapest gate returned the decision.

Harness: `scripts/terwilliger_gms_gate0.py` (`docs/results/terwilliger_gms_gate0.json`). Test:
`tests/test_terwilliger_gms_gate0.py`. Paper reading: arXiv:1005.4959 §3–4. Plan gated:
`docs/plans/terwilliger-gms2012-build-plan-2026-07-02.md` (GATE 0).

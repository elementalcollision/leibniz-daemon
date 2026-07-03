<!--
Archived external witness-panel review of the GMS 2012 build plan + brief (PR #244, f50592e), for provenance.
Six reviewers. Verbatim outputs preserved below the synthesis. The durable findings were folded into
docs/plans/terwilliger-gms2012-build-plan-2026-07-02.md and the external brief in this same review-response.
Audit/measurement only; no trust surface touched.
-->

# External witness review — GMS 2012 build plan (2026-07-02)

Six reviewers (**Fugu**, **Deepseek v4 Pro**, **Kimi**, **GLM 5.2**, **Gemini 3.5 Thinking**, **Qwen 3.7 Max**)
critiqued the GMS quadruple-distance build plan and external brief. Below: a synthesis with our critical
examination (claims cross-checked against our own code), then the verbatim panel.

## Synthesis — what survived examination

**Unanimous and correct:** this is a **verification-amplification** build, not a discovery bet — every reviewer
independently reached our D3 conclusion. Amplification lands at our audit/Observatory tier (Qwen's
novelty-invariant point aligns with ADR 0046).

**The decisive contested fact — GMS reduced block size, O(n) vs O(n²):** the panel split (Fugu/Kimi/Qwen:
O(n²), "dead on arrival"; Deepseek/GLM: O(n), many blocks), and several reviewers flagged their own numbers as
guessed. We resolved it against our own code: `terwilliger_cwc_beta.py::block_idx(w,v,k,l)` returns a
single-index **O(n)** range and D1 kernel-verified a 26×26 block — so the O(n²) alarm reasons about the
*unreduced* moment matrix, which the block-diagonalization exists precisely to avoid forming. **BUT** D1 is the
Johnson scheme and GMS is the Hamming scheme (S_n vs S_w×S_v) — so whether the Hamming quadruple *also* reduces
to O(n) is unconfirmed. **Resolution: this became GATE 0**, the front kill gate ($0 CPU, measured before any
solver/Lean work).

**High-reliability process advice we adopted:**
- GATE 0 (algebra + block-profile probe) first, ahead of provenance/solvability.
- Machine-scrape provenance — the panel's *remembered* cells were wrong (Gemini: A(19,6) ub = Schrijver 1280;
  it is GMS 1237 and outside our n≥20 snapshot. Deepseek/GLM proposed A(20,8)/A(23,8) — both exact/closed
  `lb=ub` in our snapshot). Human/LLM table memory is not a decider.
- Iterative active-set for the exact LP — with the caveat we verified: `certify_lp` deliberately uses all non-ν
  columns because static active-set *restriction* caused spurious infeasibility (the εI margin needs them); the
  *iterative* enlarge-until-feasible variant is the reconciliation, not a settled swap.
- M0 `fromBlocks` lemma is hand-closeable via our F2a `gram_pairing_nonneg` quadratic-form pattern — don't block
  on Aristotle. Keep weak duality quantifying over a block *family*, not a monolithic `blockDiag` (F1/F2a
  already do this).
- Per-block diagonal preconditioning on top of eq.(8); offline integer β literals rather than inlining binomial
  sums into every `decide`.

**Where the panel was wrong / low-reliability (verified):** the O(n²) block alarm (rebutted by our D1 code);
the remembered open cells (closed/mis-attributed in our snapshot); Qwen's "N=32 kernel wall" (we never stated
N=32; our verified ceiling is ~26); muddled record values across reviewers (reinforces the machine scrape).

**Strategic forks recorded (not adopted):** Kimi's generic SDP-certificate ingestion pipeline (horizontal infra
instead of a bespoke renderer); the amplification-only scope-down if GATE 0/GATE 2 are RED.

**Net:** the review does not kill the build — our own code rebuts the loudest alarm — but it materially sharpens
Phase 0 (GATE 0 first) and corrects two real overclaims (Johnson≠Hamming; amplification-tier). All folded into
the plan and brief in this review-response commit.

---

## Verbatim panel

> Source: `/Users/dave/Downloads/GMS 2012 for Leibniz.md` (operator-supplied). Reproduced for provenance; the
> reviewers' specific remembered facts (block sizes, record values, open cells) are **not** authoritative —
> see the synthesis above for what we verified. Formatting normalized; content unaltered.

*(The full six-reviewer text is retained in the operator's source file and summarized above. Key verbatim
positions by reviewer:)*

- **Fugu** — reframe soundness claim (arithmetic is kernel-protected, the GMS *bridge* is the object under
  review); add formulation/certificate/Lean-size gates before the spike; block-size warning `(n+1)²=841` at
  n=28 as "the most likely hidden build-killer"; EV table (discovery ~1–8%, amplification 40–65%).
- **Deepseek v4 Pro** — block size `n−k−l+1` (O(n)), many blocks; GMS §III / eqs (7)–(9) for the reduction;
  eq.(8) scaling; active-set square-system trick; `fromBlocks` proof sketch; automate the table scrape.
- **Kimi** — adversarial; "verification backfill not discovery"; 4-point algebra needs Racah/6j-symbols, "not a
  simple Kronecker product"; ranked $0 probes (table diff, algebra factorization at n=6, SDPA-GMP n=22 smoke,
  synthetic kernel load, LP sparsity); horizontal-infra alternative.
- **GLM 5.2** — block-diag *is* the Kronecker product (cites Laurent 2007 §3.2); spike A(20,8) not A(28,12);
  Frobenius-norm basis scaling; float→exact active-set; `fromBlocks` via quadratic form + `Sum.elim`.
- **Gemini 3.5 Thinking** — claims A(19,6)/A(23,6)/A(25,10) still Schrijver-2005 (mis-attributed — see synth);
  LPS 2017 for the change-of-basis (Hahn polynomials); 512–1024-bit precision; Bareiss GCD deflation;
  `blockDiag` sigma-type for the n-block generalization.
- **Qwen 3.7 Max** — "N=32 kernel wall fatal for 4-point" (block sizes O(n²), >100×100 at n=28); mandates
  LPS-2017 split-Terwilliger; float→rational-basis→sparse-LU for the LP; `posSemidef_fromBlocks_zero` via
  `.comp` congruence; argues amplification is quarantined non-novel (audit tier) — consistent with ADR 0046.

---

## Full verbatim review (operator source, preserved for provenance)

```markdown
# Fugu

\#\# Executive review

The brief is directionally sensible if the goal is \*\*verification-amplification\*\*: reproduce GMS 2012 bounds at kernel tier using an already-working Schrijver/Terwilliger certificate stack. It is much weaker as a \*\*discovery\*\* bet. Your own premise says the only plausible unexplored headroom is basically \`A(27,12)\` and \`A(28,12)\`, and even there you have no evidence that quadruple SDP improves the table.

The biggest architectural risk is not the Lean PSD checker. It is that a wrong GMS block reduction can produce a perfectly checked certificate for the wrong SDP. Your kernel protects the arithmetic of the certificate, not automatically the mathematical equivalence between the GMS relaxation and \`A(n,d)\` unless that bridge is formalized.

So I would revise the framing from:

\> “Soundness is already kernel-protected; experts only need correctness/reach.”

to:

\> “Arithmetic certificate soundness is kernel-protected; the GMS formulation/bridge is the object we need correct, because once transcribed it becomes the theorem being checked.”

\---

\# 1\. Phase-0 spike: current gates are not sufficient

Your two gates are useful but incomplete.

Current gates:

1\. provenance: find open cells whose current UB is old enough;  
2\. solvability: test \`A(27,12)\` / \`A(28,12)\`.

The missing gates are:

3\. \*\*formulation gate\*\*: can you reproduce one published GMS bound numerically with the proposed block reduction?  
4\. \*\*certificate gate\*\*: can you rationalize and exact-check one nontrivial GMS dual certificate, even before Lean rendering?  
5\. \*\*Lean-size gate\*\*: can Lean check a synthetic certificate with the projected block profile and bit lengths?

Without these, you can pass provenance and still fail on the actual hard parts.

\#\# Recommended Phase-0 gates

\#\#\# Gate 0 — formulation sanity

Before discovery cells, reproduce one published GMS bound numerically.

GREEN:

\`\`\`text  
Using the proposed quadruple block reduction, solve one small published GMS cell  
and match the published bound within numerical tolerance.  
\`\`\`

RED:

\`\`\`text  
Cannot reproduce any published GMS bound without ad hoc sign/scaling changes.  
\`\`\`

Reason: this catches wrong \`(k,l)\` indexing, normalization, orbit variables, and sign conventions before the 4–6 week build.

\---

\#\#\# Gate 1 — provenance / headroom

Your current Gate 1 is okay but should be stricter.

Require:

\`\`\`text  
machine-pinned current table snapshot;  
exact current UB/LB;  
attribution source;  
whether UB is from GMS, later LPS/split-Terwilliger, AVZ, LP, etc.;  
whether current UB is already known exact.  
\`\`\`

GREEN:

\`\`\`text  
≥3 cells in n∈19..28,d∈{6,8,10,12}  
with lb \< ub,  
current UB not already from GMS-or-later,  
and enough table provenance to make a record comparison deterministic.  
\`\`\`

RED:

\`\`\`text  
Only ambiguous attribution, or only A(27,12)/A(28,12).  
\`\`\`

If only two cells survive, discovery EV is low and should not justify a general build by itself.

\---

\#\#\# Gate 2 — numeric discovery probe

For \`A(27,12)\` and \`A(28,12)\`, run a numeric-only GMS solve before exact rationalization.

GREEN:

\`\`\`text  
GMS numerical dual gives T \< current\_UB  
with margin ≥ 0.5, preferably ≥ 1.0,  
and residuals stable under increased precision.  
\`\`\`

RED:

\`\`\`text  
No improvement, or improvement margin \< numerical/rationalization uncertainty.  
\`\`\`

If this is RED, discovery is dead; continue only as amplification.

\---

\#\#\# Gate 3 — exact certificate feasibility

Before Lean:

\`\`\`text  
rationalized dual \+ exact stationarity \+ nonnegative multipliers \+ PSD certificates  
\`\`\`

GREEN:

\`\`\`text  
Exact dual\_check closes one published GMS reproduction.  
\`\`\`

RED:

\`\`\`text  
float solution cannot be rationalized, active set explodes, or stationarity requires manual patches.  
\`\`\`

This is probably the real build-killer.

\---

\#\#\# Gate 4 — Lean rendering feasibility

Synthetic benchmark with projected certificate shape.

GREEN:

\`\`\`text  
Lean checks a synthetic per-(k,l) certificate with projected number of PSD blocks,  
stationarity identities, and comparable integer bit lengths within acceptable time.  
\`\`\`

RED:

\`\`\`text  
Lean elaboration/reduction fails before the actual GMS math is even present.  
\`\`\`

\---

\# 2\. Strongest case against this direction

The strongest case against the GMS build is:

\> GMS is not a discovery path; it is a high-complexity reimplementation of known SDP machinery whose published wins are already in the table, while the only unexplored cells are too few to justify the engineering risk.

The failure mode is predictable:

\`\`\`text  
4–6 weeks → reproduce some known GMS bounds → no table improvement → large brittle codepath  
\`\`\`

That may still be worthwhile as verification-amplification, but do not sell it as a discovery bet unless Gate 2 gives a numeric improvement on \`A(27,12)\` or \`A(28,12)\`.

My rough estimates:

| Outcome | Probability | Confidence |  
|---|---:|---|  
| Reproduce at least one published GMS bound numerically | 60–75% | medium |  
| Produce exact rational certificate for a published GMS bound | 35–60% | low/medium |  
| Lean-check full published GMS certificate | 30–50% | low |  
| Improve current Brouwer 2026 table on \`A(27,12)\`/\`A(28,12)\` | 1–8% | low |  
| Build becomes valuable verification-amplification infra | 40–65% | medium |

\---

\# 3\. Four walls: review and concrete advice

\#\# Wall 1 — quadruple block diagonalization

This is the highest-risk mathematical wall.

The brief says:

\> product-β blocks \`β^{t,w}\_{i,j,k} · β^{s,v}\_{i,j,l}\` are the same objects our constant-weight build already ships.

This may be true in your intended formulation, but it is exactly the point that needs external confirmation. The risk is that the GMS quadruple SDP is not just “Schrijver β tensor squared.” There may be:

\- orbit constraints over quadruple distances;  
\- stabilizer-dependent multiplicities;  
\- normalization factors;  
\- symmetrization over unordered triples/quadruples;  
\- parity/triangle constraints;  
\- block sizes larger than expected;  
\- equality constraints not present in the constant-weight implementation.

\#\#\# Mandatory validation

Do not trust the product-β formula until you have at least two independent checks:

1\. \*\*Small-n full ambient vs reduced comparison\*\*

For very small \`n\`, explicitly build the unreduced moment matrices and compare spectra/ranks/traces against the block-reduced form.

GREEN:

\`\`\`text  
For random rational variables satisfying orbit constraints,  
ambient PSD matrix block-diagonalizes to the proposed reduced blocks  
with matching characteristic traces/eigenvalue multiplicities.  
\`\`\`

2\. \*\*Published GMS reproduction\*\*

Match one published GMS numerical bound using only the proposed reduction.

Without these, a wrong reduction can pass your exact checker because the checker only verifies the wrong reduced SDP.

\#\#\# Block-size warning

You need to explicitly compute the largest PSD block dimension in GMS.

In Schrijver 2005, largest block is \`n+1\`.

In GMS quadruple-distance, if the \`(k,l)\` product block has dimension roughly:

\`\`\`text  
(n-2k+1) \* (n-2l+1)  
\`\`\`

then the largest block at \`(0,0)\` is \`(n+1)^2\`.

For \`n=28\`, that is:

\`\`\`text  
29^2 \= 841  
\`\`\`

which is completely outside your current Lean PSD wall.

Maybe the GMS reduction decomposes further, or maybe your constant-weight product machinery avoids forming that matrix. But this must be measured, not assumed.

Add a hard gate:

\`\`\`text  
Compute actual reduced block dimensions for target n.  
If any dense PSD block dimension exceeds the Lean/certificate plan,  
no-build unless a further block factorization or certificate compression exists.  
\`\`\`

This is the most likely hidden build-killer.

\---

\#\# Wall 2 — SDPA-GMP conditioning

Using high precision is correct. But I would not expect SCS/CLARABEL-style double precision to be adequate at GMS scale.

Recommendations:

1\. \*\*Solve in normalized basis, certify in integer basis\*\*

Use Schrijver/GMS normalization for numerical conditioning, then transform the rational dual back into the integer coefficient basis for certification.

Do not force the solver to see huge unnormalized β² coefficients if a congruent normalization exists.

2\. \*\*Scale constraints and objective\*\*

Normalize columns of the coefficient matrix / stationarity equations so dual multipliers are similar magnitude.

3\. \*\*Require precision ladder stability\*\*

For a target cell, solve at multiple precisions:

\`\`\`text  
100 digits → 150 → 200 → 300  
\`\`\`

GREEN:

\`\`\`text  
same objective to required margin,  
same active set mostly stable,  
PSD slack profile stable.  
\`\`\`

RED:

\`\`\`text  
objective or active set drifts materially with precision.  
\`\`\`

4\. \*\*Expect near-singular PSD blocks\*\*

At optimal SDP bounds, complementary slackness often puts dual blocks on low-rank faces. Strict-PD rounding may not be straightforward. You likely need exact feasibility reconstruction on the active face, not simply adding \`εI\`.

\---

\#\# Wall 3 — exact-rational LP active-set growth

Do not start by building a giant custom exact simplex unless forced.

Recommended order:

1\. Use SDPA-GMP to identify approximate dual solution and active constraints.  
2\. Freeze a candidate active set.  
3\. Solve the rational stationarity system exactly on that active set.  
4\. Check:  
   \- stationarity;  
   \- nonnegativity;  
   \- PSD certificates;  
   \- objective.  
5\. If violated, enlarge active set iteratively.

Use existing exact rational LP/MIP tools as baselines:

\- QSopt\_ex if applicable;  
\- SoPlex rational;  
\- exact rational simplex over sparse matrices;  
\- Sage/Pari for linear algebra prototypes.

Bareiss/fraction-free methods are appropriate, but sparse structure matters more than generic tableau cleverness.

Kill criterion:

\`\`\`text  
If exact active-set reconstruction for one published GMS cell produces multipliers  
with bit lengths or active set size \>10× three-point,  
pause before Lean work.  
\`\`\`

\---

\#\# Wall 4 — Lean elaboration of \~1 MB certificate

The largest risk is not merely source size; it is kernel reduction through generated arithmetic and matrix operations.

Recommendations:

\#\#\# Avoid recomputing β sums in Lean for every product entry

If you ask Lean to reduce thousands of binomial sums inside stationarity theorems, elaboration may dominate.

Prefer:

\`\`\`text  
offline exact generator computes integer coefficient literals;  
Lean checks integer identities over literals;  
separate small audited/tested β generator validates formula on regression cases.  
\`\`\`

If you need kernel-level β correctness, prove it in chunks and cache/reuse lemmas. Do not inline two binomial sums per product entry into every certificate theorem.

\#\#\# Chunk by independent obligations

Generate:

\`\`\`text  
\- one theorem per PSD block;  
\- one theorem per stationarity chunk;  
\- one final aggregation theorem;  
\`\`\`

Avoid one mega theorem.

\#\#\# Do not build a giant block diagonal matrix if avoidable

Your weak duality theorem should quantify over a list/family of PSD blocks directly:

\`\`\`lean  
∀ b, PosSemidef (Z b)  
\`\`\`

rather than constructing:

\`\`\`lean  
blockDiag Z₁ Z₂ ... Z\_m  
\`\`\`

and proving the whole thing PSD.

The direct formulation avoids needing the n-block block-diagonal lemma in the hot path.

\#\#\# About the block-diagonal PSD lemma

The two-block lemma is mathematically easy:

\`\`\`text  
blockDiag(A,D) PSD ↔ A PSD ∧ D PSD  
\`\`\`

Proof idea:

\- forward: embed a vector into the left or right summand with zeros elsewhere;  
\- reverse: split any vector into left/right components; quadratic form is sum of two nonnegative terms.

For Lean, use the quadratic-form characterization of \`Matrix.PosSemidef\` rather than fighting block matrix algebra if possible.

But I would not make this lemma the critical path unless needed. Better: avoid constructing block diagonal matrices in the certificate theorem.

\---

\# 4\. Economics: discovery vs amplification

I agree with your assessment:

\`\`\`text  
Discovery EV: near-zero unless numeric Gate 2 improves A(27,12) or A(28,12).  
Amplification EV: real, if exact certificates and Lean rendering are feasible.  
\`\`\`

The build should be approved as \*\*verification-amplification infrastructure\*\*, not as an autonomous-discovery bet.

A GMS reproduction would be valuable because it:

\- extends kernel-tier verification to a serious SDP hierarchy;  
\- validates the exact rational dual pipeline at larger scale;  
\- creates reusable machinery for future certificate architectures;  
\- demonstrates that known computational bounds can be independently rederived.

But it probably will not produce a new Brouwer-table upper bound.

Greenlight discovery spending only if:

\`\`\`text  
numeric GMS solve on A(27,12) or A(28,12) beats current UB  
with enough margin that exact rationalization plausibly survives.  
\`\`\`

Otherwise, bill it under amplification only, with a capped scope.

\---

\# 5\. Issues in the brief wording

\#\# “Trust boundary held byte-identical throughout”

This is a strong claim. If you mean the three-point path is fully kernel-attested, fine. But for GMS, the unformalized block reduction is not yet part of the checked bridge.

Suggested wording:

\> “The existing three-point path is kernel-attested. For GMS, the block-reduction formula is the object under review and must not be assumed trusted until reproduced/formalized.”

\#\# “GMS is the right stronger formulation”

This is plausible but should be phrased as a hypothesis unless Gate 2 shows live headroom.

Suggested wording:

\> “GMS is the most plausible stronger formulation for amplification, and the only currently identified route that might affect the two pre-SDP cells.”

\#\# “The same objects our constant-weight build already ships”

This may bias reviewers. Ask them to attack it.

Suggested wording:

\> “We suspect the product-β machinery overlaps with our constant-weight build; please identify any missing multiplicities, normalizations, or orbit constraints.”

\---

\# 6\. What I would add to the external brief

Add these explicit questions.

\#\#\# Q0 — block dimensions

\> For target \`n\`, what are the exact dimensions and multiplicities of every reduced PSD block in GMS? Is the largest block \`O(n)\`, \`O(n²)\`, or something else?

This is crucial for your Lean wall.

\#\#\# Q1 — smallest reproduction target

\> What is the smallest published GMS bound that is not already reproduced by Schrijver 2005 and has a documented numerical value suitable for regression?

You need a first target smaller than \`A(27,12)\`.

\#\#\# Q2 — normalization

\> What basis should be used for numerical solving, and what transform maps the dual certificate back to integer/rational coefficients?

\#\#\# Q3 — active-set reconstruction

\> Are published GMS computations known to have rationally reconstructible dual certificates, or are they numerical-only?

If the literature never needed exact duals, your task may be harder than reproduction.

\#\#\# Q4 — table attribution

\> For \`A(27,12)\` and \`A(28,12)\`, what is the current best UB source as of the table snapshot, and have later non-GMS methods improved them?

This determines whether discovery is even live.

\---

\# 7\. One likely wrong assumption

The likely wrong assumption is:

\> Because the constant-weight build already has \`(k,l)\` product-block machinery, the GMS quadruple SDP will fit the same certificate and Lean profile.

Maybe it will. But if the actual GMS PSD blocks are product-space blocks with dimension quadratic in \`n\`, or if multiplicities/stationarity constraints are substantially denser, then the existing machinery is only superficially similar.

This should be the first Phase-0 measurement:

\`\`\`text  
Generate the exact GMS block profile for n=19..28:  
  number of variables,  
  number of PSD blocks,  
  dimension of each block,  
  nonzero coefficient count,  
  projected certificate size.  
\`\`\`

If the largest dense block or stationarity size blows past your known Lean/exact-rational envelope, stop before solver work.

\---

\# 8\. Recommended go/no-go rule

I would use this decision rule.

\#\# GREEN for 4–6 week amplification build

All must pass:

\`\`\`text  
1\. Exact GMS block profile is within Lean/exact-rational envelope.  
2\. Numeric solver reproduces one published GMS bound.  
3\. Exact dual\_check closes that reproduction outside Lean.  
4\. Synthetic Lean certificate with projected size checks.  
\`\`\`

\#\# GREEN for discovery spending

Additionally:

\`\`\`text  
Numeric GMS improves current UB for A(27,12) or A(28,12)  
with margin ≥ 1 after conservative rounding allowance.  
\`\`\`

\#\# RED

Any of:

\`\`\`text  
\- block dimensions exceed feasible PSD cert size;  
\- no published GMS bound can be numerically reproduced;  
\- exact rational reconstruction fails on the smallest reproduction cell;  
\- current table already includes GMS-or-later bounds for all candidate cells;  
\- A(27,12)/A(28,12) numeric GMS does not improve current UB.  
\`\`\`

\---

\#\# Final recommendation

Proceed only as a gated verification-amplification spike: first compute the exact GMS block profile and numerically reproduce one published GMS bound; do not fund the full build or discovery swing unless exact dual reconstruction succeeds and \`A(27,12)\`/\`A(28,12)\` show a stable numerical improvement over the current table.

# Fugu Ultra

# Deepseek v4 Pro

\#\# Critical Review of the GMS 2012 Quadruple-Distance Build

This is an ambitious but logically coherent plan. The leap from three‑point to quadruple is non‑trivial, and the gate design is sensible. I will address each request concretely, flagging risks and offering practical advice. I assume the trust boundary is never at stake: the kernel remains the sole decider, and all advice here concerns the \*\*untrusted producer\*\* (SDP solves, certificate construction) except for the explicit Lean lemma.

\---

\#\#\# (A) Review of the Phase‑0 spike design

\#\#\#\# GATE 1 – provenance of open cells

The requirement “best‑known upper bound attributed to Schrijver‑2005‑or‑earlier and still \`lb \< ub\`” can be satisfied. The best source is \*\*Brouwer’s online table for A(n,d)\*\* (https://www.win.tue.nl/\~aeb/codes/binary-1.html). The table lists the reference for each upper bound. I recall, and you can verify, that for many parameters the best known is still Schrijver (2005) because the later GMS (2012) improvements were concentrated on specific d. Examples that likely satisfy the criterion:

\- \*\*A(23,8)\*\* – upper bound 13766 (Schrijver 2005), lower bound 13762 (via linear codes). Gap exists. GMS did not improve it.  
\- \*\*A(24,8)\*\* – was improved by GMS, so disregard.  
\- \*\*A(25,10)\*\* – Schrijver gives 503, GMS gives 503 (tie). Lower bound is 502; gap exists. The current table probably lists Schrijver as the source.  
\- \*\*A(21,10)\*\* – Schrijver 242, GMS 240? Need to check; GMS improved many d=10 entries. Consult the table.  
\- \*\*A(19,6)\*\* – Both Schrijver and GMS give 1280, lower bound 1280? Actually A(19,6) is likely optimal, lb=ub=1280, so not open. Not viable.  
\- \*\*A(22,8)\*\* – Schrijver 876, GMS 872? Again check.

I am not in front of the live table, but you can scrape it mechanically. The spike should \*\*script a scrape\*\* of Brouwer’s table (the raw HTML is parseable) and filter rows where \`upper\_ref \== 'Schrijver2005'\` (or earlier) and \`lb \< ub\`. That will give you a definitive count in minutes, removing guesswork.

\*\*Outcome:\*\* I am confident you will find at least three such cells. If you don’t, then the discovery track is dead on arrival anyway.

\#\#\#\# GATE 2 – solvability of A(27,12) and A(28,12)

The AVZ‑2001 bounds are from an LP (probably Delsarte). The three‑point SDP already tightens many AVZ bounds; GMS 2012 did not report these specific cells, likely because:  
\- The computational cost (variables, memory) for n=27,28 with quadruple was too high for their 2012 resources.  
\- Or they tested and got no improvement, so not worth publishing.

The \*\*three‑point SDP might already tighten them\*\* marginally; you could test that quickly with your existing three‑point pipeline. If the three‑point gives a bound equal to AVZ, then the quadruple might do better. The conditioning concern is real because the number of free variables \`x^{t,w}\_{i,j}\` grows roughly as \`binom(n+4,5)\` (five indices\!), making the SDP huge. For n=27, that’s tens of thousands of variables, blocks up to (14)²? Actually, the quadruple blocks are indexed by (k,l) with size \~(n‑2max(k,l)+1). Largest block still about 27+1=28, but there are \*\*many\*\* blocks (O(n²) blocks). The SDP will have many block‑PSD constraints, which SDPA-GMP can handle as a “block‑diagonal” structure, but the number of linear variables is the bottleneck.

\*\*My assessment:\*\* A(27,12) and (28,12) are high‑risk for a first spike; they may push the solver beyond reasonable time/memory. I would \*\*reserve them for later\*\* and for GATE 2 pick a smaller cell that is genuinely open and has a known gap, e.g., A(23,8) or A(25,10) (if they are indeed open). The spike can attempt to solve the quadruple SDP for that smaller cell; if it obtains a bound strictly better than the current best, GATE 2 passes. If not, then the quadruple might not add value for that cell, and you must search for another candidate.

\---

\#\#\# (B) Tackling the four measured WALLS

\#\#\#\# 1\. Block‑diagonalization of the quadruple Terwilliger algebra

The cleanest statement is in \*\*Gijswijt–Mittelmann–Schrijver (2012), Section III, particularly Theorem 2 and the surrounding text\*\*. The blocks are indexed by two integers \`(k,l)\` with \`0 ≤ k ≤ l ≤ n/2\`. For each such pair, there is a block \`B\_{k,l}(t,w)\` of size \`(n \- k \- l \+ 1\) × (n \- k \- l \+ 1)\`? Actually, I need to be precise: The block size is \`(n \- 2l \+ 1)\`? Wait, the indices i,j run from some range. The paper states:

\> For \`0 ≤ k ≤ l ≤ ⌊n/2⌋\`, the block \`𝒜\_{k,l}\` has dimension \`n \- k \- l \+ 1\` and its rows and columns are indexed by \`i,j ∈ {l, …, n-k}\`.

So the size is \`(n \- k \- l \+ 1)\`. The entries are sums of products of the \`β\` coefficients (from the three‑point) as:

\`\`\`  
(B\_{k,l}(t,w))\_{i,j} \= β^t\_{i,j,k} · β^w\_{i,j,l}   (with some normalisation? I think it's exactly the product)  
\`\`\`

But I recall the block is \`M\_{k,l} \= R\_k ⊗ R\_l\` restricted to a certain subspace. The paper gives an explicit formula in equations (7)–(9). The key is that the block for the quadruple is essentially the \*\*Kronecker product\*\* of two three‑point blocks, but then reduced to a smaller subspace (the symmetric/alternating part?). Actually, they split into symmetric and alternating parts, giving two families of blocks for each \`(k,l)\`. The constraint is that the whole block matrix must be PSD. So you have for each \`(k,l)\` a PSD block of size \`(n \- k \- l \+ 1)\`.

Your existing constant‑weight machinery with \`(k,l)\` pairs is directly reusable: you already compute \`β^{t}\_{i,j,k} \* β^{s}\_{i,j,l}\`. The quadruple adds a second index \`w\` because the variables become \`x^{t,w}\_{i,j}\`. The block entry for a given \`(k,l)\` and variable \`(t,w)\` is the product \`β^t\_{i,j,k} · β^w\_{i,j,l}\`. I am 90% confident this is correct, but \*\*verify against GMS’s Table I\*\* by computing a few entries for a small case (n=6,d=4) and comparing the SDP objective value with their published bound.

You asked for a citation-backed clean statement. I would directly quote from the arXiv version (1005.4959), page 6, “Block‑diagonalization” and the formulas that follow. That is the authoritative source. Transcribe those formulas into your β‑oracle and test.

\#\#\#\# 2\. SDPA‑GMP conditioning

The raw product‑β entries can vary by factors of \`binom(n, …)^2\`, causing severe ill‑conditioning. The GMS paper itself applies a scaling: \*\*they multiply each block by a factor \`γ\_{k,l}\`\*\* (equation (8) in the paper) involving inverse binomials to keep entries moderate. In the final integer certificate, those scalings are absorbed into the dual matrices. So you can adopt their scaling exactly: for SDPA-GMP, define scaled blocks \`B̃ \= γ · B\`, solve the SDP, then unscale the dual solution by multiplying the dual matrix by \`1/γ\`. This preserves exact rational feasibility if the scaling factor is rational (it is, as ratios of binomials). This is likely the normalization you already use, but quadruple exacerbates it.

I recommend:  
\- Use SDPA-GMP with \*\*1000‑digit precision\*\* (parameter \`prec=1000\`). It will be slow but reliable for the small blocks you need for a spike.  
\- For larger cases, you may need to switch to the \*\*high‑precision variant SDPA‑QD\*\* or use an iterative refinement in rational arithmetic. But that’s later.  
\- The dual solution from SDPA-GMP will be extremely accurate; your rounding step with strict‑PD εI should work if the rational distance to the optimum is modest.

\#\#\#\# 3\. Exact‑rational LP active‑set growth

The phase‑I LP that extracts non‑negative multipliers for the linear constraints (the \`λ\` and \`y\_1\` in the dual) is indeed the bottleneck. The number of dual variables grows combinatorially. However, you can \*\*pre‑solve\*\* an approximate dual using the float solution: run a float LP solver (like HiGHS) on the same system (with approximate rational numbers) to identify an active set, then use that active set as a warm start for the exact simplex, drastically reducing the tableau size. Since you only need \*one\* certificate, you don’t need to solve the full LP to optimality; you can fix many variables to zero and just certify feasibility. This is essentially a \*\*basis recovery\*\* approach.

Another trick: The dual of the SDP gives you \`Z\_k, W\_k\` directly; the remaining linear multipliers \`λ\` can be found by solving a \*\*linear system\*\* (not an LP) if all inequality constraints are either active with \`λ\>0\` or inactive \`λ=0\`. The exact LP is only needed to confirm non‑negativity. Often, the active constraints are exactly those where \`λ\` is strictly positive in the float solution. You can test that by solving a float LP first, then constructing an exact system with only those constraints active and solving the resultant linear equations exactly (via rational Gaussian elimination). If the solution satisfies all inequalities, you are done. That could reduce the problem to solving a square system rather than a full simplex.

\#\#\#\# 4\. Kernel elaboration and the \`fromBlocks\` lemma

The certificate size (\~1 MB) is within Lean’s capabilities if processed chunk‑wise. The key is that each block’s PSD proof is independent. You plan to use per‑\`(k,l)\` chunking, which is correct.

The lemma \`(Matrix.fromBlocks A 0 0 D).PosSemidef ↔ A.PosSemidef ∧ D.PosSemidef\` is \*\*provable\*\* and essential. The zero blocks mean the matrix is the direct sum of A and D. The standard proof:

\- For any vector \`v \= \[x; y\]\`, we have \`vᴴ M v \= xᴴ A x \+ yᴴ D y\`.  
\- Since \`xᴴ A x ≥ 0\` iff \`A\` is PSD, and similarly for \`D\`, the sum is nonnegative for all \`x,y\` iff both are PSD.

In Mathlib, \`PosSemidef\` is defined for a Hermitian matrix \`M\` via \`∀ v, dotProduct v (M.mulVec v) ≥ 0\` (or similar). The proof can be done using \`Matrix.posSemidef\_iff\_forall\` and \`Matrix.fromBlocks\_mulVec\`. I can sketch a Lean proof:

\`\`\`  
import Mathlib

lemma fromBlocks\_posSemidef {n₁ n₂ : Type \_} \[Fintype n₁\] \[Fintype n₂\]  
    (A : Matrix n₁ n₁ ℝ) (D : Matrix n₂ n₂ ℝ) (hA : A.IsHermitian) (hD : D.IsHermitian) :  
    (Matrix.fromBlocks A 0 0 D).PosSemidef ↔ A.PosSemidef ∧ D.PosSemidef := by  
  constructor  
  · intro h  
    have hApos : A.PosSemidef := by  
      intro x  
      \-- extend x to a vector on n₁⊕n₂ by zeros  
      ...  
    sorry  
  · intro ⟨hApos, hDpos⟩  
    \-- split vector  
    ...  
\`\`\`

But I’m not in a Lean environment. However, this is a straightforward property that any experienced Mathlib contributor can close in under 30 minutes. I suggest posting on the \*\*Mathlib Zulip\*\* with a request; the community is responsive.

The \*\*n‑block generalization\*\* follows by induction using the same lemma repeatedly, e.g., a block‑diagonal matrix with 4 blocks is two nested \`fromBlocks\`, and the lemma iterates.

\---

\#\#\# (C) Sanity‑check the go/no‑go economics

\*\*Discovery EV:\*\* I agree with your assessment. GMS 2012 already squeezed the quadruple method for all computationally feasible parameters. Their Table I is essentially the state of the art for small n. Any further improvement would require either a larger search (higher n, beyond current SDP capabilities) or a new idea (e.g., split Terwilliger, which Litjens–Polak–Schrijver explored). So finding a new record is unlikely. Even if you succeed, the bound improvement would be incremental and likely absorbed into Brouwer’s table soon after publication. The discovery EV is indeed near‑zero.

\*\*Amplification value:\*\* Real and significant. Having a \*\*kernel‑verified\*\* GMS bound is a stepping stone toward a fully verified table of code bounds. It proves that the SDP methodology is sound and can be trusted without reading the paper. That is a meaningful contribution to the formal‑mathematics ecosystem. Moreover, the same pipeline will be reusable for other SDP bounds (e.g., for covering codes, sphere packings). So the amplification track is the right focus.

However, I caution: even for amplification, you need a \*\*known correct bound\*\* to verify. You must ensure that you are not inadvertently verifying a wrong transcription of GMS. The safest approach is to use GMS’s own reported bounds as the target, but your pipeline will produce a certificate that implies a bound; you then compare that bound to the known one. If they match, trust is amplified. If they don’t match, you have found a bug in your implementation (or in GMS). That’s a win‑win. So the amplification build should target \*\*all GMS bounds\*\*, not just open cells. That gives a robust regression suite.

\---

\#\#\# Overall Recommendation

1\. Proceed with the Phase‑0 spike, but automate the table scraping for GATE 1\.  
2\. For GATE 2, pick a modest cell like A(23,8) or A(25,10) that is confirmed open. If the quadruple SDP produces an improved bound there, GATE 2 passes; if it only matches Schrijver, then GATE 2 fails and you can stop.  
3\. During the spike, implement the explicit block formulas directly from GMS’s Section III and verify against a known small case.  
4\. Use SDPA-GMP with scaling as per GMS (equation (8)), and try the active‑set trick to reduce exact LP burden.  
5\. Get the \`fromBlocks\` lemma proved by a Mathlib contributor; it’s a small, high‑leverage task.

The quadruple build is a natural extension, but the discovery dream is over. Focus on amplification and the trust gains.

# Kimi:Latest

\*\*This is an adversarial review. I believe you are about to spend 4–6 weeks building a costly museum piece with near-zero discovery value and a high probability of hitting an intractable rational-arithmetic wall that your Phase-0 spike is not designed to detect.\*\*

\---

\#\# 1\. Attack the premise: GMS 2012 is not a discovery frontier; it is a verification backfill

You state that the base three-point family is “mined out” and that GMS is the “right stronger formulation.” \*\*That framing conflates mathematical strength with epistemic opportunity.\*\* GMS 2012 \*is\* stronger than Schrijver 2005, but its improvements have been absorbed into Brouwer’s table over the past 13+ years. Therefore, reproducing GMS certificates cannot yield a table-beat; it can only yield a kernel-attested re-derivation of bounds already listed as best-known. \*\*Discovery EV is not “near-zero”—it is zero\*\* unless you target cells GMS never computed, which you admit are A(27,12) and A(28,12). 

\*\*The trap:\*\* those cells are not “open because GMS missed them”; they are \*\*untouched because the quadruple SDP at n≥27 is computationally intractable\*\* with 2012-era solvers and remains so today for exact certification. SDPA-GMP does not magically remove the \`O(n^6)\` variable growth of the four-point orbit space. You are planning to sprint into a wall that GMS already mapped.

\*\*What would change my mind:\*\* A \*\*machine-diff\*\* (not a manual reading) of Brouwer 2026 against the GMS 2012 table showing ≥3 cells where \`best\_ub \== Schrijver\_2005 \< GMS\`. I \*\*guess (70%)\*\* this set is empty or ≤1. If it is empty, \*\*kill the discovery objective immediately\*\* and scope the build down to a 1-week amplification spike for a single cell, or abort entirely.

\---

\#\# 2\. Phase-0 Spike Review

\#\#\# (A) GATE 1: Provenance

\*\*Wrong methodology.\*\* Do not rely on human reading of Brouwer’s table. Write a 50-line Python script that downloads the machine-readable Brouwer table, cross-references the GMS 2012 bounds (from the paper’s Table II/III or your own parse), and counts cells where:  
\- \`lb \< ub\` (still open), AND  
\- \`ub\_source ∈ {Schrijver\_2005, Delsarte, AVZ\_2001}\`, AND  
\- \`GMS\_bound \< current\_ub\`.

\*\*If count \< 3, RED.\*\* My prior: \*\*count \= 0\*\* for d∈{6,8,10,12}, n∈19..28. \*\*GUESSED (65%).\*\*

\#\#\# (B) GATE 2: Solvability at A(27,12) and A(28,12)

\*\*Likely RED, and your spike design does not test the actual blocker.\*\* The blocker is not “does SDPA-GMP return a number?” but “does the exact-rational LP leg close at this scale?” At n=27, the number of quadruple orbits is roughly the dimension of the 4-point Terwilliger algebra: \`O(n^4)\` variables after symmetry reduction, with block sizes up to \`\~n^2\`. The β-coefficients involve products of 8 binomial coefficients (quadruple intersection counts). The condition number of the resulting moment matrices is catastrophic.

\*\*Cheapest probe:\*\* Before any Lean build, attempt to \*\*form and solve the GMS SDP relaxation at n=22, d=8\*\* (a parameter GMS \*did\* compute) using SDPA-GMP at 1000-bit precision with a 4-hour timeout. Measure:  
\- Does it converge to a feasible point?  
\- What is the \`log10(condition\_number)\` of the largest block?  
\- Can you extract a rational dual multiplier vector with \`\<1000 bits\` of denominator using your existing exact LP leg?

\*\*RED if any of:\*\* convergence fails, condition number \> 1e16, or rational denominators explode. This probe costs \~$5 and one day; it validates whether the “solvable” cells are actually certifiable, not just numerically approximable.

\---

\#\# 3\. The Four Walls — concrete help and warnings

\#\#\# Wall 1: Block-diagonalization of the quadruple algebra

\*\*I cannot give you the explicit \`(k,l)\`-indexed β formula from memory. What I can tell you is that your assumption that it factorizes as a product of known constant-weight β’s is an unverified hypothesis that could collapse the build.\*\*

The three-point Terwilliger algebra decomposes under the action of \`S\_n\` on pairs. The four-point algebra decomposes under the action on 4-tuples, and its irreducibles are indexed by \*\*triples\*\* \`(k,l,m)\` or by partitions, not simply pairs \`(k,l)\`. The product structure \`β·β\` appears in the \*Gram matrix\* of certain vectors, but the block-diagonalization of the \*algebra\* itself requires \*\*Racah coefficients / 6j-symbols\*\* for the Hamming scheme (or Hahn polynomials). GMS 2012 §4-5 derives this; it is not a simple Kronecker product of Schrijver 2005 blocks.

\*\*Concrete guard:\*\* Before writing the Lean renderer, implement a \*\*computational algebra probe\*\* in Python/Sage:  
1\. Generate the adjacency matrices of the 4-point Hamming scheme for n=6 (small enough to be dense-manageable).  
2\. Compute their common eigenspaces numerically.  
3\. Compare the dimensions and multiplicities against GMS 2012’s Table I (or Prop. X).  
4\. Derive the β coefficients numerically from the eigenvectors and compare to your closed-form generator.

\*\*If the numerical β from (4) does not match the product-β assumption, your renderer is built on sand.\*\* This is a $0 probe (CPU only) and gates the entire build.

\#\#\# Wall 2: SDPA-GMP conditioning on β²-conditioned blocks

\*\*KNOWN:\*\* SDPA-GMP at arbitrary precision still uses the same interior-point algorithm; it does not remove ill-conditioning, it only delays overflow. With β coefficients spanning \`\~binom(22,11)^2 ≈ 10^12\`, a relative float error of \`1e-12\` becomes an absolute error of \`1.0\`, which is fatal.

\*\*Recipe:\*\*  
\- \*\*Scale each block individually\*\* before passing to SDPA. For block \`(k,l)\` with coefficient matrix \`M\`, compute diagonal \`D\` where \`D\_ii \= 1 / sqrt(max\_j |M\_ij|)\`. Replace the block constraint with \`(D^T M D) ≽ 0\`. This is a congruence transform, so PSD is preserved. Pass the scaled problem to SDPA.  
\- \*\*Track scaling in the dual certificate.\*\* The dual certificate block \`Z\` must be transformed back as \`D^{-T} Z D^{-1}\` before the kernel checks it. This inverse scaling must be applied in exact rational arithmetic inside the Lean generator.  
\- \*\*Use the “deleted factor” integer trick at the quadruple level.\*\* Schrijver deleted \`binom(...)^{-1/2}\` to keep coefficients integer. For the quadruple product blocks, there may be a similar normalization factor (a product of square roots). You must find and delete it to keep the kernel-side arithmetic rational. \*\*GUESSED:\*\* the normalization is the product of the two Schrijver normalizations; deleting both yields integer coefficients. Verify this from GMS eq. (X).

\*\*If you feed raw β² blocks to SDPA-GMP without scaling, the solver will return infeasible junk for n≥20.\*\*

\#\#\# Wall 3: Exact-rational LP active-set growth (\~40k multipliers)

\*\*Your current two-phase simplex approach will die at this scale.\*\* A 40k×40k rational tableau with Bareiss fraction-free elimination has bit-length growth \`O(n log n)\` in theory, but in practice the intermediate numerators/denominators for dense SDPs explode to thousands of bits. More importantly, the \*\*pivot selection\*\* in exact rational simplex is notoriously slow because you cannot use floating-point heuristics to pick the entering variable.

\*\*Better mechanism (mandatory):\*\* Abandon tableau simplex. Use a \*\*rational active-set projection\*\*:  
1\. Take the approximate dual multipliers \`ỹ\` from SDPA-GMP.  
2\. Identify the active set \`A \= {i : ỹ\_i \> 1e-8}\` (or by complementary slackness).  
3\. Solve the \*\*square linear system\*\* \`M\_A · y\_A \= rhs\` exactly over ℚ using \`fractions.Fraction\` Gaussian elimination, where \`M\_A\` is the submatrix of active constraints. This is \`O(|A|³)\` instead of \`O(m²n)\`.  
4\. Set \`y\_inactive \= 0\`.  
5\. Verify stationarity, nonnegativity, and bound exactly.  
6\. If verification fails, add the most-violated inactive constraint to \`A\` and re-solve (a rational cutting-plane method).

\*\*Why this works:\*\* In SDPs for code bounds, the dual multipliers are typically \*\*sparse\*\*—most nonnegativity constraints are inactive. The active set size is often \`O(n³)\`, not \`O(n⁶)\`. For your three-point build, you likely had \~12k multipliers but only \~500 were truly active. Exploit this.

\*\*Probe:\*\* On your existing three-point certificates, measure the fraction of nonzero dual multipliers. If \>10% are nonzero, my sparsity assumption is wrong and you need a different approach. If \<2%, the active-set method is validated.

\#\#\# Wall 4: Kernel elaboration of \~1 MB certificates

\*\*The source-size wall is a red herring; the term-reduction wall is the killer.\*\* Lean 4.31’s elaborator can parse multi-megabyte files if chunked. However, the \*\*kernel computation\*\* \`by decide\` on a stationarity identity involving a sum of 40k terms, each a product of two binomial sums (product-β), requires reducing a massive rational arithmetic expression. \`maxHeartbeats 0\` only removes the heartbeat counter; it does not remove the fundamental complexity of term reduction. If the intermediate normal form has millions of rational operations, the kernel will hang or OOM.

\*\*Concrete help on the lemma:\*\*

For \`Matrix.fromBlocks A 0 0 D\` PSD iff \`A\` and \`D\` PSD:

\`\`\`lean  
import Mathlib

lemma Matrix.fromBlocks\_psd\_iff {m n : Type\*} \[Fintype m\] \[Fintype n\] \[DecidableEq m\] \[DecidableEq n\]  
    {A : Matrix m m ℝ} {D : Matrix n n ℝ} :  
    (Matrix.fromBlocks A 0 0 D).PosSemidef ↔ A.PosSemidef ∧ D.PosSemidef := by  
  constructor  
  · \-- Forward: block-PSD implies each block PSD  
    intro h  
    constructor  
    · \-- A is PSD: for any x, xᵀ A x \= \[x;0\]ᵀ M \[x;0\] ≥ 0  
      refine ⟨h.1.blocks \_, fun x \=\> ?\_⟩  
      let y := Matrix.fromBlocks (Matrix.col Unit (fun \_ \=\> x)) (Matrix.col Unit (fun \_ \=\> 0))  
        (Matrix.row Unit (fun \_ \=\> 0)) (Matrix.of (fun \_ \_ \=\> 0))  
      \-- Actually simpler: use the quadratic form definition directly  
      have h1 := h.2 (fun i \=\> if i.isLeft then x (i.getLeft) else 0\)  
      \-- simp \[Matrix.fromBlocks, mul\_apply, Finset.sum\] at h1 ⊢  
      \-- exact h1  
      sorry \-- You need to expand the block multiplication and use Finset.sum\_subset  
    · sorry \-- symmetric for D  
  · \-- Backward: both PSD implies block PSD  
    rintro ⟨hA, hD⟩  
    refine ⟨?\_, fun x \=\> ?\_⟩  
    · \-- Hermitian  
      sorry \-- use hA.1 and hD.1  
    · \-- Nonnegativity  
      \-- Decompose x into left/right blocks  
      \-- xᵀ M x \= Σ\_{i,j∈m} x\_i A\_ij x\_j \+ Σ\_{i,j∈n} x\_i D\_ij x\_j  
      \-- This is hA.2 (x|m) \+ hD.2 (x|n) ≥ 0  
      sorry  
\`\`\`

\*\*Key tactic insight:\*\* Do not fight \`Matrix.mul\_apply\` with automation. Instead, prove the \`n\`-block version by \*\*induction on the number of blocks\*\*, using the 2-block lemma as the step. The induction hypothesis handles arbitrary partitions. For the base \`fromBlocks A 0 0 D\`, the proof is a direct calculation using \`Finset.sum\` manipulation.

\*\*More importantly:\*\* For the stationarity theorems, do not generate one giant \`by decide\` proof. Instead, prove each block’s stationarity as a \*\*separate theorem\*\* with explicit intermediate sums (\`have step1 : ...\`), so the kernel reduces incrementally. Chunking by \`(k,l)\` is correct; chunking further by \*\*half the stationarity sum\*\* may be necessary if individual terms are too large.

\*\*Synthetic load probe:\*\* Generate a fake Lean file with 220 theorems, each asserting \`∑\_{i=1}^{5000} (i : ℚ) \= ...\` (approximating your term complexity), and time \`lean \--make\` with \`maxHeartbeats 0\`. \*\*If this OOMs or takes \>30 minutes, your 1 MB certificate will not elaborate.\*\*

\---

\#\# 4\. Sanity-check the go/no-go economics

\*\*I agree with your assessment, and that agreement should frighten you.\*\* If discovery EV is near-zero and amplification is the only win, then a 4–6 week build is \*\*negative EV\*\* relative to spending those same engineering weeks on:

\- \*\*Horizontal transfer:\*\* Building a generic SDP certificate verifier that can ingest \*any\* algebraically-structured SDP (not just Terwilliger), or  
\- \*\*Verification amplification at scale:\*\* Kernel-attesting the existing literature backlog of \*already-published\* bounds that lack machine-checked proofs (e.g., the full Delsarte table, not just the Schrijver/GMS frontier).

A one-off GMS build produces a \*\*bespoke artifact\*\* (quadruple certificates for a handful of cells) that nobody asked for and that does not generalize. If you want to build infrastructure, build the \*\*certificate ingestion pipeline\*\*, not the quadruple renderer.

\*\*Mis-attribution I see:\*\* You attribute the lack of discovery to the producer wall (LLMs can't originate constructions), so you pivot to a stronger bound family. But the \*actual\* wall is \*\*frontier exhaustion\*\*: all easy cells are closed, and all open cells require either human constructions or computational resources beyond exact certification. GMS does not change this; it merely moves the wall from \`n≈25\` to \`n≈27\` at a 10× cost increase. \*\*The correct response to frontier exhaustion is not a stronger bound; it is a different objective function\*\* (e.g., counterexample search, as previously proposed, or verification amplification).

\---

\#\# 5\. One thing you are getting wrong

\*\*You believe the quadruple algebra is “just” the product of two three-point β’s, and therefore your existing \`(k,l)\` machinery ports trivially.\*\* This is the most dangerous assumption in the brief. The constant-weight \`(k,l)\` blocks you already ship are for the \*\*Johnson scheme\*\* (pairwise intersections in a fixed-weight layer). The quadruple GMS bound is for the \*\*Hamming scheme\*\* (unrestricted binary codes), and its Terwilliger algebra on 4 points involves the \*\*centralizer algebra of the hyperoctahedral group acting on 4-tuples of subsets\*\*. The decomposition into \`(k,l)\` blocks in GMS is \*\*not\*\* the naive product of two Schrijver decompositions; it is a decomposition under the action of \`S\_n\` on ordered pairs of subsets, where the multiplicities are given by products of binomial coefficients but the matrix entries involve \*\*Racah polynomials\*\* (Hahn polynomials in two variables). 

If you code the renderer assuming \`β\_quadruple \= β\_threepoint ⊗ β\_threepoint\`, you will generate plausible-looking Lean code that fails to reproduce the GMS bounds. The kernel will still check it soundly, but you will spend weeks debugging why the SDP optimum does not match the literature. \*\*Verify the algebra numerically before writing the renderer.\*\*

\---

\#\# 6\. Ranked pre-build probes (measure-before-build)

Execute these in order; stop at first RED.

1\. \*\*Automated table diff (GATE 1, $0):\*\* Script Brouwer 2026 vs GMS table. RED if \<3 cells with headroom.  
2\. \*\*Algebraic factorization probe (Wall 1, $0):\*\* Numerically compute quadruple β for n=6 from GMS formulas vs. your product-β assumption. RED if relative error \> 1e-12.  
3\. \*\*SDPA-GMP n=22 smoke test (Wall 2, \~$5):\*\* Run GMS SDP at n=22, d=8 for 4 hours. RED if no convergence or condition number \> 1e16.  
4\. \*\*Synthetic kernel load test (Wall 4, $0):\*\* 220 fake theorems with 5k-term rational sums. RED if elaboration \> 30 min or OOM.  
5\. \*\*Exact LP sparsity probe (Wall 3, $0):\*\* On existing three-point certs, measure active multiplier fraction. RED if \>10%.

\*\*Recommendation:\*\* Run probes 1–3 this week. If any is RED, \*\*cancel the 4–6 week build\*\* and redirect to horizontal infrastructure (generic SDP certifier) or pure verification amplification.

\---

\*\*Single prioritized recommendation in one sentence:\*\*

\*\*Cancel the GMS discovery track immediately unless the automated table-diff probe finds ≥3 open cells where GMS strictly improves the current best bound; regardless, do not write a line of the quadruple renderer until the numerical algebra probe confirms your product-β assumption and the n=22 SDPA-GMP smoke test yields a condition number under 1e16.\*\*

# GLM 5.2

This is a high-stakes build. You are attempting to jump from the three-point Terwilliger algebra (which is well-understood and tractable) to the four-point GMS 2012 formulation (which borders on computational intractability even with modern solvers). Your instinct to gate this aggressively is correct. 

Here is the adversarial review and concrete technical assistance requested.

\---

\#\#\# (A) Review the Phase-0 Spike Design

\*\*GATE 1 (Provenance): Is the two-gate decider right and minimal?\*\*  
The gate is right, but your premise that there are $\\ge 3$ open cells relying on Schrijver-2005 is likely \*\*FALSE\*\*. GMS 2012 explicitly targeted and tightened the most glaring gaps left by Schrijver. Furthermore, the community (Brouwer's table) incorporates lower-bound improvements constantly. You must verify the \*current\* Brouwer table, not the 2005/2012 papers. Do not assume $lb \< ub$ for $n \\in 19..28$ based on 2005 data; those gaps are likely closed by GMS upper bounds or newer lower bounds. 

\*\*GATE 2 (Solvability): A(27,12) and A(28,12)\*\*  
\*Is there a known reason the quadruple SDP isn't solvable there?\* \*\*Yes. Combinatorial explosion of the active set.\*\*   
At $n=27, 28$, the number of variables in the quadruple formulation balloons to tens of thousands. SDPA-GMP will struggle to find a high-precision float solution, but the true wall is the \*\*exact LP active-set extraction\*\*. A 40k-multiplier LP will have an active set of maybe 500-1000 constraints. Finding that exact active set using exact rational arithmetic from a float hint at $n=28$ is incredibly fragile. Float solvers at that scale silently drop tiny constraints. If you miss even one active multiplier, the exact rationalization fails. 

\*\*Spike Redirection:\*\* Do not spike on $n=27, 28$. Spike on \*\*A(20,8)\*\*. GMS tightened this from 290 (Schrijver) to 274\. It is small enough that SDPA-GMP will converge cleanly, and the active set is small enough to exactify. If you cannot exactify A(20,8), A(28,12) is a fantasy.

\---

\#\#\# (B) Help tackle the four WALLS

\*\*Wall 1: Block-diagonalization of the quadruple Terwilliger algebra\*\*  
You do not need to re-derive this. The quadruple algebra acts on $\\mathcal{P} \\times \\mathcal{P}$ (pairs of subsets). Its block-diagonalization is the \*\*Kronecker product\*\* of the three-point decompositions, filtered by the Johnson scheme constraints.   
Because you already have the constant-weight \`(k,l)\` product-block machinery, you already have the decomposition. The product-$\\beta$ formula \`β^{t,w}\_{i,j,k} · β^{s,v}\_{i,j,l}\` \*is\* the explicit change-of-basis for the 4-point algebra restricted to constant weight. GMS 2012 is essentially the 4-point bound \*projected\* onto the constant-weight subspace. Do not look for a separate 4-point basis; use the \`(k,l)\` tensor product you already ship. Citation: Laurent 2007 (§3.2) establishes that the tensor product of the Terwilliger algebra decomposes as the direct sum of the tensor products of the irreducible modules.

\*\*Wall 2: SDPA-GMP conditioning\*\*  
The $\\beta^2$ conditioning will murder standard SDPA-GMP. The coefficients will span 8+ orders of magnitude.  
\*Mandatory recipe:\* \*\*Pre-normalize the basis matrices.\*\* Before passing the constraint matrices $F\_i$ to the solver, scale them: $F'\_i \= F\_i / \\|F\_i\\|\_F$ (Frobenius norm). Solve the SDP with the scaled matrices. When you extract the dual variable $y'\_i$ from the solver, the \*real\* dual variable is $y\_i \= y'\_i / \\|F\_i\\|\_F$. If you do not do this, SDPA-GMP will return \`nan\` or false optima for $n \\ge 22$.

\*\*Wall 3: Exact-rational LP active-set growth\*\*  
Do not run Bareiss simplex on a 40k $\\times$ 40k tableau. It will take weeks and terabytes of memory.  
\*Concrete advice:\* Use a \*\*float-to-exact hybrid\*\*.   
1\. Run a high-precision float LP (using HiGHS or CLARABEL) to find the optimal basis (the active set).  
2\. Extract the indices of the active constraints. At optimum, $\\sim 99\\%$ of constraints are inactive ($y\_i \= 0$).  
3\. Build a \*tiny\* exact-rational sub-tableau consisting \*only\* of the active constraints.  
4\. Run Bareiss/\`certify\_lp\` \*only\* on this sub-tableau.   
This reduces the problem from a 40k square matrix to a \~500 square matrix, which Bareiss solves in seconds.

\*\*Wall 4: Kernel elaboration of a \~1 MB certificate\*\*  
220 stationarity theorems will absolutely time out the Lean 4 kernel if rendered as one monolithic term.  
\*The Lemma:\* \`(Matrix.fromBlocks A 0 0 D).PosSemidef ↔ A.PosSemidef ∧ D.PosSemidef\`  
If your automated prover failed this, it is because you are not unfolding the definition of \`PosSemidef\` and \`fromBlocks\` properly. In Mathlib, \`PosSemidef M\` is typically \`∀ v, 0 ≤ vᵀ M v\`.  
\*Proof strategy (works in Lean 4):\*  
1\. Unfold \`PosSemidef\` to the quadratic form \`∀ x, dotProduct (M.mulVec x) x ≥ 0\`.  
2\. For a vector \`x\` over blocks, split it into \`x \= (a, b)\`.  
3\. \`mulVec (fromBlocks A 0 0 D) (a, b)\` simplifies (via \`simp\` with \`Matrix.mul\_apply\` and \`fromBlocks\`) to \`(A.mulVec a, D.mulVec b)\`.  
4\. The dot product simplifies to \`dotProduct (A.mulVec a) a \+ dotProduct (D.mulVec b) b\`.  
5\. The bidirectional split follows directly from \`add\_nonneg\` and the individual PSD assumptions.  
\*Do not build a generalized n-block lemma.\* Chunking is your friend. Render 220 individual \`PosSemidef\` theorems for the \`(k,l)\` blocks, verify them independently, and then use a simple \`List.All\` aggregator. This avoids a 1MB term and keeps kernel heartbeats low.

\---

\#\#\# (C) Sanity-check the go/no-go economics

\*\*Your assessment is exactly right.\*\* The Discovery EV for GMS is 0%. Gijswijt, Mittelmann, and Schrijver were expert practitioners using specialized solver configurations; Leibniz will not beat their bounds using their own method. 

\*\*The Amplification EV is substantial, but you are undervaluing it.\*\* You frame it as "re-deriving published records." In the formal methods community, this is known as \*\*verifying computational mathematics\*\*, and it is a top-tier result. The GMS 2012 bounds are trusted entirely because of the authors' reputations and spot-checks; no one has independently \*proven\* them from first principles. Providing a Lean-kernel-verified certificate for A(20,8) ≤ 274 is a genuine, publishable contribution to the intersection of formal methods and coding theory.

\*\*Mis-attribution check:\*\* Do not waste time trying to formalize the \*algorithm\* GMS used (e.g., the specific SDP solver heuristics). Formalize only the \*output\* (the exact dual certificate). The solver is untrusted; the certificate is the math.

\#\#\# Bottom Line

The A(28,12) target is a trap that will consume 6 weeks and return an OOM error. Shift the spike to A(20,8). Normalize the SDP basis matrices. Do not run full exact simplex—extract the active set in float and exactify only the active sub-tableau. Chunk the Lean certificate per \`(k,l)\` block. If the A(20,8) spike fails to exactify, the whole GMS build is RED.

# Gemini 3.5 Thinking

This is an exceptionally well-thought-out verification pipeline. Scaling up from Schrijver’s three-point bound to the GMS 2012 quadruple-distance bound inside a strict proof assistant kernel like Lean 4.31 is an ambitious, high-value milestone for formal combinatorics.  
Here is a critical review of your brief, addressing your specific gates, walls, and economic assumptions.

## **(A) Phase-0 Spike Design & Gates**

### **GATE 1: Provenance & Open Cells**

Your threshold of $\\ge 3$ open cells is met. In the standard coding theory tables (e.g., Brouwer's tables), there are several prominent cells in your target region where the reigning upper bound is still inherited from Schrijver-2005 (or earlier) and a significant gap remains:

* **$A(19,6)$**: Bound stands at $1024 \\le A(19,6) \\le 1280$ (Schrijver 2005).  
* **$A(23,6)$**: Bound stands at $8192 \\le A(23,6) \\le 13766$ (Schrijver 2005).  
* **$A(25,10)$**: Bound stands at $192 \\le A(25,10) \\le 503$ (Schrijver 2005).

Because GMS 2012 focused heavily on $d \\in \\{6, 8, 10\\}$ for specific ranges and matched rather than beat Schrijver on these particular vertices, your pipeline has plenty of headroom to amplify and re-verify these classic results at the kernel tier.

### **GATE 2: Solvability of AVZ-2001 Cells**

The pre-SDP Agrell–Vardy–Zeger (2001) cells—**$A(27,12) \\le 169$** and **$A(28,12) \\le 288$**—were omitted by GMS primarily due to scoping choices and the sheer curse of dimensionality on 2012-era hardware when constructing quadruple orbits for large $n$.

* **Three-point SDP Solvability:** Absolute **GO**. For $n=28$ and $d=12$, the three-point Terwilliger algebra block sizes are incredibly small (the largest blocks are well under $30 \\times 30$). Modern SDPA-GMP will solve this in seconds at arbitrary precision.  
* **Quadruple SDP Solvability:** Highly viable but memory-intensive. The number of orbits for quadruples at $n=28$ spikes the constraint matrix size. However, given that $d=12$ forces vast swaths of your product-$\\beta$ coefficients to vanish (due to the distance constraints), the actual active constraint graph will be significantly sparser than the $d=6$ equivalents.

## **(B) Tackling the Four Measured Walls**

### **1\. Block-Diagonalization of the Quadruple Algebra**

To get your explicit $(k,l)$-indexed block reduction, look to **Litjens, Polak, and Schrijver (2017)** (*Semidefinite programming bounds for constant weight codes*). They lay out the explicit change-of-basis that generalizes Schrijver’s 2005 Propositions.  
Because your constant-weight code infrastructure already handles the doubly-indexed $(k,l)$ product-blocks, the mapping is symmetric: the quadruple algebra decomposes under the action of the symmetric group $S\_n$ into blocks indexed by the sizes of the intersections of the four subsets. You can write your change-of-basis matrices using products of discrete Hahn polynomials, which can be elegantly verified in Lean via their standard orthogonality relations.

### **2\. SDPA-GMP Conditioning Recipes**

With $\\sim 40\\text{k}$ multipliers and $\\beta^2$-conditioned blocks, SDPA-GMP will suffer from severe numerical fuzz unless pre-processed.

* **Hyperbolic/Log Scaling:** Do not feed raw binomial combinations directly to the solver. Scale the rows and columns of your input matrices by the square root of their diagonal entries (diagonal preconditioning) before handoff.  
* **Precision Floor:** For $n \\ge 22$, do not run at the standard 128-bit float tier. Set your GMP exponent and precision flags (mpf\_set\_default\_prec) to at least **512 bits** (and 1024 bits when approaching $n=28$). This keeps the Schur complement matrix inversion from stalling out near the optimum.

### **3\. Exact-Rational LP Active-Set Growth**

The Bareiss fraction-free algorithm is excellent for preserving exactness, but its integer explosion can quickly bottleneck memory.

* **Pivot Selection Strategy:** Modify your active-set selection to favor entering variables that minimize the bit-length growth of the resulting determinant (a "shallowest-growth" heuristic rather than pure steepest-edge).  
* **Periodic GCD Deflation:** Bareiss prevents fractions, but it does *not* prevent common factors across the entire row or tableau from inflating. To defeat the projected 3–5$\\times$ tableau growth, introduce a mandatory **row-wise GCD reduction step every $m/10$ iterations**. This dramatically compresses the integer bit-lengths.

### **4\. Kernel Elaboration & The Self-Contained Engine Lemma**

Your automated attempt likely failed because Lean's automation got tripped up by typeclass resolution on matrix dimensions or the implicit splitting of the dependent vector.  
The core lemma can be closed cleanly by isolating the forward and backward directions using explicit evaluation vectors. Here is the mathematical blueprint for your formalizer:  
Lean

```

import Mathlib.LinearAlgebra.Matrix.PosDef

variable {n m : Type*} [Fintype n] [Fintype m] [DecidableEq n] [DecidableEq m]
variable (A : Matrix n n ℝ) (D : Matrix m m ℝ)

lemma posSemidef_fromBlocks_diagonal :
    (Matrix.fromBlocks A 0 0 D).PosSemidef ↔ A.PosSemidef ∧ D.PosSemidef := by
  sorry

```

#### **Blueprint to Close the Proof:**

1. **Forward Direction ($\\rightarrow$):** Assume the total block matrix is PSD. To prove $A.\\text{PosSemidef}$, evaluate the total quadratic form $x^T M x \\ge 0$ using a split vector constructed via Sum.elim where the $n$-component is an arbitrary vector $v$ and the $m$-component is $0$. This collapses the block multiplication down to exactly $v^T A v \\ge 0$. Repeat symmetrically with $\[0, u\]^T$ to prove $D.\\text{PosSemidef}$.  
2. **Backward Direction ($\\leftarrow$):** Assume $A$ and $D$ are individually PSD. For any combined vector $w \= \[v, u\]^T$, expanding the definition of Matrix.mul\_vec across fromBlocks yields the split scalar sum:  
3. $$w^T \\begin{pmatrix} A & 0 \\\\ 0 & D \\end{pmatrix} w \= v^T A v \+ u^T D u$$  
4. Since $v^T A v \\ge 0$ and $u^T D u \\ge 0$ by your hypotheses, their sum is trivially $\\ge 0$.  
5. **The $n$-block Generalization:** Do not use a cascading binary tree of fromBlocks (which kills Lean's elaboration times). Instead, formalize it as a dependent sigma-type block diagonal matrix (Matrix.blockDiag). The lemma then maps directly to ∀ i, (M i).PosSemidef, which matches your intended per-$(k,l)$ chunking strategy.

## **(C) Go/No-Go Economics Sanity Check**

**Verdict:** Your economic assessment is spot-on.  
The expected value (EV) of *discovery* (finding a brand new, tighter upper bound that shifts standard coding tables) is incredibly low because these specific bounds have been heavily picked over for over a decade.  
However, the EV of **Verification-Amplification** is massive. Right now, the global trust boundary for these massive combinatorial bounds relies on unverified, floating-point, or closed-source C++ solvers from the early 2010s. By porting GMS to Leibniz and generating machine-certified proofs inside the Lean kernel, you are upgrading an empirical numerical approximation into an absolute, uncontestable mathematical truth. That is an unconditional win for formal verification.  
To help refine the automated generation of your chunked certificates, **what does the internal schema of your** block\_pairs **generator look like when tracking the overlapping orbits?**

# Qwen 3.7 Max

\*\*1. Attack the Premise: The $N=32$ Kernel Wall is Fatal for 4-Point\*\*  
Your brief completely ignores the kernel dimension wall you explicitly identified in the previous scoping round.   
\*I know\* that for the 3-point (Schrijver 2005\) algebra, the maximum block size is $n-2k+1$ (max $n+1$). For $n=28$, the max block is $29 \\times 29$, which safely passes your $N=32$ kernel PSD check.   
\*I know\* that for the 4-point (GMS 2012\) algebra, the block sizes correspond to higher-order representations and grow as $O(n^2)$. For $n=22$, the maximum block size easily exceeds $60 \\times 60$; for $n=28$, it exceeds $100 \\times 100$.   
\*Conclusion:\* Your native \`ldltOK\` kernel checker will OOM or timeout on the 4-point blocks before you ever finish the build. The brief assumes the $(k,l)$ machinery handles this, but it does not bypass the kernel's raw matrix-dimension limit. You must either (a) use the aggressive symmetry reduction of the \*\*split\*\* Terwilliger algebra (Litjens-Polak-Schrijver 2017\) to shatter these blocks further, or (b) abandon native kernel PSD checking in favor of a verified external certificate (e.g., verified Schur-complement or interval arithmetic). If you proceed with the current kernel checker, the build is dead on arrival.

\*\*2. Gate 1 & 2 (Provenance and Solvability)\*\*  
\*   \*\*Gate 1 (Provenance):\*\* \*I guess (85% confidence)\* you will find $\\ge 3$ open cells where the table still reflects Schrijver 2005, but mostly for odd $d$ or specific $n$ where researchers deemed the cell uninteresting. Do not confuse "no one ran GMS" with "GMS will tighten it." The headroom is likely zero.  
\*   \*\*Gate 2 (Solvability of A(27,12) / A(28,12)):\*\* SDPA-GMP will not fail due to \*precision\*; it will fail due to \*\*memory and time\*\*. The 4-point SDP for $n=28$ has $\\sim 10^5$ variables. A single interior-point iteration requires forming and factorizing a dense Schur complement matrix of size $10^5 \\times 10^5$ ($\\approx 80$ GB of RAM). \*Verdict:\* Solvable in theory, but practically out of reach for a 6-week build without a massive, dedicated HPC allocation. 

\*\*3. The 4 Walls\*\*  
\*   \*\*Wall 1 (Block-diagonalization):\*\* The explicit $(k,l)$ reduction in GMS 2012 is insufficient because the blocks are too large. You \*\*must\*\* use the \*\*split Terwilliger algebra\*\* from Litjens-Polak-Schrijver 2017 (DCC 84, 87), which exploits additional symmetries to reduce block sizes by an order of magnitude. Without LPS 2017, the SDP is intractable.  
\*   \*\*Wall 2 (Conditioning):\*\* SDPA-GMP is the wrong tool for 40k variables. Use \*\*Hypatia\*\* or \*\*Clarabel\*\* with high-precision floats, or use a first-order method (SCS) to get close, followed by Newton refinement on the exact rational manifold.   
\*   \*\*Wall 3 (Exact LP):\*\* Bareiss simplex on 40k variables will explode due to intermediate expression swell and sparsity destruction. \*Fix:\* Do not use Bareiss. Use \*\*floating-point solve $\\rightarrow$ rational basis identification $\\rightarrow$ exact sparse LU\*\*. Solve with HiGHS/Gurobi, identify the active basis, extract the basis matrix, and solve the small square system $B x\_B \= b$ in exact rationals using a sparse exact solver.   
\*   \*\*Wall 4 (Kernel Lemma):\*\* The Mathlib lemma you want is conceptually \`Matrix.posSemidef\_fromBlocks\_zero\_offdiag\`. If it is missing, here is the exact Mathlib 4 proof sketch to bypass the automated prover's failure:  
    \`\`\`lean  
    lemma posSemidef\_fromBlocks\_zero {A D} :  
        (Matrix.fromBlocks A 0 0 D).PosSemidef ↔ A.PosSemidef ∧ D.PosSemidef := by  
      refine ⟨fun h ↦ ⟨h.comp (Matrix.fromBlocks 1 0), h.comp (Matrix.fromBlocks 0 1)⟩, ?\_⟩  
      rintro ⟨hA, hD⟩  
      refine Matrix.posSemidef\_iff.mpr fun x ↦ ?\_  
      \-- decompose x into x1, x2; the cross terms vanish due to the 0 blocks.  
      \-- use hA x1 \+ hD x2 \>= 0  
    \`\`\`  
    \*Note: Adapt to exact Mathlib 4 API (e.g., \`Matrix.PosSemidef\`), but the mathematical path is trivial via \`comp\` (congruence) and vector decomposition.\*

\*\*4. Economics (Part C)\*\*  
Your assessment that "Discovery EV is near-zero" is correct, but your conclusion that "amplification value is real" is fundamentally flawed. Amplifying a 12-year-old result that is already in Brouwer's table yields \*\*zero mathematical novelty\*\*. Your daemon's invariant states "novelty is settled by a decision procedure". If it's in the table, the oracle flags it as NOT NOVEL. It will be quarantined as audit-tier. Spending 6 weeks to build a pipeline that produces audit-tier results is a massive opportunity cost. The \*only\* positive EV is if this build unlocks the infrastructure to run on cells GMS \*couldn't\* reach in 2012, AND those cells have headroom. If the $N=32$ kernel wall kills you, the EV is strictly negative.

\*\*5. One thing you're getting wrong\*\*  
You are treating the 4-point Terwilliger algebra as a straightforward extension of the 3-point algebra. It is not. The representation theory of $S\_4$ acting on the Hamming space introduces massive multiplicities and block sizes that do not exist in the 3-point ($S\_3$) case. Without the aggressive symmetry reduction of the \*split\* Terwilliger algebra (LPS 2017), the 4-point SDP is computationally intractable for $n \\ge 22$, both for the SDP solver and the Lean kernel.

Prioritized recommendation: Halt the GMS 2012 build immediately, run a probe to measure the exact maximum block size for the 4-point algebra at $n=22$ to formally confirm the $N=32$ kernel wall breach, and pivot to the LPS 2017 split Terwilliger algebra if you wish to proceed.  
```

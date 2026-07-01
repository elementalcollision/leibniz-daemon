<!--
Synthesis of the external review round on the Terwilliger/Schrijver three-point brief
(docs/external-brief-terwilliger-threepoint-2026-07-01.md). Analysis + corrected build plan only;
no code, no trust touch. Panel: 6 substantive reviews. The two load-bearing corrections are D2
(εI is invalid for the full dual) and D1 (constant-weight = a different scheme). Read before the build.
-->

# Terwilliger three-point — external review synthesis + corrected build plan (2026-07-01)

**Panel (6 substantive):** Fugu · Deepseek v4 Pro · Kimi · GLM 5.2 · Gemini 3.5 Thinking · Qwen 3.7 Max.
Fugu Ultra returned empty. This synthesizes their answers to `external-brief-terwilliger-threepoint-2026-07-01.md`,
resolves the disputes, and lays out the corrected build. **The kernel remains the sole decider; this document
touches no trusted surface.**

---

## 1. Unanimous consensus — build directly on these

1. **§1 formulation is correct.** Integer β coefficients (delete the `binom(n-2k,i-k)^{-1/2}` normalization;
   PSD is congruence-invariant so this is safe and *decisive* for exact arithmetic); two block families
   `M_k(x)` (from R) and `M'_k(x)` (from R', substituting `x⁰_{i+j−2t,0} − xᵗ_{i,j}`); block `k` size
   `p_k = n−2k+1`, indices `i,j ∈ {k,…,n−k}`, `k ∈ {0,…,⌊n/2⌋}`; **k=0 block = the Delsarte LP.** (6/6)
2. **Dimension-wall escape confirmed.** The kernel never sees the 2ⁿ ambient matrix; the largest PSD object
   is the k=0 block, `(n+1)×(n+1)` (20×20 at n=19). (6/6) — **but two reviewers (Fugu, Kimi) add a trap:**
   do **not** assemble `blockdiag(Z₀,Z'₀,Z₁,…)` into one matrix (~220×220 at n=19 → back over the wall).
   Check each block *independently* with `ldltOK`. ✅ This confirms our own foundation finding #215-(i).
3. **The three-point bound must contain the LP.** k=0 = Delsarte; without it the SDP can be *weaker* than
   the LP. ✅ Confirms our foundation finding #215-(ii) (plain full-graph ϑ floored to 6 vs 4 on A(8,5)).
4. **DROP A(12,5).** The illustrative "40→32" is unverified/hallucinated. (6/6 — Gemini: A(12,5)=A(13,6)=32
   is *already* the LP value, zero improvement; Qwen: A(12,5)=A(11,4) by the odd-distance rule; GLM: 32 needs
   the *split*-Terwilliger algebra, not 2005; Kimi/Deepseek: not a strict-improvement cell, LP=SDP=32.)
5. **The 2005 formulation is sufficient** for the first strict-improvement targets; split-Terwilliger /
   quadruples are only for larger n. (6/6, some at "GUESSED 75%".)
6. **No transcendentals.** Integer β + rational dual matrices + rational multipliers ⇒ the certificate is an
   exact rational identity, denominators clear to one integer equality. (6/6)
7. **SCS conditioning is the #1 engineering risk.** The β entries span ~`binom(19,9) ≈ 10¹⁰`; `eps=1e-7`
   absolute tolerance is meaningless against 10¹⁰ coefficients. (6/6 flagged.) Fixes below (D6).

---

## 2. The reframing that outranks everything (Fugu, echoed by Qwen)

**The kernel checks certificate *arithmetic*, not the *formulation*.** If Schrijver's construction is
transcribed with a consistent wrong sign/convention — used by *both* the untrusted solver and the checker —
the kernel will happily verify a valid certificate for the **wrong SDP**, and stamp a bound that may not even
be about the claimed quantity (Qwen's Trap 3: running the Hamming formula on a constant-weight cell certifies
`A(17,6) `, not `A(17,6,7)`). The kernel never sees the string "A(n,d)"; it sees integer matrices.

**Consequence for our trust boundary.** A formulation transcription is an LLM/human *proposal*. By our own
charter (inv 1: no LLM decides a proof; inv 7: Q.E.D. iff `kernel_verified`), it **cannot be stamped Q.E.D.**
until the reduction *itself* is kernel-checked — i.e., a **bridge theorem** in Lean:

> `feasible-dual (y, {Z_k, Z'_k}) with these PSD + linear-identity certificates  ⟹  A(n,d) ≤ b`.

Absent that theorem, the honest output tier is audit-level **`DUAL_CERTIFICATE_CHECKED`**: *"these specific
integer matrices are PSD and satisfy these specific integer identities."* The step to *"therefore A(n,d) ≤ B"*
rests on the transcription, which is in the TCB. → **Operator decision #1** (§5).

De-risking the transcription short of the full bridge theorem (all become build gates, §4):
- **k=0 ≡ Delsarte regression** — our k=0 block must reproduce the #209 Delsarte certs *exactly*.
- **Reproduce a KNOWN Table I integer before any open cell** — reproduction ⇒ formulation almost-certainly right.
- **Primal–dual cross-check** (Fugu) — compute a primal feasible point; primal obj ≈ dual obj ⇒ self-consistent.
- **Tiny n=8,d=4 full example** (Deepseek, Fugu) — catches index/off-by-one bugs at negligible cost.

---

## 3. Resolved dissents

### D1 — First target: unrestricted (Hamming) vs constant-weight (Johnson). *Load-bearing.*
The fault line: **A(17,6,7) is constant-weight ⇒ the Johnson scheme ⇒ a *different* Terwilliger algebra**
(different β tensor, block sizes, constraints). Fugu warns it "may need a separate Johnson-scheme
formulation"; **Qwen states it flatly (Trap 3)**. GLM and Deepseek treat constant-weight as merely "a smaller
sub-case" of the Hamming machinery — which Fugu/Qwen say is **wrong** and silently bounds the wrong quantity.
- **Resolution: the first target MUST be unrestricted (Hamming).** Reusing the Hamming three-point machinery is
  the entire point; a constant-weight cell would require building a *second* (Johnson) algebra and carries a
  silent-wrong-quantity risk. Constant-weight is deferred to its own later build.
- Unrestricted candidates:
  - **A(19,6): 1289 → 1280.** Cited by 4/6 (Fugu, Deepseek, Kimi, Qwen) as the canonical smallest unrestricted
    strict improvement in Schrijver Table I. Cost: 20×20 largest block (well inside the wall). Gap 9 (Kimi/GLM
    note small gaps are harder for float solvers → needs the conditioning fixes).
  - **A(12,4): 135 → 132.** Gemini *only*; cheaper (13×13 blocks) and Gemini claims the optimum is *rational*
    (=132 exactly → no irrationality tax). **Unverified** by the other five.
- **Recommendation:** in Phase 0, text-verify both against Schrijver's Table I. If A(12,4) 135→132 checks out,
  use it as an even-cheaper warm-up — **the same unrestricted renderer serves both**, so this is low-risk. Else
  go straight to A(19,6). → **Operator decision #2** (§5), but deferrable because one renderer covers both.

### D2 — The εI strict-PD margin is INVALID for the full dual. *Load-bearing correction to #214.*
**Qwen (Trap 2) + Kimi:** adding `εI` to a dual slack `S_k = Σ yᵢAᵢ − C_k` breaks dual feasibility, because
`S_k` is pinned by the equality system `Aᵀy = c`; perturbing it means it is no longer the slack of the original
problem. Our #214 εI trick worked *only* because there `t` was a **free** scalar being minimized in `Z(t)=tI+W`
— it does **not** transfer to the three-point dual.
- **Fix (synthesis of Kimi + Qwen):**
  - **(a) Feasibility-SDP at the target** (Kimi, preferred). Fix `t = target integer` (e.g. 1280) and *solve
    for feasibility*, not optimality. Because the target integer sits strictly above the true (≈1279.x)
    optimum, the slack `S(target)` gains a margin that **restores strict positive-definiteness** — so the
    existing `ldltOK` / Bareiss (`#212`/`#215`) certify it **with no kernel change and no εI**. This also
    turns a hard optimization into an easy feasibility check, exactly what exact certification wants.
  - **(b) Pivoted LDLᵀ** (Qwen, fallback). If the target-feasibility slack is still numerically singular, the
    proposer emits a symmetric (Bunch–Kaufman) factorization `(P, L, D)` and the **kernel checks
    `P·S·Pᵀ = L·D·Lᵀ` with `D_ii ≥ 0`** — a valid PSD certificate for a *singular* PSD matrix (which strict
    `ldltOK` and strict-minor `detSignOK` both reject). This **would** add a checker (`ldltPivOK`) to the
    trusted surface → gated, careful, but sound (checking an identity + `D≥0`; the permutation is a relabeling).
- Net: prefer (a); keep (b) in reserve. **Retire the εI-on-the-dual idea.**

### D3 — Dual feasibility is NOT "one scalar identity."
**Qwen (Trap 1) + Fugu + Kimi:** our brief asked for "one exact rational scalar identity." That conflates the
*objective* (`t = bᵀy`, a scalar) with *feasibility* (the β tensor defines `S_k = ΣyᵢAᵢ − C_k ⪰ 0`, not the
objective). The kernel must:
1. **Recompute each slack `S_k`, `S'_k` from `(y, β)` itself** (O(n³) integer ops/block) — never trust the
   producer's `S`. (Mirrors #215's Bareiss `detSignOK`, which recomputes minors from M.)
2. Check each `S_k ⪰ 0` block-by-block.
3. Check the **coefficient-matching system** — one exact rational identity *per primal-variable orbit* (Kimi:
   O(n³) tiny identities the kernel dispatches in a fraction of a second). Reducing to a single eliminated
   identity is "a comfort optimization, not a trust requirement," and risks a transcription bug. **Do not.**
4. Compute `t = bᵀy` and check `t ≤ target`.

### D4 — β-generator anchors CONFLICT; don't hardcode any reviewer's numbers.
Kimi (n=2, k=0): β¹₁₁₀ = **−2**. GLM (general): β¹₁₁₀ = **n** (=2 at n=2). Direct conflict, both
self-flagged low-confidence. Gemini gives n=4 anchors (β⁰₂₂₀=36, β²₂₂₀=−30, β¹₁₁₁=1) unreconciled with either.
- **Resolution:** write an **independent** brute-force integer β generator (zero-returning binomials, sum `u`
  over all integers — no manual loop clipping, per Kimi/GLM/Gemini/Qwen consensus on Q-block-1), validate its
  **k=0 slice against the #209 Krawtchouk code** (GLM: `β_{i,j,0}` is a Krawtchouk product; everyone agrees
  k=0=Delsarte is the golden anchor), then **publish our own β table (n=2..6) as the regression oracle** (Kimi).

### D5 — Derive the dual MECHANICALLY, not by hand (Kimi + Fugu, emphatic).
A hand sign-error will "burn weeks inside the `ldltOK` noise floor." Build a Python (CVXPY/SymPy) conic model
that assembles the primal in standard form and *prints* the dual constraints; transcribe those to the Lean
checker. Treat any hand-written dual formula (including those in these reviews) as a heuristic to sanity-check
the print, never as the spec.

### D6 — Solver conditioning: solve NORMALIZED, transform back EXACTLY (Qwen), or interior-point (Gemini).
Unanimous that raw β kills SCS. Concrete recipe:
- Solve with the **normalized** blocks `B̃` (O(1) condition number), then transform the dual back to the
  unnormalized `Z = D^{−1/2} Z̃ D^{−1/2}` **in exact rational arithmetic** before the kernel (Qwen). Equivalently,
  diagonal-congruence-scale each block to unit diagonal and bake the scale into the aggregation (GLM/Fugu/Kimi).
- Prefer an **interior-point solver (Clarabel/MOSEK)** over first-order SCS for these blocks (Gemini). Consider
  **SDPA-GMP** (multi-precision) for the warm start if float64 can't seed the exact system (Fugu).
- Combine with **feasibility-at-target** (D2a) and **Bareiss** (`#215`) to keep the certificate bit-length bounded.

---

## 4. Corrected build plan (sequenced, gated)

**Phase 0 — free-CPU, cheap, no solver (gates the whole build):**
- Text-verify against Schrijver Table I: **A(19,6) 1289→1280** and **A(12,4) 135→132**; confirm A(12,5) absent.
  (Fugu/Kimi/GLM all say this 2-hour check gates everything.)
- Independent integer β generator; validate k=0 slice vs #209 Krawtchouk; publish β oracle table (n=2..6).
- n=8,d=4 tiny full example scaffold for later dual-identity/index regression.

**Phase 1 — mechanical dual (free-CPU):** Python conic model prints the dual; from it, write the checker that
**recomputes `S_k(y,β)`** + the per-orbit coefficient system (D3). No hand-derived signs (D5).

**Phase 2 — solver (operator-local cvxpy/Clarabel):** normalized-block solve → **feasibility-at-target** (D2a)
→ exact rational round with **Bareiss** for bit-length (D6, #215).

**Phase 3 — kernel:** block-by-block PSD via existing `ldltOK`/Bareiss `detSignOK`. Only if the
target-feasibility slack is singular, add the **gated** pivoted `ldltPivOK` (D2b) — trusted-surface change,
behind the guard hook + operator sign-off.

**Phase 4 — reproduce BEFORE discover (the trust gate):** reproduce a **KNOWN** Table I value end-to-end,
kernel-checked, with k=0≡Delsarte regression green + primal–dual cross-check + block-profile/self-duality
microprobes (Fugu). **Only after reproduction passes** do we point the pipeline at a genuinely open cell.
Output tier stays **`DUAL_CERTIFICATE_CHECKED`** (audit) unless/until the bridge theorem lands (§2, decision #1).

---

## 5. Two operator decisions (everything else is determined)

**Decision #1 — Trust tier for SDP three-point outputs.**
- **(A) Audit-tier now (recommended).** Ship `DUAL_CERTIFICATE_CHECKED`; the kernel still guarantees the
  certificate arithmetic; reproduction + k=0 regression + primal-dual cross-check de-risk the transcription.
  Fast path to a real, checkable discovery frontier. Bridge theorem becomes a later, separate rung.
- **(B) Bridge theorem first.** Formalize the Terwilliger reduction in Lean so outputs can be Q.E.D. Much larger
  effort (weeks of Lean), touches trusted surface, but yields promulgable laws.

**Decision #2 — First reproduction cell** (deferrable — one unrestricted renderer serves both):
- **Verify-then-A(12,4)-else-A(19,6) (recommended):** cheapest warm-up if Gemini's 135→132 confirms; else the
  4-reviewer consensus A(19,6).
- **A(19,6) directly:** highest-confidence Table I cell, skip the A(12,4) verification.
- **Constant-weight A(17,6,7):** *not recommended first* — needs a separate Johnson-scheme algebra (D1).

---

## 6. What the panel VALIDATED about our existing foundation
- **#215-(i)** block-by-block wall escape — **confirmed 6/6** (with the "don't concatenate" caveat).
- **#215-(ii)** LP-inclusion necessity (k=0=Delsarte) — **confirmed**.
- **#214** irrationality-margin εI — **does NOT transfer** to the full dual (D2); corrected here to
  feasibility-at-target + pivoted-LDLᵀ. The #214 *result* (irrationality is surmountable) stands; the
  *mechanism* is replaced.

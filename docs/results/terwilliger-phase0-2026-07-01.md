<!--
Phase 0 of the SDP three-point build (per docs/results/terwilliger-review-synthesis-2026-07-01.md).
Free-CPU; no trust touch; tests/test_invariants.py byte-identical. Two deliverables: the Table I gate
(resolves the first-cell decision) and the validated integer β generator (the build's foundation).
-->

# Terwilliger three-point — Phase 0: Table I gate + validated β generator (2026-07-01)

Phase 0 is the free-CPU gate the panel said "gates the entire build." Two results, both GREEN.

## 1. Table I gate — from Schrijver's actual paper (not reviewer memory)

Fetched and text-extracted Schrijver 2005 (`homepages.cwi.nl/~lex/files/codes.pdf`). **Table I in full**
(new upper bounds on `A(n,d)`, computed from eq. (19)+(20) via maximizing (22)):

| n | d | best lower | **new (SDP)** | prev best | Delsarte LP |
|---|---|---|---|---|---|
| 19 | 6 | 1024 | **1280** | 1288 | 1289 |
| 23 | 6 | 8192 | 13766 | 13774 | 13775 |
| 25 | 6 | 16384 | 47998 | 48148 | 48148 |
| 19 | 8 | 128 | 142 | 144 | 145 |
| 20 | 8 | 256 | **274** | 279 | 290 |
| 25 | 8 | 4096 | 5477 | 5557 | 6474 |
| 27 | 8 | 8192 | 17768 | 17804 | 18189 |
| 28 | 8 | 16384 | 32151 | 32204 | 32206 |
| 22 | 10 | 64 | 87 | 88 | 95 |
| 25 | 10 | 192 | 503 | 549 | 551 |
| 26 | 10 | 384 | 886 | 989 | 1040 |

**Findings that settle the open decisions:**
- **A(19,6): 1289 → 1280 CONFIRMED.** It is the *smallest-n* row in the entire table — the canonical first
  unrestricted target, matching 4/6 reviewers.
- **A(12,4) is NOT in Table I** — Gemini's "135 → 132" is **hallucinated** (the whole table starts at n=19;
  there is *no* n<19 cell). The verify-leg of the operator's "verify-then-A(12,4)-else-A(19,6)" decision
  **fails**, so the first reproduction cell resolves cleanly to **A(19,6)**. (This is exactly the failure the
  gate was designed to catch — a reviewer number that evaporates against the source.)
- **A(12,5) absent**, as all six reviewers said. Dropped.
- Among the two n=19 cells, **A(19,6) (gap 9) is the better first target than A(19,8) (gap 3)** — a larger
  LP→SDP gap is easier for the float solver to hit (Kimi/GLM). Largest kernel block is 20×20 (`n+1`), well
  inside the N≈32–64 wall.
- The paper states Table I comes from **(19)+(20)** — **no split-Terwilliger needed** (confirms Q-pit-4 from
  the source, not just reviewer belief). Constant-weight is explicitly a *separate* Johnson-scheme construction
  (eq. 25) that "did not obtain any improvement" for the unrestricted table — confirming D1.

**Authoritative formulation extracted** (for the build, replacing all hand-transcribed reviewer formulas):
- **eq. (7):** `β^t_{i,j,k} = Σ_u (−1)^{u−t} · C(u,t) · C(n−2k,u−k) · C(n−k−u,i−u) · C(n−k−u,j−u)`. It is
  **C(u,t)**, not C(t,u) — this settles the reviewer conflict.
- **eq. (8) deleted factor** (the integer trick): `C(n−2k,i−k)^{−1/2} C(n−2k,j−k)^{−1/2}` — a positive diagonal
  congruence, so it is exactly the per-block scaling for the SCS-conditioning fix (D6).
- **eq. (19):** two PSD block families per `k=0..⌊n/2⌋`, size `p_k=n−2k+1`, `i,j∈{k..n−k}`.
- **eq. (20)(i)-(iv):** the linear constraints — and (20)(iv)'s `{i,j,i+j−2t}` form is confirmed correct for
  the *unrestricted* code (Kimi's worry was misplaced).
- **eq. (22):** maximize `Σ_i C(n,i) x^0_{i,0}`; **even-d reduction:** `x^t_{i,j}=0` if `i` or `j` odd.

## 2. β generator — validated against combinatorial ground truth (`scripts/terwilliger_beta.py`)

The panel warned that reviewers' hand β-anchors **conflict** (Kimi β¹₁₁₀=−2 via a transposed binomial; GLM
β¹₁₁₀=n; Gemini β⁰₂₂₀=36 is a partial sum). So we trust **no** anchor. Instead the generator (eq. 7 verbatim)
is validated by a **combinatorial differential test**: for any real code C, `x^t_{i,j} = λ^t_{i,j}/(|C|·C(n;i−t,j−t,t))`
(triple counts) makes **both** block families PSD by construction. A single wrong sign/index makes some real
code's block go non-PSD.

- **GREEN:** all 4 codes × 4 lengths (singleton, repetition, even-weight, full-space; n=3..6) give **both
  families PSD for all k** — 16/16.
- **Teeth:** the transposed-binomial corruption (`C(t,u)`, Kimi's exact error) **breaks PSD** on a real code
  — the test discriminates.
- **Anchors, now computed from eq. (7)** (not trusted): β⁰₀₀₀=1, **β¹₁₁₀=n** (GLM right, Kimi wrong),
  β¹₁₁₁(n=4)=1 (Gemini right), **β⁰₂₂₀(n=4)=6** (Gemini's 36 wrong).
- **Published oracle:** `docs/results/terwilliger_beta_oracle.tsv` — 372 nonzero β for n=2..6, the regression
  ground truth for the renderer build (Kimi's advice: publish our own table).
- Exact rational PSD test (`is_psd_exact`) handles the singular/rank-deficient blocks real codes produce
  (rank-1 for the full space) — the same semidefinite-not-just-definite need the dual certificate will have
  (relevant to D2's pivoted-LDLᵀ fallback). Fully free-CPU; CI-guarded by `tests/test_terwilliger_beta.py`
  (6 tests).

## Status
Phase 0 GREEN. First cell = **A(19,6) 1289→1280**; authoritative eq. (7)/(8)/(19)/(20)/(22) in hand; integer β
generator validated + oracle published. **Next: Phase 1** — mechanical dual derivation (Python conic model
prints the dual; checker recomputes the slack `S_k(y,β)` + per-orbit identity system). Trust tier stays
audit (`DUAL_CERTIFICATE_CHECKED`) per operator decision #1.

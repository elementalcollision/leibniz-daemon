<!--
Scoping (measure-before-build, design only) for the Schrijver SDP three-point certificate — the real
discovery bet in the code-bounds family, after the plain Delsarte LP reach probe returned NO-TIGHTENING.
No code, no trust touch. Decision-informing.
-->

# Scoping — the Schrijver SDP three-point certificate (2026-07-01)

## Why
The reach probe showed **plain 2-point Delsarte LP reproduces but does not tighten** best-known A(n,d) upper
bounds (0/38) — because the tables already incorporate it. The cells where LP was *looser* than best-known
(A(12,5): LP 40 vs 32; A(12,7): 5 vs 4; A(16,5): 425 vs 256; A(16,7): 50 vs 36) are exactly where a
**stronger** method already won. That method is the **Schrijver semidefinite (three-point / Terwilliger
algebra) bound** — the source of most modern best-known UB improvements over LP. It is the one surveyed path
with a real shot at a *genuine, sound-checkable* discovery. This scopes it before any build.

## Mechanism
- **Untrusted producer:** an SDP solver finds a dual-feasible solution to the three-point relaxation over
  the Terwilliger algebra (block-diagonalized). The dual certificate is a set of **PSD matrices** (one per
  block) plus multipliers satisfying linear constraints; feasibility ⇒ an upper bound on A(n,d).
- **Sound re-check (the kernel's job):** verify, in exact arithmetic, that (a) each certificate matrix is
  **PSD**, and (b) the linear dual inequalities hold, and (c) the objective gives the claimed bound.

## The hard part — an exactly-kernel-checkable PSD certificate
LP's certificate was trivially integer (clear denominators). PSD is the fragile step (GLM flagged it):
- **Rounding:** float SDP solutions must round to **exact rationals that remain PSD** while staying dual-
  feasible — much harder than LP rounding (the PSD cone has no slack in the wrong directions). Standard
  fixes: round the interior solution with margin, then re-project; or exploit the block structure.
- **Kernel-checkable PSD proof (integer, no Mathlib — mirrors our covering/Delsarte checkers):** clear
  denominators to an integer matrix `M`, then prove `M ⪰ 0` by one of:
  1. **Integer LDLᵀ / Cholesky:** exhibit `M = L·D·Lᵀ` with rational `L` (unit lower-triangular) and `D ≥ 0`
     diagonal; the kernel checks the product equals `M` and `D ≥ 0`. Cleanest; the producer supplies `L,D`.
  2. **Sylvester's criterion:** all leading principal minors ≥ 0 via **exact integer determinants** — kernel-
     computable, but O(size³) determinants and PSD (not PD) needs care with zero minors.
  3. **Sum-of-squares:** `xᵀMx = Σ (linear form)²` with rational coefficients — a rational SOS certificate.
  Option 1 (LDLᵀ, producer-supplied factors) is the recommended kernel target: verification is a matrix
  multiply + diagonal-sign check, all integer after denominator clearing — no eigenvalues, no decide-wall.
- **Size:** the Terwilliger blocks are modest for small n (the three-point matrices are indexed by triples
  but block-diagonalize to size ~n/2 per block), so the integer certificate stays small — the same regime
  where the LP certs kernel-verified to n=24.

## Soundness posture
Same as everything: the SDP solver + the rounding are **untrusted proposers**; the kernel decides the PSD
factorization + linear inequalities. A bad certificate fails the exact re-check. `Q.E.D.`/promulgation still
requires the analog of the Delsarte bridge lemma (`certificate ⇒ A(n,d) ≤ bound`, i.e. the three-point
bound's correctness) — deferred, audit-tier until then, exactly like LP.

## First probe (measure-before-build; the make-or-break)
**Reproduce a known SDP-improved UB via an exact rational PSD certificate the kernel checks.** Target the
smallest cell where SDP is known to beat LP — e.g. **A(12,5)** (LP 40, best-known 32) or A(16,5) (425 → 256).
- Solve the three-point SDP (untrusted, float) → dual PSD solution.
- Round to a rational PSD certificate; clear denominators; produce integer LDLᵀ factors.
- Kernel-check: `M = L·D·Lᵀ`, `D ≥ 0`, linear dual inequalities hold → bound.
- **GREEN:** a rational PSD certificate verifies (kernel) and reproduces the SDP-known bound (e.g. 32 for
  A(12,5)). This proves the exact-PSD pipeline is feasible → then push to *open* cells for a real tightening.
- **RED:** float→rational→exact-PSD rounding cannot produce a verifying certificate at reproduction scale →
  plain SDP-certificate discovery is out of reach without heavier exact-SDP machinery; bank LP and stop.
- **Cost:** an SDP solver dependency (e.g. SCS/CVXPY, float; operator-local) + the rounding/LDLᵀ tooling;
  ~days of engineering. The probe itself is ~$0 compute.

## Risks
- **PSD exact-rounding fragility** (the #1 risk; LP rounding held, PSD is harder).
- **Block-diagonalization complexity:** the Terwilliger reduction is intricate; a bug yields an invalid
  certificate — caught by the kernel (safe, just no result), but engineering-heavy.
- **Even reproduction may be hard;** and tightening an *open* cell is a research-grade outcome, not assured.
- **Oracle:** a genuine tightening still needs the authoritative version-pinned UB oracle before any claim.

## Recommendation
This is a genuinely heavier bet with real fragility — appropriate for a **gate before committing**:
- Option A: an **external mini-round** on SDP-three-point-certificate feasibility (the exact-PSD rounding +
  kernel-checkable-PSD question specifically), like the discovery-frontier round.
- Option B: a **$0 feasibility micro-probe** — attempt the exact rational LDLᵀ PSD certificate on one
  SDP-improved cell (A(12,5)) directly; if the rounding+kernel-check works, greenlight the build; if not,
  bank LP as the final word on this family.
Either resolves whether the SDP discovery path is real before sinking a multi-day build into it.

Prereqs already banked: the LP certificate architecture (`scripts/delsarte_lp_probe.py`,
`scripts/delsarte_bank.py` — the kernel-checked UB corpus) and the core-Lean integer-certificate + Krawtchouk
machinery this would extend.

---

## Addendum (2026-07-01) — external-agent critique + our measurements (REVISES the above)

An external agent attacked this scoping. Its technical points are largely correct; folding them in materially
changes the risk picture. The certificate MECHANISM is fine, but the DISCOVERY-critical risk was under-weighted.

**(1) The mechanism is Strict-PD + rational Cholesky — NOT LDLᵀ on boundary PSD.** The agent is right that a
tight SDP bound puts the optimal dual on the PSD-cone *boundary* (PSD-not-PD → LDLᵀ hits zero pivots → needs
Bunch–Kaufman pivoting, a big Lean effort). The fix (and what the exact-PSD micro-probe #212 *already*
implemented): push to the interior with an exact rational `εI`, giving strict PD → **rational Cholesky with
no pivoting**. So the micro-probe's mechanism is validated — but note it dodged the boundary by construction,
which is exactly why its GREEN is only a *mechanism* result.

**(2) The compute trap is REAL — measured.** `scripts/psd_scaling_probe.py` (gate #2): with naive rational
Cholesky the exact certificate's integer **bit-length grows ~quadratically — 944 bits (n=6) → 30,773 bits
(n=30)** — and kernel-check time climbs (≈4 s at n=18). At Terwilliger-block scale this matches the agent's
>10⁴-bit / kernel-timeout warning. **Mitigation (untested):** a **Bareiss / fraction-free** integer
elimination bounds the certificate to determinant size (~hundreds of bits) — plausibly a naive-implementation
wall, not fundamental (cf. the GATE-2 maxRecDepth artifact). A Bareiss LDLᵀ is a REQUIRED build technique, not
optional.

**(3) The Irrationality Wall is the PRIMARY, still-untested risk (likely fatal for discovery).** Spectrahedra
have algebraic-irrational extreme points; on an *open* cell the optimal dual face may contain no rational
point, so any rational dual-feasible certificate has objective strictly above the true optimum. The `εI` shift
*adds* to the objective. If the SDP optimum sits just below the integer (e.g. 31.9…), the rational-over-
approximation + `εI` margin can push `⌈objective⌉` to the next integer → **fails to certify the tighter
bound**. The micro-probe (#212) did NOT test this — it ran on synthetic strict-PD matrices, and the scoping's
original probe (reproduce A(12,5)=32, a small highly-symmetric cell with a wide rational face) is a **False
GREEN**: reproducing it says nothing about open cells where the face is a single irrational point.

**Revised gate (before any multi-day build) — needs an SDP solver (SCS/cvxpy, operator-local):**
1. Reproduce A(12,5)=32 via a rational PSD (strict-PD Cholesky) certificate, using **Bareiss** to keep
   bit-length bounded, kernel-checked. (Necessary, not sufficient.)
2. **Falsify the False-GREEN:** run a slightly larger, *less-symmetric / non-tight* cell (e.g. A(14,5),
   A(16,5)) and measure the **irrationality margin** — the gap between the rational-certified bound (with the
   smallest `εI` that keeps denominators kernel-checkable) and the target integer. GREEN only if the margin
   is positive on a cell where SDP must beat LP; RED if the rational+`εI` bound floors to the wrong integer.
3. Confirm the Bareiss certificate stays kernel-checkable (bit-length + time) at the real block size.

**Revised recommendation.** The build is **higher-risk than the micro-probe implied**: mechanism GREEN,
compute-trap real-but-mitigable (Bareiss), and the **Irrationality Wall (agent's 95%) untested and plausibly
fatal for discovery on open cells**. Do **not** commit the multi-day build on the micro-probe GREEN alone.
Either (a) run the revised gate above (add an SDP solver → the irrationality-margin falsification test) — the
honest measure-before-build step; or (b) **bank the LP win as the product and treat SDP discovery as a
low-confidence, deferred bet.** Reproduction remains necessary-but-insufficient; the margin test is the real
decision.

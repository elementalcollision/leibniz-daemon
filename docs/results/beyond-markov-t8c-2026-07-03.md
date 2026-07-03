# T8-c — Minimal Positive Realization: kernel-certified, GREEN, and honestly AMPLIFICATION (2026-07-03)

**Result: GREEN, kernel sound — and it settles the one discovery-shaped bet on the beyond-Markov track as
AMPLIFICATION.** A 5-agent soundness workflow verified the certificate + witness before the build; the real
Lean 4.31 kernel then certifies a **minimal-positive-realization > linear-dimension** separation for a concrete
small rational process, rejecting both corrupted controls. `scripts/beyond_markov_mprp.py`,
`docs/results/beyond_markov_mprp.json`, `tests/test_beyond_markov_mprp.py`. No trust surface touched.

## The claim, certified

The **4-state cyclic ("necklace") Markov chain** on `{0,1,2,3}` — circulant `A` with support the 4-cycle
`M = [[1,1,0,0],[1,0,1,0],[0,1,0,1],[0,0,1,1]]`, uniform stationary `π`, each state emitting its label — is a
valid stationary rational process whose word-Hankel has **ordinary rank exactly 3** (stable to length 3), yet
whose minimal **positive** (HMM) realization is **4**. So **no 3-state positive HMM realizes it** while its
OOM/linear dimension is 3.

Two sound bridges (verified in the workflow, full injectivity/factorization proofs in
`beyond_markov_mprp.json` provenance):
- **HMM ⇒ nonneg factorization.** An r-state positive HMM gives `H = F·B` with `F,B ≥ 0`, inner dim r, so
  `nonneg-rank(H) ≤ r`. Contrapositive: `nonneg-rank(H) > r ⇒ no r-state positive HMM`.
- **Fooling-set lower bound** (Fiorini–Kaibel–Pashkovich–Theis). Positions with positive diagonal and vanishing
  cross-products ⇒ `nonneg-rank ≥ t`. **Combinatorial** (sign/zero pattern), decided by integer positivity +
  zero-products — **not** an LP.

The length-2 Hankel block is `H2 = (1/8)·M`, so `M` carries the size-4 fooling set `{(0,0),(1,2),(2,1),(3,3)}`
⇒ `nonneg-rank(H) ≥ 4`, while the 4 chain states give the upper bound 4.

## What the kernel checks (core Lean, `decide`; both controls rejected)

`mprpOK M sub3 dep ri ci = depOK dep M 4 ∧ det3 sub3 ≠ 0 ∧ foolingOK M ri ci`:
- `depOK [1,−1,−1,1] M` — the dependency `r0−r1−r2+r3 = 0` ⇒ rank ≤ 3.
- `det3` of the `{0,1,2}` minor `= −1 ≠ 0` ⇒ rank ≥ 3.
- `foolingOK M {0,1,2,3} {0,2,1,3}` ⇒ nonneg-rank ≥ 4.

Measured: separation valid **True**; control **fill a structural zero** (`M[0][2]:=1`) **rejected** (breaks the
fooling predicate *and* the rank-≤3 dependency); control **all-ones J** with a bogus fooling claim **rejected**.
Audit: `π A = π`, `8·H2 = M`, consistency `Σ_x P(ux)=P(u)`, and Hankel rank = 3 at lengths ≤1 and ≤2.

## Honest verdict — AMPLIFICATION, with two hard limits

1. **This is a textbook fact, well-verified.** The 4-cycle rank-vs-nonneg-rank gap is the smallest classical
   0/1 gap (communication-complexity / extended-formulation folklore). The contribution is pinning an
   exact-rational, end-to-end **kernel-certifiable** witness (matrix + process), not new mathematics.
2. **The separation is minimal and shallow.** `+1` state, on a **fully-observed** chain (the positive
   realization is just the 4 chain states). It is *not* the deep **finite-OOM-but-no-finite-HMM** phenomenon
   (Jaeger's probability clock), which is **irrational and dense-Hankel** → **DEFERRED, unreachable by any
   finite fooling set**.
3. **The panel's "Farkas/LP" framing was wrong — corrected.** The sound tool is the combinatorial fooling
   `decide`; `exact_simplex`/LP is *not* it. Deciding `nonneg-rank ≤ k` in general is **ExR-complete** (the
   deferred SOS/Positivstellensatz territory), so **autonomous *search*** for the minimal positive realization
   is out of reach — only **verification** of a supplied separation is.

## Bottom line for T8

T8-c answers the standing EV question: **the beyond-Markov track is verification-amplification.** Its one
discovery-shaped lever certifies only a minimal, classical separation; the genuinely-open case is provably
beyond the exact-rational fooling machinery. T8 delivers three sound, kernel-verified capabilities (T8-a certs,
T8-b ∀k infinite order, T8-c the positive-realization gap) — all amplification, all behind the unbroken trust
boundary. Next: the rank-upper bridge lemma (make rank-lower into rank-exact), the same F2a/F2b REPL pattern.

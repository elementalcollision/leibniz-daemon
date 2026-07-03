# Beyond-Markov external witness review — synthesis + capability match/divergence (2026-07-03)

**Panel:** 8 reviewers of `docs/briefs/beyond-markov-external-brief-2026-07-03.md` — Fugu, Fugu Ultra, Deepseek v4
Pro, Kimi, GLM 5.2 (**empty**), Gemini 3.1 Pro, Qwen 3.7 Max, MiniMax M3 (7 substantive). The panel was
unusually strong and **convergent**. It found two load-bearing problems (an *impossible* flagship; a framing
error about the trust boundary), a genuine discovery lever, and the honest novelty position. This doc archives
the panel, records the durable corrections, and — the operator's specific ask — maps each proposed certificate
against Leibniz's **actual** machinery.

## Per-reviewer one-line verdict

- **Fugu** — sharpest constructive review: finite-Hankel-rank ≠ HMM (positivity needed); rank-upper needs a
  linear-representation cert, not window minors; infinite-order is a *restricted recurrence* cert (Lean
  induction), not Observatory; sell it as a certificate/benchmark domain, not discovery.
- **Fugu Ultra** — soundness traps (validity, window-vs-global rank, Z3-NRA, denominator positivity); the
  genuine discovery frontier is **HMM-rank / positive-realization (NMF) lower bounds**.
- **Deepseek v4 Pro** — novelty claim survives (no known formalization); BM-2 is the killer *if* valid;
  infinite-order is "a few hours of induction," upgrade it now; honestly amplification, not discovery.
- **Kimi** — the meta-critique: "kernel-attestable ≠ `decide`-checkable." The kernel checks proof *terms*;
  induction is as sound as `decide`. Create a **Q.E.D.-parametric** tier; the `∀k` theorems are the real product.
- **GLM 5.2** — empty (no content).
- **Gemini 3.1 Pro** — the Negative Probability Problem is *undecidable* for general OOMs (need an invariant-cone
  cert); a Z-transform/generating-function route to infinite-order; (its "discovery EV is profound" is an
  outlier, discounted).
- **Qwen 3.7 Max** — contrarian: the theory is a "solved fossil," discovery EV ≈ 0; **BM-3's quadratic-loss/Z3
  is a fatal soundness trap** (Z3-NRA is not a complete decider); pivot to the **Minimal Positive Realization
  Problem**; drop the MCR anchor.
- **MiniMax M3** — decisive catch: **BM-2 is mathematically impossible as stated**; the even-process order-1
  error is 1/4 not 1/3; the novelty is the *trust chain*, not the math; add kill-criteria + a process ontology.

## Durable corrections (incorporated)

**Soundness (load-bearing):**
1. **BM-2 is impossible as stated.** On a *stationary binary* process, `det B = p(1−p) − q`, so `rank(B)=1 ⟺
   q=p(1−p) ⟺ iid ⟺ rank(H)=1`. "rank-1 bigram ∧ rank-3 Hankel" cannot exist; our own witness `B=outer(p,p)`
   *is* iid. **Fix:** coarse-grain — a larger alphabet iid on a *coarsening* (e.g. parity) so the coarse bigram
   is rank 1 but the fine-alphabet Hankel is rank r; **or** drop BM-2 and lead with BM-4/BM-1. (Retracted in the
   conjecture bank.)
2. **Global rank-UPPER cannot be a finite window.** All 3×3 minors `=0` on a 4×4 block does **not** prove global
   `rank ≤ 2`. Use a rational linear representation `P(w)=α T_w ω` + a bridge theorem; window minors are
   regression tests only. Restate "rank = 2" as "≥2 by minor ∧ ≤2 by representation."
3. **Loss must be linear for the LRA/LP path.** Gini/quadratic loss is nonlinear → **Z3-NRA is not a complete
   decider**; using it as an arbiter *violates the "mechanical checker decides" invariant*. For linear 0-1 loss
   emit an exact LP-dual/Farkas cert; for quadratic loss emit a **PSD/SOS cert** (our `ldltOK`), never Z3-NRA.
4. **BM-4 needs an optimality proof** (lower-bound the best order-k loss), not just an exhibited predictor; and
   **recheck 1/3 vs 1/4** (the 1/3 is the causal-state optimum, not the order-1 floor).
5. **Process-validity is mandatory.** A Hankel minor certifies a *formal series*; a valid stochastic process
   needs `P(w)≥0 ∀w`, `∑_a P(wa)=P(w)`, `P(ε)=1`. Trivial for HMMs (nonneg matrices); undecidable for general
   OOMs → **prefer HMMs for every flagship**, or a per-instance invariant-cone certificate.

**The big reframe — infinite-order is Q.E.D.-reachable, not Observatory.** The kernel checks proof *terms*, so a
restricted recurrence certificate (`Δ_{k+2}=qΔ_k, Δ_0,Δ_1≠0, q≠0 ⇒ ∀k Δ_k≠0`) proved by induction is a full
Q.E.D. — the `decide`/`ldltOK` restriction was a *pipeline convenience*, not the trust boundary. Honest labeling
discipline (Qwen): the kernel attests "order > K" until the recurrence bridge lemma is *discharged*; only then
may we say "infinite order." This is the **F2b pattern applied to T8**: a bridge lemma, LLM-proposed,
kernel-checked.

**The discovery lever (convergent — Qwen, Fugu Ultra, Kimi).** Hankel-rank separations are amplification, but
the **Minimal Positive Realization Problem** is genuinely open and certificate-shaped: HMM (nonnegative) rank is
often strictly greater than Hankel rank; computing it = NMF = NP-hard. A **Farkas/LP-infeasibility certificate
that "no r-state positive HMM realizes this process"** is a real lower bound a machine could attest as *new*.

**Novelty reframe (MiniMax).** Bareiss dets and Z3-UNSAT live in every CAS; the contribution is the **end-to-end
Lean-kernel trust chain** (process → matrix → determinant → inequality, one proof object, replayable) — an
engineering contribution with research flavor, **not** "new mathematics discovered by AI."

## Capability match / divergence (grounded in the code)

Each proposed certificate vs. Leibniz's actual machinery (files verified 2026-07-03):

| Certificate shape | Leibniz machinery | Verdict |
|---|---|---|
| Hankel rank ≥ r (nonsingular rational minor `det≠0`) | `bareiss_minors` (`bareiss_ldlt.py:79`) + `detSignOK` (Lean, `:183`); flip `>0`→`≠0` | **MATCH** (one-line variant) |
| Rank-r factorization identity (integer matmul equality) | `verify_int_cert`/`ldltOK` pattern (`psd_certificate_microprobe.py:82`) minus PSD legs | **MATCH** (trivial `matMulEqOK`) |
| Markov order > K (cross-mult `det≠0` + denominator > 0) | `bareiss_minors` + exact-rational positivity | **MATCH** |
| Error floor, **linear** 0-1 loss (∀ predictor) | Z3-LRA (`p3_z3_floor_proven`) **or** the exact LP-dual (`exact_simplex`, `:35`, returns a Farkas cert) | **MATCH** (prefer the replayable LP-dual over Z3) |
| Error floor, **quadratic/Gini** loss | *not* Z3-NRA (unsound); a PSD/SOS cert → **`ldltOK`** (`:105`) | **MATCH via a different existing tool** (the "trap" is dodged) |
| Infinite order (∀k) via recurrence + induction | the Lean REPL runs non-`decide` Mathlib tactic proofs sorry-free — **demonstrated in F2a** (`rw/simpa/Finset.sum_nonneg/linarith/ring`, `terwilliger_f2a.py`) | **MATCH — pipeline-integration gap, NOT Observatory, NOT a new tier** |
| Global rank ≤ r (linear representation + bridge theorem) | Mathlib has `Matrix.rank`; needs a **new** `linear_rep ⇒ hankel_rank_le` lemma (an F2b-style slice) | **DIVERGE** (bridge lemma; achievable, like F2b) |
| Process validity — HMM (nonneg, row-stochastic) | trivial exact-rational checks | **MATCH** |
| Process validity — general OOM (global nonnegativity) | undecidable (NPP); only a per-instance invariant-cone Z3-SAT | **DIVERGE** (prefer HMMs) |
| **HMM/nonnegative-rank lower bound** (no r-state positive HMM exists) — *the discovery lever* | `exact_simplex` already returns `"infeasible"` (Farkas/LP-infeasibility cert); the NMF/positive-realization *encoding* is new | **MATCH-ADJACENT** (checker exists; encoding is the new work) |
| BM-2 (rank-1 bigram ∧ rank-r Hankel) as stated | — | **N/A — mathematically impossible; retract/fix** |

**Reading.** The match/divergence split is clean: **every finite lower-bound and separation certificate matches
machinery we already run** (`bareiss_minors`, `exact_simplex`, `ldltOK`, Z3-LRA). The panel's two scariest
objections both **resolve in our favor**: the "quadratic-loss decidability trap" is dodged by using `ldltOK`
(PSD/SOS) instead of Z3-NRA, and the "infinite-order Observatory ceiling" collapses because F2a already proves
non-`decide` Mathlib theorems through the kernel. The **real divergences** are exactly two, both known shapes:
(a) a **global-rank-upper bridge lemma** (the F2b pattern), and (b) **OOM validity** (undecidable → we stay in
the HMM subclass). The **discovery lever** (MPRP / HMM-rank lower bounds) is the one place the machine could
attest something new, and its *checker already exists* (`exact_simplex` infeasibility) — only the encoding is
unbuilt.

## Actions

- **Brief → v2:** BM-2 retracted/fixed (coarse-grain); §0 trust framing corrected (kernel checks proof terms,
  not just `decide`); BM-1 rank-upper → linear-representation cert; BM-3 loss split (linear→LP-dual,
  quadratic→PSD/`ldltOK`, never Z3-NRA); BM-4 optimality + 1/3-vs-1/4; process-validity mandate; novelty →
  trust-chain; the MPRP discovery lever added.
- **Roadmap T8 updated:** infinite-order is **Q.E.D.-reachable via a recurrence bridge lemma** (not Observatory);
  the **MPRP is the discovery-shaped increment**; novelty = trust chain; BM-2 caveat.
- **Conjecture bank updated:** BM-2 retraction recorded; the honest-negative (impossible-on-stationary) noted.
- **Not adopted:** dropping the MCR anchor entirely (Qwen) — kept as *one application*, not the frame (MiniMax's
  softer version); Gemini's "profound discovery EV" (outlier vs. 6 reviewers) and its speculative
  `hex-determinant-mathlib` scaling claim (unverified library) — flagged, not banked.

# Beyond-Markov conjecture round — vetted set (2026-07-03)

**What.** An internal ideation + adversarial-vetting round for a candidate new certificate domain: exact-rational,
kernel-checkable certificates that a stochastic process is *beyond every finite-order Markov model*. Motivated by
the MCR whitepaper audit (a bigram counter; P3 error floor; P8's exponential Σ^k steelman). Method: 5 mathematical
lenses proposed conjectures (high effort), then each was adversarially vetted for **(a) actually-beyond-Markov,
(b) exact-rational kernel/Z3-checkable, (c) novel-vs-textbook**. **Result: 15 proposed, 11 kept, 3 killed, 1 lost
to a tool error.** This doc banks the set; the external-review brief is
`docs/briefs/beyond-markov-external-brief-2026-07-03.md`; the roadmap position is T8 in
`docs/capability-roadmap-2026-07-03.md`.

## The reframe (the load-bearing idea)

Markov *order* is the wrong invariant; the **Hankel-matrix rank** `H[u,v]=P(uv)` (the prediction-state dimension)
is right. Order-k Markov ⊊ finite-Hankel-rank (= HMM/OOM/PSR/WFA). A process can have **infinite Markov order yet
finite Hankel rank**; the MCR-P3 process is a **rank-2** such process. Beyond-Markov, made kernel-checkable, is a
**determinant fact** — the same exact-rational-minor machinery the code work already runs (`bareiss_minors`,
`ldltOK`).

## Kept conjectures (11), by certificate shape

All statements verified by the vetter with exact rationals; each reuses or lightly extends existing machinery.

**A. Rank-r ∧ infinite/high order separations (the flagship family — convergent across 3 lenses).**
- **BM-1** rank(H)=2 ∧ order>K on the symmetric 2-mode HMM (q=3/4, e=1/8): a 2×2 minor det≠0 (3/32→int 96), all
  four 3×3 minors of a 4×4 block =0 (on-window rank≤2), and K per-depth 2×2 dets≠0 (order>K). Reuses
  `bareiss_minors` (flip `>0→≠0`) + a trivial new integer-matmul-equality checker.
- **BM(mcr) block-mode / de-Finetti / permanent-mode** variants: same rank-2 minor shape; the de-Finetti mixture
  adds an exact `Err_k` ladder (Err₀=1/2, Err₁=Err₂=3/8, Err₃=Err₄=21/64, …, `Err_k>1/4 ∀k`, →1/4).
- **VLMC leaf-count / causal-state lower bound** via one nonsingular r×r context-tree/Gram minor.
- **Matched PSD-Gram realizability** certificate (integer-LDLᵀ, `ldltOK` form) for the r-dim future-conditional Gram.

**B. The bigram-invisible gap (the sharpest "MCR can't see it").**
- **BM-2** an explicit dim-3 OOM whose bigram matrix `B` has **rank 1** (`det B=0`, consecutive symbols
  independent — the exact regime a first-order counter inhabits) yet `rank(H)≥3` (nonsingular 3×3 Hankel minor).
  Two `decide` facts on one process; provably invisible to any pairwise statistic, provably not first-order.

**C. Error-floor / excess-loss (quantified impossibility).**
- **BM-3** rank-r minor ∧ **Z3-UNSAT** error floor `∀g: E[err(g)]≥1/3` over the order-1 simplex. Half is already
  GREEN (`mcr_audit_artifacts.py:88 p3_z3_floor_proven`); the increment is the ∀-over-simplex quantifier.
- **BM-4** even process, Gini loss: exact closed-form `g_k=(1/9)(1/2)^{⌊k/2⌋}·{1 even, 3/4 odd}` (verified
  k=0..10; `g_{k+2}=g_k/2`); per-order rational identities are Q.E.D.-reachable, `g_k>0 ∀k` is the symbolic limit.

## Killed (3) — why the filter is real

- **Order-1 > rank-2 strict separation (mcr lens):** KILL — arithmetically sound but semantically mislabeled;
  fact-check showed `Err_1=Err_2=13/32` (order-1 *saturates* last-symbol info), so the relabel destroys the
  beyond-Markov claim.
- **Pythagorean/Brier tightness (learning lens):** KILL as a conjecture (salvage as tooling) — it's the
  orthogonality principle (Bayes-Brier risk = Σ P(c)μ_c(1−μ_c)), textbook and **not** beyond-Markov.
- **PSD-Gram dimension≥2 (information lens):** folded into the rank-certificate family (a restatement of the same
  rank-2 fact via a Gram LDLᵀ).

## Honest conclusion (the standing claim)

The **mathematics is textbook** — nearest prior art: Blackwell–Koopmans (1957), Carlyle–Paz (1971), Fliess
(1974), Jaeger OOMs (2000), Littman–Sutton–Singh PSRs (2001), Crutchfield–Shalizi ε-machines, Hsu–Kakade–Zhang
spectral, Rissanen context-trees. The even process is *their* canonical infinite-order/finite-complexity example.
**The potential novelty is the certificate object / first kernel-attestation, not the theorem.** Two honest
ceilings the vetter pinned: (1) K finite minors prove *order>K*, not infinite order — infinite order needs a
symbolic induction (Observatory-tier, not `decide`); (2) a finite window certifies a rank *lower* bound and an
on-window *upper* bound, but true minimality over the infinite Hankel is Observatory-tier. Whether any
beyond-Markov separation is *genuinely open* (discovery, not amplification) is the open EV question put to the
external round.

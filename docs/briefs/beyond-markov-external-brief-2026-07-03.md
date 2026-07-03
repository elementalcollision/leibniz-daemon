# External review brief — *Beyond Markov*: kernel-attestable process-complexity certificates

**For circulation to external agents/reviewers. Self-contained.** We are the Leibniz theorem-daemon. This
brief asks for feedback on a candidate new **domain** for our certificate architecture: exact-rational,
machine-checkable certificates that a stochastic process lives *beyond* every finite-order Markov model. It is
anchored on our recent formal audit of the "MCR" whitepaper (a bigram Markov counter claimed to be a "universal
processor / path to AGI"), and on an internal adversarial vetting round (15 conjectures proposed across 5
mathematical lenses, **11 kept** after a novelty/checkability filter). We want you to attack the strongest cases.

---

## 0. The constraint that makes a conjecture useful to us (read this first)

Leibniz is unusual: **LLMs only propose; the decision is made solely by the Lean 4 kernel, Z3, or an
exact-rational decision procedure.** A conjecture is only actionable for us if its certificate is **finite and
exact-rational** — an integer/rational matrix identity the kernel can settle by `decide`, or a Z3-UNSAT of a
rational-arithmetic negation. Anything requiring reals, limits, or an undecidable step is not kernel-attestable
(it can at most be an "Observatory-tier" record, never a Q.E.D.). Please judge every conjecture against *that*
bar, not against general mathematical interest. Our existing machinery you can assume: fraction-free (Bareiss)
integer minors and `det ≠ 0` / `det = 0` checks; integer-LDLᵀ PSD certificates; Z3-UNSAT over exact rationals.

## 1. The anchor and the reframe

The MCR apparatus is a **first-order (bigram) Markov frequency counter**. Our flagship refutation (verified,
Z3): on a hidden-2-mode block process it has a strictly positive, **sample-size-independent** prediction-error
floor `min(q, 1−q)` — the context isn't in the order-1 state. The paper's own steelman "rescues" this by
augmenting the state to Σ^k, at cost **|Σ|^k — exponential in context depth**.

That exponential is an artifact of the wrong yardstick. **Markov *order* is not the invariant; the *rank of the
Hankel matrix* `H[u,v] = P(uv)` — the dimension of the prediction-state space — is.** Order-k Markov is a
*strict* subclass of finite-Hankel-rank processes (= HMM / Observable-Operator-Model / Predictive-State-
Representation / weighted finite automaton). A process can have **infinite Markov order yet finite Hankel rank**.
The MCR process is exactly that: infinite raw-symbol order, but a **2-state** HMM — so the Σ^k escape is the
*weak* (exponential) one and a **rank-r PSR is the strong (constant-size)** one. Beyond-Markov, made precise, is
"finite Hankel rank, unbounded order" — and, crucially for us, the separation is a **determinant fact**.

## 2. The vetted conjectures (our strongest cases — please attack them)

Four featured; each verified by us with exact rationals; each maps onto machinery we already run. `H[u,v]` is the
string-Hankel matrix; "clear denominators" = scale to an integer matrix so the kernel checks an integer det.

**BM-1 — The rank-2 / infinite-order separation (convergent; 3 lenses independently produced it).**
Fix the symmetric 2-mode HMM (hidden transition `[[1−e,e],[e,1−e]]`, `P(0|A)=q`, `P(0|B)=1−q`; e.g. `q=3/4,
e=1/8`). Certificate = **three exact-integer facts on one process**: (i) `rank(H) ≥ 2` via a 2×2 Hankel minor
with `det ≠ 0` (raw `3/32` → integer det `96`); (ii) `rank(H) ≤ 2` *on a window* via all four 3×3 minors of a
4×4 Hankel block `= 0` (cleared to a common integer scale); (iii) for each `k ≤ K`, a 2×2 integer determinant
`≠ 0` on the pasts `0·0^k` vs `1·0^k` (same k-suffix, different next-symbol) → **order > K**. Reuses
`bareiss_minors` with the check flipped `>0 → ≠0`, plus a trivial new integer-matmul-equality checker for the
rank-r factorization.
> **Honest caveat we want you to weigh:** (iii) as `K` finite minors proves *order > K*, **not infinite order**.
> The closed form (the raw determinant numerator is a *constant* independent of k; equivalently the de-Finetti
> variant has `Err_k > 1/4` for all k) proves infinite order — but that needs a one-line *symbolic induction*,
> which is beyond a kernel `decide`. So the honest kernel artifact is "rank = 2 **and** order > K"; "infinite
> order" is an Observatory-tier symbolic addendum. **Is there a finite exact-rational certificate for infinite
> order that we're missing?**

**BM-2 — A rank gap invisible to the bigram spectrum (the sharpest "MCR can't see it").**
An explicit dimension-3 OOM whose **bigram matrix `B[a,b]=P(x_t=a,x_{t+1}=b)` has rank 1** (consecutive symbols
independent — the *exact* regime a first-order/bigram counter inhabits) **yet whose word-Hankel matrix has a
nonsingular 3×3 minor**, so `rank(H) ≥ 3`. Verified witness: `B = outer(p,p)`, `det B = 0`; an explicit
nonsingular 3×3 Hankel minor. Two exact-rational `decide` facts: `det B = 0` (rank-1 bigram) **and** a 3×3
integer minor `≠ 0`. (We do **not** claim minimality = 3 in the finite certificate — only the lower bound.)
This is the crispest object: *provably invisible to every pairwise/bigram statistic, provably not first-order.*

**BM-3 — The error-floor sandwich (half of it is already GREEN in our repo).**
Pair a nonsingular Hankel minor (rank ≥ r) with an **exact error-floor lower bound**: for the task "predict
`x_{t+1}` from the order-1 state," `E[err(g)] ≥ 1/3` for **every** order-1 stochastic predictor `g` on the
simplex, as a **Z3-UNSAT** of `∃g: E[err(g)] < 1/3` over rational linear arithmetic. Our `p3_z3_floor_proven()`
already discharges the pinned-argmax version; the increment is the ∀-over-the-simplex quantifier. The pair
(dimension lower bound ∧ error floor) is a self-contained "class-M-cannot, rank-r-can" certificate.

**BM-4 — The quantified excess-loss curve (a *closed-form* separation).**
For the canonical **even process** (the textbook infinite-order / finite-complexity ε-machine; operators
`T0=[[1/2,0],[0,0]]`, `T1=[[0,1/2],[1,0]]`, `π=[2/3,1/3]`), under Gini/quadratic predictive loss: the
causal-state predictor achieves `L* = 1/3`, and the best order-k predictor achieves `L(k) = 1/3 + g_k` with the
**exact rational** `g_k = (1/9)(1/2)^{⌊k/2⌋}·{1 if k even, 3/4 if k odd}` (verified k=0..10; two-step recurrence
`g_{k+2}=g_k/2`). Each per-order identity + strict positivity is a Q.E.D.-reachable rational fact; `g_k>0 ∀k`
(the full separation) is the symbolic-limit addendum.

The other 7 kept conjectures (VLMC leaf-count lower bounds via a nonsingular context-tree block; a matched
PSD-Gram realizability certificate; a de-Finetti/permanent-mode instance with an exact `Err_k` ladder; the
period-3 random-phase witness; etc.) share these shapes and are available on request.

## 3. Our own honesty position (so you attack the real claim, not a strawman)

We assess **the mathematics as textbook** and **the novelty as the certificate object / first
kernel-attestation**, not the theorem. Nearest prior art we are aware of, named: **Blackwell–Koopmans (1957)**
(Hankel/moment rank of HMMs), **Carlyle–Paz (1971)** and **Fliess (1974)** (Hankel rank = minimal linear
representation), **Jaeger (2000)** (OOMs), **Littman–Sutton–Singh (2001)** (PSRs), **Crutchfield–Shalizi**
(ε-machines / statistical complexity — the even process is *their* canonical example), **Hsu–Kakade–Zhang**
(spectral HMM learning), **Rissanen** (context trees). We are **not** claiming new mathematics. We are claiming a
new *checkable certificate family* our architecture can uniquely attest, and we want to know if even *that*
narrow claim survives.

## 4. What we're asking (the review)

1. **Certificate novelty.** Is a *kernel-attested exact-rational Hankel-rank / Markov-order separation* published
   anywhere (any proof assistant — Lean/Coq/Isabelle formalizations of WFA Hankel rank, PSR, ε-machines)? Is the
   "rank-r ∧ order>K as simultaneous integer minors on one process" object new *as a formal certificate*, or is
   it a restatement of an existing mechanized result? **Kill-shots welcome — point at the paper.**
2. **The sharpest witness.** Which instance best dramatizes "beyond bigram/Markov" — BM-2 (bigram-invisible
   rank-3), the even process (BM-4), the de-Finetti mixture? Is there a *smaller* or *more canonical* witness we
   should feature instead?
3. **The infinite-order upgrade.** Can "infinite Markov order" be made a **finite** kernel-`decide` certificate
   (a single algebraic identity), avoiding the symbolic induction — or is Observatory-tier the honest ceiling?
4. **Discovery vs. amplification (the EV question).** Is there a beyond-Markov **separation or lower bound that
   is genuinely open** (not folklore) *and* certificate-shaped — a place a machine could attest something *new*,
   not re-attest textbook facts? This is the make-or-break for whether this is a discovery track or another
   verification-amplification asset.
5. **Soundness of the shapes.** Do any of BM-1..4 smuggle in a step that is *not* exact-rational/decidable
   (a hidden real, a limit, an undecidable equality)? We flagged the ones we found (BM-1(iii), minimality
   claims); tell us the ones we missed.

## 5. Framing and provenance

- **Scope.** This brief concerns the *mathematical, kernel-checkable* conjectures only (the "develop the theory
  and turn it into checkable targets" reading). A separate, unrelated question — whether the daemon's *own
  discovery search* is near-Markovian and should be made history-dependent — is **out of scope here**.
- **Trust boundary.** Nothing in this program edits the trust core; every certificate above is audit/Observatory
  tier unless and until a bridge theorem is discharged. `tests/test_invariants.py` stays byte-identical.
- **Position on the roadmap.** This is track **T8** of the auditable capability roadmap
  (`docs/capability-roadmap-2026-07-03.md`) — the first genuinely new *domain* for the certificate architecture
  since covering designs, and (unlike the code tables) one whose impossibility band may not be human-saturated.
- **Transmission** is the operator's channel; reviewers reply through the operator. Every claim above is backed
  by an exact-rational computation we can share on request.

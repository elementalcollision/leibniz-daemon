# External-Agent Guidance Brief — Schrijver Three-Point (Terwilliger) Bound for Binary Codes

**Audience:** experts in semidefinite bounds for codes / the Terwilliger algebra of the binary Hamming scheme.
**What we need from you:** a *correct and reachable* recipe, not a soundness argument. Soundness is already kernel-protected in our system (details in §0). A wrong formulation, wrong block, or wrong sign convention simply fails the Lean-kernel check and is discarded — it can never yield a false bound. So please optimize your answer for **correctness and computational reach**, and be explicit about conventions and pitfalls.

---

## 0. Context you can rely on (already built and self-validated)

We are Leibniz, a theorem daemon whose invariant is: *producers propose, only mechanical checkers decide.* For PSD bounds this means an untrusted SDP solver proposes a dual certificate, and the **Lean 4.31 kernel** checks an exact **integer** identity. Four pieces are validated end-to-end (measured, not intended):

1. **Exact-PSD integer certificate (`scripts/psd_certificate_microprobe.py`).** A producer supplies integer lower-triangular `L`, integer diagonal `d >= 0`, and integer `scale` with `L·diag(d)·Lᵀ == scale·M`. The kernel checker `ldltOK` verifies an *integer matrix identity plus a sign check* — no eigenvalues, no `decide`-wall. This is the object every block certificate must reduce to. **Reuse `ldlt`, `clear_denoms`, `verify_int_cert`, `render_ldlt_lean` verbatim.**
2. **Irrational-optimum rounding (`scripts/irrationality_margin_test.py`).** On genuinely irrational SDP optima (ϑ(C₅)=√5) a rational PSD cert floors to the correct integer with tax ~0.002, via **Strict-PD (+ exact εI) rational Cholesky with NO pivoting**. This is how we get from a float solver point to an exact rational feasible point.
3. **Bounded bit-length (`scripts/bareiss_ldlt.py`).** Naive whole-matrix-LCM rational Cholesky explodes (944 bits at n=6 → 30773 at n=30). Bareiss / fraction-free elimination replaces the scale with an LCM of *adjacent leading-principal-minor products* (Hadamard-bounded), measured ~2.8× smaller at n=30. Required at scale.
4. **Full-graph code SDP → kernel pipeline (`scripts/sdp_code_bound.py`).** Untrusted SCS solve of a dual Lovász-ϑ SDP on real confusability graphs → rational rounding → integer PSD cert → kernel check → floor, GREEN and reproducing A(4,2)=8, A(4,4)=2, A(5,2)=16. **Measured wall:** the kernel PSD checker is walled by matrix *dimension*, not bit-length — an N=64 (n=6) cert times out even at `maxHeartbeats 0`; N=32 checks in ~20s. **This is the single most important constraint for the three-point build** (see §5, Q3).

We have already extracted Schrijver's paper (§1 restates it). We are **not** asking you to re-derive it; we are asking you to (a) confirm/correct our reading, (b) tell us the certificate-per-block composition, (c) pick the smallest reproduction cell that fits under our kernel dimension wall, and (d) warn us about conditioning and convention traps.

---

## 1. The formulation as we currently read it (please confirm or correct)

Source: A. Schrijver, *New code upper bounds from the Terwilliger algebra and semidefinite programming*, IEEE Trans. Inf. Theory 51(8), 2005 (author copy: `homepages.cwi.nl/~lex/files/codes.pdf`). Equation numbers below are Schrijver's.

- **Terwilliger algebra basis.** Matrices `M^t_{i,j}` on `P = 2^{[n]}`, with `(M^t_{i,j})_{X,Y}=1` iff `|X|=i, |Y|=j, |X∩Y|=t`; nonzero only when `0 <= t <= i,j` and `i+j-t <= n`. `dim A_n = binom(n+3,3)`.
- **Block-diagonalization (Thm 1).** `A_n ≅ ⨁_{k=0}^{⌊n/2⌋} C^{N_k×N_k}` with block order `p_k = n-2k+1` and multiplicity `q_k = binom(n,k) - binom(n,k-1)`. Block `k` is the `(n-2k+1)×(n-2k+1)` matrix indexed by `i,j ∈ {k,…,n-k}`.
- **Integer block coefficients (eq. 7).**
  `β^t_{i,j,k} = Σ_u (-1)^{u-t} binom(t,u) binom(n-2k, u-k) binom(n-k-u, i-u) binom(n-k-u, j-u)`.
- **CRITICAL — entries are RATIONAL/INTEGER, not irrational.** Schrijver's eq. (8) carries a normalization factor `binom(n-2k, i-k)^{-1/2} binom(n-2k, j-k)^{-1/2}` with square roots, but he **explicitly deletes it** ("We have deleted the factor … as it makes the coefficients integer, while positive semidefiniteness is maintained"). So the reduced block, as an affine form in the variables, has **integer** coefficients `β^t_{i,j,k}`:
  block `k` entry `(i,j) = Σ_t β^t_{i,j,k} · x^t_{i,j}`.
  This is decisive for us: PSD is a congruence-invariant, so we can work with the integer-coefficient blocks and never touch a square root. The only irrationality is in the *optimal value* `t*` of the SDP, which is exactly the case #214 already handles.
- **The SDP (eqs. 19, 20, 22).** Maximize `Σ_i binom(n,i) x^0_{i,0}` subject to:
  - (19) For each `k`: the block `(Σ_t β^t_{i,j,k} x^t_{i,j})_{i,j=k}^{n-k}` is PSD, **and** the block `(Σ_t β^t_{i,j,k} (x^0_{i+j-2t,0} - x^t_{i,j}))_{i,j}` is PSD (two block families, from R and R').
  - (20)(i) `x^0_{0,0}=1`; (ii) `0 <= x^t_{i,j} <= x^0_{i,0}` and `x^0_{i,0}+x^0_{j,0} <= 1+x^t_{i,j}`; (iii) symmetry `x^t_{i,j}=x^{t'}_{i',j'}` when `(i',j',i'+j'-2t')` is a permutation of `(i,j,i+j-2t)`; (iv) distance: `x^t_{i,j}=0` if `{i,j,i+j-2t} ∩ {1,…,d-1} ≠ ∅`.
  - Variable reduction: for even `d`, set `x^t_{i,j}=0` when `i` or `j` is odd.
- **Why it beats Delsarte.** The Delsarte LP is the `k=0`/Bose-Mesner sub-case (eq. 23) — the diagonal restriction of this SDP. Extra PSD blocks `k>=1` are the "three-point" strengthening.

**Please confirm:** the two-block-family structure (R and R'), the exact index ranges, and that (20)(ii)/(iii)/(iv) are the complete linear constraint set. If you know a cleaner equivalent formulation (e.g. Gijswijt–Mittelmann–Schrijver's reduced variable set, or the symmetric-Jordan-basis construction of Brouwer–Polak/Val­lentin) that produces smaller or better-conditioned blocks, tell us which and why.

---

## 2. (a) The block-diagonalization we will implement — what we need pinned down

We will compute, in exact integer arithmetic (Python `fractions`/`int`), for given `n, d`:

1. the coefficient tensor `β^t_{i,j,k}` from eq. (7) (a nested integer sum of products of four binomials — we will build binomials via Pascal, exactly);
2. the reduced blocks as integer-coefficient affine forms in the free variables `x^t_{i,j}` after applying constraints (20)(iii)/(iv) to collapse symmetric/zero variables.

**Questions for you (Q-block):**
- Q-block-1: Confirm the summation index range for `u` in eq. (7) and any implicit `binom(a,b)=0 for b<0 or b>a` conventions (we will use the standard "0 outside range").
- Q-block-2: Confirm that block `k` rows/cols are indexed by `i,j ∈ {k,…,n-k}` (size `n-2k+1`), and that the diagonal `k=0` block reproduces the Delsarte/Krawtchouk LP exactly (a check we will run as a regression).
- Q-block-3: Is there a published *numeric* dump of a small block (say all `β^t_{i,j,k}` for `n=6` or `n=8`) we can diff our generator against? A single trustworthy small table would let us validate the generator before scaling. If not, state the one or two entries you are most confident of as anchors.

---

## 3. (b) Dual certificate per block that composes into a sound upper bound

Our soundness rests on a **dual** certificate: a nonnegative combination of the constraints that yields an upper bound `A(n,d) <= floor(t)` provable by exhibiting, per block, a PSD matrix the kernel can check. We need the dual made explicit.

Concretely, the primal maximizes `Σ_i binom(n,i) x^0_{i,0}`. The dual assigns:
- a PSD dual matrix `Z_k^{(1)}, Z_k^{(2)}` (one per block family, per `k`) to each block PSD constraint (19),
- nonnegative multipliers to the inequality constraints (20)(ii), and free multipliers to the equalities (20)(i)(iii)(iv),
such that the dual objective (a single scalar `t`) upper-bounds the primal, and complementary/feasibility reduces to: **each `Z_k^{(*)}` is PSD** (checked by our integer `ldltOK`) **plus one exact rational scalar identity** linking `t`, the multipliers, and the `β` tensor.

**Questions for you (Q-dual):**
- Q-dual-1: Write the dual SDP of (19)+(20)+(22) explicitly, or point to a reference that does. We specifically need: which dual objects must be PSD (so we can hand each to `ldltOK` independently), and the single linear identity that ties them to the bound `t`. We want the check to factor as *(a set of per-block integer PSD certs) AND (one integer/rational linear identity)* — mirroring how `sdp_code_bound.py` already composes "block PSD + `floor(t)`".
- Q-dual-2: Confirm that the bound composes **additively over blocks** — i.e. the kernel can check each `Z_k` separately (dimension `n-2k+1`, small) and then a scalar aggregation, rather than needing one giant PSD check. This is what makes the dimension wall (§5) survivable: the *largest* block is `k=0` at size `n+1`, not the `2^n` full graph. Please confirm the largest object the kernel must PSD-check is `(n+1)×(n+1)`, which for A(12,5)-scale is ~13×13 — trivially inside our wall.
- Q-dual-3: The rounding step (#214) perturbs the dual `Z_k` to strict-PD by adding `εI` and re-solving exactly. Adding `εI` to a *dual* matrix weakens the bound slightly (the ~0.002 tax). Confirm that a small strict-PD margin on each `Z_k` preserves a *valid* (if slightly worse) upper bound, and that `ceil`/`floor` on the aggregated `t` still lands on the integer bound at the cells in §4. If the dual has an exact rational optimum at these cells (it may, given integer `β`), say so — that would let us skip the margin entirely.

---

## 4. (c) Smallest cell where three-point strictly beats LP — reproduction target + expected margin

From Schrijver's Table I and constant-weight table, the candidate small targets are:

| target | Delsarte LP | Schrijver SDP | notes |
|---|---|---|---|
| **A(19,6)** | 1289 | **1280** | smallest *unrestricted* `A(n,d)` cell with a strict improvement in Table I |
| A(20,8) | 290 | 274 | larger gap, larger `n` |
| A(17,6,7) (constant weight) | 249 | **228** | constant-weight variant — *smaller* SDP (weights fixed), often the cheapest first win |
| A(12,5) | — | — | prompt's illustrative "40→32" target — please confirm the actual LP and SDP values here; we could not find A(12,5)=32 in Schrijver's tables and suspect the prompt's numbers are illustrative |

**Questions for you (Q-cell):**
- Q-cell-1: **Which single cell is the cheapest genuine strict improvement to reproduce first?** Our binding cost is the *number of free variables* `x^t_{i,j}` (≈ `binom(n+3,3)` before symmetry reduction) driving SCS conditioning, and the *bit-length* of the resulting integer cert. We suspect **A(17,6,7) constant-weight** (fewest variables, well-documented 249→228) or **A(19,6)** (Schrijver's own first unrestricted entry). Please rank 2–3 cells by expected build difficulty and confirm the exact (LP, SDP) integer pair for each, with a citable source.
- Q-cell-2: Please **verify or correct the A(12,5) "40→32" claim** in our prompt. If it is not a real strict-improvement cell, we will drop it. If it is (e.g. via a later split-Terwilliger refinement, Springer DCC 2023, arXiv:2203.06568), give the citation and the actual numbers.
- Q-cell-3: **Expected irrationality margin.** At the chosen cell, do you expect the SDP optimum `t*` to be irrational (algebraic degree > 1), or rational? If irrational, roughly how far above the integer bound does it sit (analogue of ϑ(C₅)=√5 → floor 2 with tax 0.002)? This tells us whether the #214 margin machinery is exercised or trivially satisfied, and how fine a rational grid the rounding needs.

---

## 5. (d) Pitfalls — conditioning, signs, indexing, reach

**Questions for you (Q-pit):**
- Q-pit-1 (**dimension wall — most important**): We measured that our kernel PSD checker walls out around matrix dimension N≈32–64 (List-indexed `matmul` is ~O(N⁴) in kernel reduction). The three-point method's saving grace is that **after** block-diagonalization the largest matrix is `(n+1)×(n+1)` (the `k=0` block), ~13×13 at A(12,5) scale, far under the wall — *provided the dual certificate is checked block-by-block, never on the `2^n` ambient space.* Please confirm nothing in the sound dual forces a check on an object larger than the largest block. If any aggregation step needs a matrix bigger than `n+1`, flag it now — that would be a build-killer we must know about before starting.
- Q-pit-2 (SCS conditioning on reduced blocks): The reduced SDP has many tiny blocks with widely varying scales (the `β` coefficients span several orders of magnitude via the binomial products). Do you recommend scaling/normalizing blocks before handing them to SCS/CLARABEL? Any known conditioning traps (e.g. near-rank-deficient blocks at the optimum that make float→rational rounding fragile)? We use `eps=1e-7`; is that enough, or is a higher-precision solver (SDPA-GMP-style) effectively required to get a float point close enough to round exactly?
- Q-pit-3 (sign/indexing conventions): The two block families come from R (from C) and R' (from the complement). Sign errors between the `x^t_{i,j}` and `(x^0_{i+j-2t,0} - x^t_{i,j})` families are the classic bug. State the exact sign/orientation convention you recommend, and confirm whether the `binom(n,i)` objective weight uses `i` = the diagonal index `x^0_{i,0}` (weight = number of codewords of "distance-from-∅" `i`). Also confirm the permutation rule (20)(iii) canonicalization we should use to deduplicate variables.
- Q-pit-4 (constraint completeness): Is Schrijver's (19)+(20) the full constraint set, or do the stronger later results (split Terwilliger, arXiv:2203.06568; Litjens–Polak–Schrijver refinements) add constraints that are *necessary to actually achieve* the improved bound at our target cell? I.e. does reproducing 249→228 need only the 2005 formulation, or a later strengthening? We want to build the *minimal* formulation that achieves a strict LP improvement.
- Q-pit-5 (kernel-checkability of the dual identity): Beyond the per-block PSD checks, the scalar aggregation identity must be an *exact rational* identity (integer after clearing denominators) so the kernel can verify it by arithmetic. Confirm no transcendental/√ enters the aggregation (given integer `β`, it should not) — if it does, name where, so we can push it into the "strict-PD margin" bucket rather than the exact-identity bucket.

---

## 6. Deliverable shape we can act on

The most useful reply is, in order of value: (1) confirm/correct §1 (especially the integer-coefficient claim and the two-block-family structure); (2) the explicit dual (§3, Q-dual-1/2) — even a reference that writes it out; (3) a ranked 2–3 cell list with exact (LP, SDP) integers and citations (§4); (4) the dimension-wall confirmation (Q-pit-1) and conditioning guidance (Q-pit-2). Anything you are unsure of, mark as such — we would rather build against three confirmed facts than five guessed ones, because every guess costs us a kernel-check round-trip to falsify.

**Reminder on soundness:** you cannot make us accept a false bound. If your formulation is wrong, the integer certificate fails `ldltOK` or the aggregation identity fails, and we quarantine the candidate. So please be aggressive about *reach* (biggest cell we can hope to reach, cheapest first win) and precise about *conventions*; do not spend effort reassuring us about correctness-of-final-answer — the kernel owns that.
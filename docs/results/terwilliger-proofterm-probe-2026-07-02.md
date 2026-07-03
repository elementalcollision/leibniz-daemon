<!--
Proof-term probe — can a non-decide encoding break the kernel-PSD ceiling? Decisive result: NO, the wall is
fundamental to the trust model. Audit/measurement only; no trust surface touched; invariants byte-identical.
-->

# Proof-term probe — the kernel-PSD ceiling is fundamental, not an engineering gap (2026-07-02)

The low-rank primitive pushed the kernel-PSD ceiling to ~N=60. This probe asked the frontier question: can a
**proof term instead of `decide`** — encoding the PSD identity as flat `Int`/`Nat` arithmetic to hit the
kernel's fast bignum path, rather than reducing a `List` matmul — break the wall? **Answer: no. It is worse,
and the wall is a property of the trust model.**

## Measured (leibniz-lean-repl v4.31.0, `maxHeartbeats 0`)

| test | result | meaning |
|---|---|---|
| flat unrolled PSD check, N=40 | **timeout (>200s)** | vs compact `List`-def form: N=40 in 20s, N=60 in 89s — flat is *worse* |
| `decide` on one flat sum of K products | K=200→**1.4s**, K=1000→**30s**, K=4000→**timeout** | ~**O(K²)**: 5× more terms → 21× slower |
| Nat vs Int scalar reduction | 0.8 vs 1.4s; 24 vs 30s | Nat acceleration is **marginal** — NOT the lever |
| 1600 trivial conjuncts, nothing else | **timeout** | **term size** is the killer, independent of per-op cost |

## Why the "proof-term" avenue fails — and why it closes the question

`decide` builds and reduces a `Decidable` instance over the *entire* proposition; that cost is **~quadratic in
total term size**. The compact `List`-`def` form (shipped `lowRankOK`) is *good* precisely because the `def`
bodies keep the source term small and the kernel reuses reduction inside them — it does not unroll. Any
"proof-term" that spells out the N²·r scalar operations blows the term size straight into the O(term²) regime
and times out earlier (N=40) than the compact form (N=60). Nat vs Int does not change the order. **There is no
encoding trick that beats the compact low-rank `def` form** — it is the practical frontier of `decide`-based
kernel PSD certification.

## The real conclusion: this is a trust-boundary property, not a bug

The ~N=60 ceiling is fundamental to Leibniz's trust model: **the kernel must reduce the certificate, and
`native_decide` is forbidden** (it would trust the compiler, not the kernel — CLAUDE.md invariant). Exact
in-kernel recomputation of an N-scale matmul has irreducible term size; `decide`'s cost on it is superlinear.
The only ways past N≫60 all **leave the model**, so none is an engineering probe — each is an operator/charter
decision:

1. **`native_decide`** for PSD blocks — compiler-evaluated, orders of magnitude faster, but trusts the Lean
   compiler + `Nat`/`Array` runtime. Forbidden by the charter as written; would need an explicit new trust tier
   + ADR (the F2c-style gate).
2. **An external verified PSD checker** (verified Cholesky / ValidSDP / a reflection-based checker) whose own
   soundness is proved once — moves the per-cert trust off the kernel onto that proof. Also a new trust tier.
3. **A mathematically cheaper certificate** needing asymptotically fewer kernel ops — the research survey
   (Gershgorin/congruence, Schur recursion, SOS/Positivstellensatz, sparse Cholesky) found **none** that wins
   without re-introducing an O(N³) step or an NP-hard decomposition.

## Net for "the best solver possible"

The achievable frontier is now **fully mapped**: the low-rank Gram primitive (shipped, PR #247) is the best
*sound, kernel-reducing, no-new-trust* PSD certificate — ~2× the ceiling of the old full-rank checker + smaller
bit-length. Beyond ~N=60, kernel-PSD certification is **not an engineering problem** — it is a trust-model
boundary. Pushing it further is a deliberate charter decision (admit `native_decide` or an external verified
checker as a new tier, with its own ADR + witness round), not more solver cleverness. Recording that boundary —
so no further effort is spent trying to scale kernel-PSD by encoding — is this probe's contribution.

Harness: `scripts/terwilliger_decide_probe.py` (`docs/results/terwilliger_decide_probe.json`). Related:
`docs/results/terwilliger-psd-primitive-2026-07-02.md` (the low-rank primitive + ceiling study),
`docs/results/terwilliger-gms-gate0-2026-07-02.md` (why large blocks are needed at all).

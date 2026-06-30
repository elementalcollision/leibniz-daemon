<!--
Gate B2 measure-before-build finding: the Ramsey kernel-`decide` cost wall. Decision-determining for the
Ramsey amplification domain (Track B2). No trust-boundary change.
-->

# Gate B2 — the Ramsey kernel-`decide` wall (frontier needs certificates, not `decide`)

**Status:** measured, 2026-06-30. Before building a Ramsey amplification verifier (Gate B0's
BUILD-CANDIDATE #2), the kernel-check cost was measured. **Finding:** the sound kernel check via Lean
`decide` is tractable only for *toy* n; at frontier sizes it is intractable, because `decide` enumerates
naively (no pruning). A sound frontier-Ramsey verifier therefore needs a **verified-certificate
architecture**, not `decide`. B2 is *not* a cheap covering-like domain.

## What was measured
A Ramsey lower-bound witness for R(s,t)>n is a graph on n vertices with no s-clique and no t-independent
set. Rendered as a core-Lean `decide` theorem (`noClique ∧ noIndep`, enumerating subsets via `combs`),
verified on the real Lean 4.31 kernel:

| witness | subsets enumerated C(n,s)+C(n,t) | kernel |
|---|---|---|
| C₅ → R(3,3)>5 (n=5) | ~20 | **verified, 1.0 s** |
| frontier R(5,5)>42 (n=43, s=t=5) | C(43,5)≈**962,000** | intractable for `decide` |
| frontier R(6,6)>165 (n=165, s=t=6) | C(165,6)≈**2.6×10¹⁰** | hopeless |

The earlier Paley-graph timing (≤0.27 s at n=241) was a **Python branch-and-bound** max-clique, which
**prunes**; the Lean kernel's `decide` does **not** prune — it must reduce the full `.all` over every
subset. The VT (vertex-transitive) reduction lowers the count to C(⌊n/2⌋, s−1), but that still explodes
(C(120,6)≈5×10⁹ for Paley-241). So the fast check is *untrusted* (a search) and the *trusted* check
(`decide`) does not scale.

## Why this is the producer wall in a new guise
- The covering/CWC kernel checks were cheap because the predicate is a **finite, polynomial-size**
  computation on the witness (pairwise distance / t-subset coverage). Ramsey's predicate ("no clique of
  size s") is a **search** over C(n,s) subsets — exponential in s — so the naive kernel evaluation
  matches the brute-force search cost, with no pruning.
- A sound kernel verdict at frontier sizes requires either (a) a **proof term** that exploits the
  witness's structure (e.g. the difference-set / circulant algebra) — per-witness proof engineering, not
  mechanical; or (b) a **verified clique/independence certificate checker** in Lean (the DRAT/LRAT
  analogue) — a substantial, separate build. Both are the "certificate architecture."

## Disposition
- **The B2 *amplification* verifier is gated on a certificate architecture.** It is NOT buildable cheaply
  the way covering was. Frontier Ramsey witnesses cannot be soundly kernel-verified via `decide`.
- The **scoped framework that ships now** (`scripts/ramsey_verify.py`): the *untrusted* VT-reduced checker
  (the reusable proposer/checker), plus a `decide` render **hard-capped** to the toy regime (it REFUSES to
  emit an intractable kernel job). This keeps the audit-tier promise honest — it never asks the kernel to
  do the impossible.
- **Recommendation:** keep B2 at the toy regime until/unless an operator chooses to invest in the
  certificate architecture (its own ADR + measure-before-build). The covering domain remains the live
  amplification target; Ramsey's value (search-set records) is real but its *sound* kernel verification is
  the expensive part — which is itself a sharper restatement of the producer wall.

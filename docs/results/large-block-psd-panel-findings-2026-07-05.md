# Findings — external panel on the large-block PSD kernel-certification wall (2026-07-05)

**Brief:** `docs/briefs/large-block-psd-kernel-certification-brief-2026-07-05.md` · **Panel:** 5 expert lenses
(Lean-kernel internals · SDP/DSOS-SDSOS · formal-verification/ValidSDP · Delsarte–Terwilliger coding theory ·
adversarial charter guardian) + adversarial synthesis · **EV:** research scoping for a future ADR 0047 revisit
· **Tier:** docs-only (no code, no trust surface). **Verdict: BANK-AND-HOLD (unanimous) + one bounded probe.**

## The one fact that organizes everything

All five converge on the same reframing of the proof-term probe: **the wall is TERM COUNT, not bit size.**
`decide` cost is ~O(term²) in the number of *distinct scalar facts* the kernel must build and traverse;
"Nat(GMP) vs Int is only marginal" is the empirical tell. This **inverts** the problem — any approach that
makes the *arithmetic* cheaper (a naive read of A) optimizes the wrong variable. The only mechanical escapes
either **check a smaller object proved sound once** or **decompose so a monolithic O(N²) term blob is never
formed.**

## Consensus ranking (reach N=130–414 while staying MECHANICAL)

**C > A > D > F > B > E** (three of five lists match nearly exactly; outliers move only A↔C, B↔F).

| | Approach | Verdict |
|---|---|---|
| **#1** | **C** — verified checker, soundness proved once in Lean | Only candidate both charter-clean **and** with a path to scale (ADR 0047's pre-registered Option 3). **But it does not escape A — it inherits A's wall.** |
| **#2** | **A** — big-`Nat` GMP arithmetization | Not a standalone answer; it is **the evaluation engine C needs.** Naive packing re-expands on decode; only the CRT-congruence variant has a chance. |
| **#3** | **D** — deeper symmetry / block shrink | Charter-cleanest (pure representation theory, zero new trust); ranks middle on *efficacy doubt* — a proven 2–7× shrink to N≤60 for GMS blocks is unlikely. |
| **#4** | **F** — compact O(N²) proof term | The probe already disproved the flat route; no independent scaling story. |
| **#5** | **B** — DD/SDD (DSOS/SDSOS) cone | Charter-clean on *trust* but **claim-laundering risk**: SDSOS ⊊ PSD ⇒ a *strictly weaker* bound that may miss the integer floor; a known DSOS/SDSOS non-convergence result applies. |
| **#6** | **E** — `native_decide` tier | **Unanimous last** — overt charter breach (compiler + `Array`/`Nat` runtime into the TCB); its "differential re-check on sub-blocks" mitigation is circular. |

## C, dissected (the load-bearing finding)

C splits into two halves of very different difficulty:
- **Half 1 — soundness** (`checker M = true → M ⪰ 0`): **tractable, ~3–6 person-months.** Standard Mathlib
  (`Matrix.PosSemidef`, LDL/Cholesky scaffolding exist). *Not* the bottleneck.
- **Half 2 — efficient in-kernel evaluation on an N≈200 matrix: the crux, and genuine research risk.**
  Lean's kernel has **no `vm_compute`/`native_compute`**, so evaluating the proved checker is the *same*
  O(N²)-term reduction that walls out at ~60. **ValidSDP/CoqInterval's speed is categorically non-portable** —
  it rests on Coq's `native_compute` + hardware floats; reaching for that in Lean *is* `native_decide`
  (forbidden). So **C's evaluation leg is gated on A/CRT working.**

**Consensus cost for C: 9–18 person-months of expert Lean** (centre ~12–15; tail to 24+), **dominated by the
unsolved eval crux, not routine formalization.** The brief/ADR's "weeks" framing is an overclaim, corrected by
the panel. "Build C now" = funding open research, not engineering a known artifact.

## Best novel approaches (both attack term count, from opposite ends)

1. **(Best) Schur-complement tiling — certify UNDER the ceiling, don't raise it.** Decompose an order-414
   block via an LLM-proposed, **kernel-checked** block-Schur elimination into pivots each of order ≤60,
   certify each with the **existing `lowRankOK`**, and combine via a **once-proved Haynsworth inertia-
   additivity lemma** (`M ⪰ 0 ⟺ all pivots ⪰ 0`). Reuses the frontier primitive, imports **zero** new trust,
   never forms a monolithic O(N²) blob, and exploits GMS block structure (chordal/banded PSD-completion,
   Grone–Vandenberghe — exact and PSD-preserving). **Open risk (bounded, measurable):** exact-rational
   Schur-pivot bit-growth / fill-in. Could beat both A and C to the target at a fraction of the cost.
2. **(Runner-up) Derandomized-Freivalds / CRT congruence ("certificate of a certificate").** Verify
   `M = LᵀDL` by checking agreement at deterministic points mod a large prime (Vandermonde projection),
   collapsing the O(N²) identity to O(N) big-`Nat` modular ops on the GMP path, + a clean once-proved lemma
   ("degree-<N polynomial with N+1 agreeing evaluations is zero"). The honest realization of A; a C-internal.

## Charter audit — the guardrail to write into any future C-ADR verbatim

**"A soundness proof does not launder a compiled evaluator."**
- **E** — overt breach (dispreferred; keep forbidden absent an explicit witnessed tier).
- **C** — *most seductive hidden trap*: if the proved checker is evaluated via `native_compute` "for speed"
  (exactly how ValidSDP is fast), C silently becomes E with a fig leaf. **C is clean iff evaluated by
  `decide`+kernel on exact rationals/`Nat`s.**
- **A / CRT** — clean **iff** the kernel *recomputes/re-verifies* the packing (not a pasted external literal),
  and the lift magnitude bound + prime-adequacy inequality `∏pⱼ > 2·maxentry` are **kernel-discharged, not
  asserted** by the prover.
- **B** — no TCB leak but a *mathematical* overclaim (weaker bound presented as the SDP bound).
- **D**, Schur-tiling, in-kernel Freivalds/CRT — clean.

## Worth it? BANK-AND-HOLD (unanimous), with triggers

**HOLD is correct on the merits today**, not a hedge: ADR 0047's revisit trigger requires a large-block cell
that is (a) **not** in the published tables **and** (b) reachable by our float solve leg. GMS records are
**published**; the reachable cells are **DRY** (D1/D3). The intersection "novel ∧ reachable-by-us" is
currently **empty** — building a 9–18 PM checker would **re-certify the empty set.** But the wall is a genuine
trust-model property and the C+A(CRT) / Schur-tiling programs are coherent and charter-preserving, so **bank
the design** (not "never"). **Triggers that flip to GO (any one):** (i) a novel, float-solve-reachable,
unpublished large-block target appears (most plausibly a *new SDP-formulation family* from the discovery leg,
not GMS); (ii) Lean ships a trusted kernel compute path (proved bytecode evaluator / attested native tier);
(iii) the probe below shows a clean O(k)-term in-kernel path (lowers the GO bar, doesn't itself justify build).

## Recommended bounded probe (all five converged — measure, don't argue)

A **1–2 week, offline, no-trust-surface** spike (touches no `trust.py`/`verifiers.py`, mints nothing, needs no
ADR). It measures the two numbers that gate the whole program:

- **Probe 7a — term-count / re-expansion.** On a real order-60 GMS/Terwilliger block, test whether a k-prime
  **CRT congruence** (`M ≡ LᵀDL mod pⱼ`, residues as ground literals, ~8–12 machine primes) — or a single
  packed `Nat.mul + Nat.decEq` — verifies the LDLᵀ identity in **O(k) kernel-reduction terms** or re-expands
  to O(N²). Extrapolate to N=200/414. *This one number tells you whether ADR 0047's "permanent trust-model
  wall" is true or an artifact of the flat-`decide` encoding — a charter-relevant result worth banking either
  way.*
- **Probe 7b — Schur-pivot bit-growth.** On the same block, run the exact-rational block-Schur elimination the
  tiling path needs and measure intermediate-pivot bit-length / fill-in. If it stays polynomial, Schur-tiling
  plausibly reaches 130–414 **inside the existing charter, no new primitive**, at a fraction of C's cost.

Neither probe is authorized here; both are recorded as the cheapest next step **if** the operator wants to
de-risk the bank without committing to a build.

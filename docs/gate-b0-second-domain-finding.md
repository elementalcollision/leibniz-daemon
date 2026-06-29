<!--
Gate B0 (ADR 0042 Track B) finding: the second-domain decision. Reconciles the 7-model external witness
panel, two adversarial scout workflows (14-domain landscape + 4 zero-spend pre-build probes), and direct
operator-side measurements (Schönheim gap analysis on live LJCR data; VT-reduced Ramsey kernel timing;
LCS deletion re-check). Decision-determining for Track B1. No trust-boundary change.
-->

# Gate B0 — the second-domain decision: covering designs (the producer wall is domain-specific)

**Status:** measured, 2026-06-29. Gate D0 was RED *for CWC*. Track B asked whether that RED is universal.
**It is not.** Two domains — **covering designs** and **Ramsey lower bounds** — clear the sharpened
bar that CWC and deletion codes fail. **Recommended Track B1: covering designs** (Ramsey second,
Grassmannian third, deletion codes dead). The producer wall is **domain-specific, not a law.**

## Method (triangulated, three independent instruments)
1. **7-model external-witness panel** (`external-witness-brief-second-domain.md`) — independent judgment.
2. **43-agent landscape scout** (workflow) — 14 candidate domains, each adversarially refuted on two
   lenses, then synthesized with a completeness critic.
3. **Four zero-spend pre-build probes** (workflow + direct operator-side measurement) — the decisive
   data: live LJCR Schönheim-gap analysis, VT-reduced Ramsey kernel timing, deletion-code LCS re-check.

## The sharpened criterion (the panel's + scout's central correction)
My initial discriminator — *"records are set by search we can strengthen"* — is **necessary but
insufficient**. The reconciled criterion is a **4-way conjunction**, all four required:

1. **MECHANISM** — the current best in the reachable band was set by *general-purpose search we can
   strengthen* (not a hand-prescribed algebraic seed) and was beaten on fundable compute recently.
2. **HEADROOM** — a non-empty population of cells that are simultaneously *not proven-optimal* **and**
   have a *small enough witness* to render + re-check in core Lean.
3. **ORACLE** — a *single machine-readable integer table* settles novelty, with **no cross-source
   merge / no judge**. *(This leg is the most common cause of death — it kills LABS and deletion codes.)*
4. **NON-COINCIDENCE** — the beatable "best known" must not already equal a proven-optimal value.

The key insight: everyone (me + the panel) under-weighted the **ORACLE** leg. The binding question is
not "can stronger search beat it?" but **"is there a clean integer oracle *at the band where* a
strengthenable search can beat, with renderable witnesses?"** — the legs must *overlap*.

## Per-domain probe results

| domain | mechanism | headroom | oracle | non-coinc | witness/sound | **overlap** | verdict |
|---|---|---|---|---|---|---|---|
| **Covering designs** C(v,k,t) | GREEN (SA/tabu — Nurmela-Östergård COVER lineage) | **GREEN** | **GREEN** | PARTIAL | GREEN (small cells) | **GREEN** | **BUILD-CANDIDATE** |
| **Ramsey** lower bounds | GREEN (AlphaEvolve/Exoo/Wesley search-set) | GREEN | GREEN-ish (DS1) | GREEN | **GREEN (measured)** | **GREEN** | **BUILD-CANDIDATE** (cyclic witnesses) |
| Grassmannian A_q(n,d,k) | PARTIAL (construction-dominated; clique wins use prescribed automorphisms) | GREEN | GREEN (Bayreuth) | GREEN | PARTIAL (GF(q) linalg) | PARTIAL | CONTINGENT |
| Deletion codes A(n,s) | **RED** | GREEN | **RED** | PARTIAL | GREEN | **RED** | DEAD |

### The deletion-codes correction (the adversarial probe earned its keep)
The headline *"a FunSearch beat deletion-code records"* (Weindel–Heckel) does **not** survive scrutiny.
The probe read the actual tables and re-measured: the FunSearch's only *clean* win is single-deletion =
the **VT₀ optimum** (a proven-optimal algebraic seed → NON-COINCIDENCE fails); at the two-deletion band
where there is headroom, a **general-purpose MIS solver (ReduMIS) beats the FunSearch** (n=13: 56 vs 48;
n=16: 215 vs 200) — so *the LLM producer did not set the band records*. And there is **no single table
of record** (assembling best-known requires merging LH07/HF02/Swart/Gabrys-Sala/MIS-solver columns →
the cross-source merge the ORACLE leg forbids). Deletion codes carry the **same CWC signature**. This
corrects an earlier over-claim that the deletion beat "falsifies the producer wall" — it does not.

### Ramsey kernel-tractability (measured, refutes the panel's fear)
The panel feared the O(nᵏ) clique check is intractable. **Measured:** with the vertex-transitive
reduction (a clique/independent-set must be mappable to contain vertex 0, so the check collapses to one
vertex's neighborhood ≈ n/2 vertices), verifying *"no K₄ ∧ no independent-set-of-16"* on a circulant at
**n=240** runs in **≤0.07 s** in Python (the kernel would be slower, but that is 3–4 orders of margin).
**Soundness condition for the contract:** the witness must be **cyclic / vertex-transitive** and the
verifier must *check the cyclic structure*; for a non-VT witness the reduction is invalid and the full
check returns. No heuristic solver in the TCB — exhaustive enumeration on the reduced subgraph only.

### Covering-designs headroom (measured on live LJCR data, updated 2026-04-21)
Of 9,482 best-known entries, computing the Schönheim lower bound per cell: **5,460 cells are
simultaneously small-witness (<5000 blocks) and gap≥2**, including **2,251 with witnesses under 100
blocks**. The headroom and small-renderable-witness bands **massively overlap** — *not* the "gaps live
only in million-block corners" failure CWC/the panel feared — against a **single DOI-pinned oracle that
ships the witnesses**. *Honest caveat:* gap-to-Schönheim overstates *beatability* (Schönheim is a weak
lower bound), so whether a search can actually *reduce* a current best-known is the residual gate (below).

## Verdict — NOT "stop at A+C"; build the covering-designs verifier (B1)
The producer wall is **domain-specific**. CWC and deletion codes fail the conjunction; **covering
designs and Ramsey pass it.** Recommended **B1 = covering designs**, because it has the **best oracle**
(the La Jolla Covering Repository is a single authoritative DOI-pinned table that *ships block
witnesses* — directly analogous to how Leibniz already mirrors Brouwer for CWC; `cwc_table_oracle.py`
is the template), **the largest small-witness headroom**, and **the simplest sound verifier** (a flat
t-subset coverage sweep — no clique enumeration, no real-valued objective). **Ramsey** is a strong
second (smallest witness, measured-tractable kernel) with margin-risk + the cyclic-witness condition.
**Grassmannian** is third (great oracle, but construction-dominated mechanism = CWC-wall risk).

### Two things the probes do NOT yet establish (the residual gate)
The probes confirm the structural **overlap exists** (beatable-band ∩ small-witness ∩ clean-oracle) —
they do **not** establish that *our* producer can actually beat a current best-known. That is the
genuine final measure-before-build, the panel's **reproduction probe**: *can a baseline search
reproduce / approach several current best-knowns on bounded compute?* This is **no longer zero-spend** —
it requires building the verifier + a baseline producer (CPU first). Sequence:

1. **B1 (build):** covering-designs verifier (audit-tier, the `amplify.py` + `cwc_check.py` pattern) +
   the LJCR oracle mirror. **This is justified by Track A regardless of D** — it extends the
   verification-amplification spine to a second domain (kernel-checking research/human-supplied
   coverings). Not wasted even if the swing is RED.
2. **Reproduction gate (CPU):** can a baseline SA/greedy reproduce several current best-known coverings?
   GREEN → the producer is in the game; RED → bank A, do not fund D.
3. **Track D (billable, operator-gated):** only on a GREEN reproduction gate.

### Soundness contract for the covering-designs verifier
- **Witness:** a finite explicit list of blocks (k-subsets of {1..v}); no generators/compression — if a
  source gives a cyclic/base-block construction, the producer must **fully expand** it before the kernel
  sees it (never trust "develop under the group").
- **Kernel re-check:** every block is a k-subset of {1..v}; **every** t-subset of {1..v} is covered by
  ≥1 block — a flat O(B + C(v,t)) sweep. Scope B1 to the small band (v, t with C(v,t) renderable;
  e.g. start t≤4, modest v) to keep it core-Lean-checkable; the million-block heavy corner is out of scope.
- **Oracle:** novelty = strictly fewer blocks than the mirrored LJCR best-known integer for that cell —
  exact integer comparison, no judge (invariant 4). Audit-tier: never sets `kernel_verified`, never
  promulgates (the `cwc_check.py` posture).

**Disposition:** Track B is **live**, not dead. Build the covering-designs verifier; gate the billable
producer swing behind a CPU reproduction probe. A+C remain the durable product; **D is now a
gated, evidence-shaped diagnostic with a domain (covering designs) that actually clears the bar.**

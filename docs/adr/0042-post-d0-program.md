# ADR 0042 — The post-D0 program: amplification spine, second-domain scouting, decider-admission

- **Status:** PROPOSED — the operator's decision after Gate D0 RED, written down. Track A's first slice
  is audit-tier and trust-neutral (same posture as `scripts/cwc_check.py`), so it is safe to build
  regardless of this ADR's final acceptance; the strategic *sequencing* (A→B→C→meaningful-D) is what is
  up for review.
- **Date:** 2026-06-29
- **Deciders:** Operator (chose "1, 2, and 3 — then get to the point where the producer-strength swing
  is meaningful").
- **Siblings / supersedes-in-part:** ADR 0041 (tool use / building / research ingestion) — this ADR
  consumes its Gate D0 RESULT and re-aims its Phases 5–6. ADR 0040 (CWC record-triviality carve-out)
  remains the dormant path for a real beat. ADR 0008 / 0033 (publish gate) bound Track A's surface.
- **Touches the proof edge:** NO. `tests/test_invariants.py` stays byte-identical. Track A is
  audit-tier (never sets `kernel_verified`, never promulgates). Track C's decider-admission is
  operator-only (State 2, `register_decider`) and gets its *own* ADR per the ADR 0041 §2.2 ritual.

---

## 1. Context — what Gate D0 settled

[Gate D0](../gate-d0-producer-wall-finding.md) came back **RED**: on 5 open Brouwer cells the daemon's
autonomous structural search missed, a stronger producer (exact CP-SAT) found the record and the **Lean
kernel verified all 5**. Reading:

- **No encoding/representation gap for CWC** (GREEN falsified — every record is a finite,
  kernel-checkable witness). Tool-building "to represent better" has no target here.
- **The producer is the wall**, but across the full autonomous arc (exact CP-SAT + LLM FunSearch, 100+
  cells) stronger producers **match records, never beat them**. Worse for the swing: where exact CP-SAT
  ran to optimality and tied the record, **the record is proven optimal — there is nothing to beat.**
  Autonomous *novelty* is RED.

This forecloses "build tools to autonomously discover novel CWC bounds." It does **not** touch (a)
**verification amplification** — the daemon soundly kernel-verifies externally-supplied finite witnesses
(D0 itself did 5; the end-to-end demo did a 42-codeword A(14,6,6)); nor (b) the **sound tool-admission
capability** — the vision's "build, assemble, test, prove tools" leg, when aimed at *verification* rather
than discovery.

## 2. Decision — the program

The producer-strength swing (ADR 0041's Track-D / FunSearch-GPU bet) is **dead-on-arrival in CWC** for
two structural reasons D0 exposed: no beatable frontier (proven-optimal) and no representation gap. The
operator's directive — *"1, 2, and 3; once cleared, get to the point where the producer-strength swing is
meaningful"* — is exactly the set of preconditions that fix this. We adopt three tracks, sequenced toward
a **meaningful** swing, each with a measure-before-build gate:

### Track A — verification amplification as the spine *(highest certainty; build first)*
Make the D0 ad-hoc verification first-class and repeatable: a batch pipeline that takes external
constructions (research / scraper CONSTRUCTION seeds / a stronger producer's output) → the existing sound
audit path (`verify_cwc → render_cwc_lean → Lean kernel`) → a **provenance'd kernel-checked corpus** +
a rendered reading-room. Audit-tier, never promulgates, trust boundary untouched (the `cwc_check.py`
posture). This is the measured-true capability and the substrate that will verify whatever B or D
produces.

- **A1 (first slice):** the batch harness + corpus JSON + reading-room render + tests.
- **A2:** wire the scraper's VALIDATED CONSTRUCTION seeds (`seed_intake.construction_task` → sandbox)
  into the harness.
- **A3:** render the kernel-checked corpus into the *Calculemus* reading-room under the operator publish
  gate (ADR 0008/0033 unchanged).

### Track B — second-domain D0 scout *(the critical path to a meaningful swing)*
D0 RED is CWC-specific. The swing is only meaningful in a domain with a **soft/unproven frontier**
(headroom to beat) **or** a representation **GREEN**. Do not build a new-domain checker on a hunch.

- **Gate B0 (cheap, measure-before-build):** enumerate candidate finite-witness domains; score each on
  (i) kernel-checkable finite witness? (ii) soft/unproven frontier? (iii) plausible representation
  GREEN? Pick the best candidate **before** building anything. B0 is the analog of D0 for a new domain.
- **B1 (only if B0 yields a candidate):** build that domain's verifier/encoder (its own ADR), then run
  its D0 to confirm a beatable/GREEN frontier.

> **✅ GATE B0 RESULT — covering designs (measured 2026-06-29).** Triangulated across a 7-model witness
> panel, a 43-agent adversarial landscape scout, and four zero-spend pre-build probes (full finding:
> [`docs/gate-b0-second-domain-finding.md`](../gate-b0-second-domain-finding.md)). **The producer wall is
> domain-specific, not universal.** The criterion sharpened to a **4-way conjunction** — MECHANISM
> (search-set, recently beaten) ∧ HEADROOM (non-optimal cells *with small witnesses*) ∧ **ORACLE** (one
> machine-readable integer table, no merge — the most common cause of death) ∧ NON-COINCIDENCE. Results:
> **covering designs C(v,k,t)** and **Ramsey lower bounds** clear all four; **deletion codes** (the
> apparent FunSearch beat is really the VT optimum + a generic MIS solver, no single oracle) and **LABS**
> (frozen/fragmented oracle) do **not**. Measured: 5,460 LJCR cells are small-witness ∩ gap≥2 (2,251 with
> <100 blocks) against a single DOI-pinned oracle that ships witnesses; the VT-reduced Ramsey kernel check
> runs in ≤0.07 s at n=240. **Recommended B1 = covering designs** (best oracle + largest small-witness
> headroom + simplest sound verifier — the `cwc_check.py`/`amplify.py` pattern); Ramsey second
> (cyclic-witness condition), Grassmannian third (construction-dominated mechanism), deletion dead.
> **Residual gate before any billable swing:** a CPU *reproduction probe* (can a baseline search reduce
> several current best-knowns?) — the verifier itself is justified by Track A regardless of D.

### Track C — sound decider-admission (ADR 0041 Phase 6), aimed at amplification
Build the foreclosed-by-nothing leg: the operator-gated ritual to admit a **verified** stronger checker
as a sound decider (`registry.register_decider`, State 2), so a re-checked certificate becomes a PASS
instead of a DEFER — broadening what amplification can verify. The `cwc_rechecker`/`cwc_template` already
exist (built in ADR 0041 Phase 2, deliberately **not** registered). The first admission gets its **own
ADR** per the §2.2 (a)–(d) ritual + operator sign-off; never autonomous. Gated behind A (something to
admit a decider into) and B (which tells us whether the decider should be CWC or the new domain).

### Then Track D — the producer-strength swing, made *meaningful*
Once A+B+C clear, the swing has what it lacked: a **beatable frontier** (B), a **sound way to verify a
beat** (A), and a **sound way to admit a stronger producer/checker** (C). Only then is the GPU/SOTA-SAT
spend priced against a real target. Operator-gated and billable — run in the operator's terminal, never
autonomously.

## 3. Sequencing & dependencies

```
A1 → A2 → A3        (spine; start now)
B0 → B1             (scout; parallel to A; B0 is cheap and decision-determining)
          C         (admission; needs A to exist + B to pick the domain)
                D   (swing; needs A + B + C; operator-gated, billable)
```

Track A delivers standalone value immediately (a growing kernel-checked corpus) **regardless** of B/C/D
— the same "correct and cheap regardless of the gate" property ADR 0041 Phases 1–3 had vs. D0.

## 4. What stays invariant
- `tests/test_invariants.py` byte-identical; `kernel_verified` only in `LeanVerifier.discharge`;
  promotion only via `TrustPolicy.validate_path`; novelty by retrieval/decision-procedure, never an LLM
  (invariant 4). Track A is audit-tier; Track C is operator-only State-2 and re-derives from `cert.data`
  (E6) under the PreToolUse hook.
- Every billable / GPU / live-producer run happens in the operator's terminal on explicit go.

## 5. Status
- **A1** — ✅ BUILT (`scripts/amplify.py`, 6/6 kernel-verified seed corpus; PR #181).
- **B0** — ✅ MEASURED → **covering designs** recommended for B1; the producer wall is domain-specific
  (see the Gate B0 result block above + `docs/gate-b0-second-domain-finding.md`). The 4-way conjunction
  is the binding criterion; the ORACLE leg is the most common cause of death.
- **B1** — ✅ BUILT (ADR 0043): covering-designs verifier; the amplification corpus now spans two
  domains, 8/8 kernel-verified.
- **Reproduction gate** — ✅ **GREEN (2026-06-29).** A generic baseline reproduces the LJCR best-known on
  6/10 pre-registered cells (9/10 within 2 blocks; 0 beaten; all valid), including gap-2 cells — the
  producer *reaches the frontier*, unlike CWC. Finding:
  [`docs/covering-reproduction-probe-finding.md`](../covering-reproduction-probe-finding.md).
- **D — NOT JUSTIFIED on reachable cells (measured 2026-06-29).** After the reproduction GREEN, the
  operator chose "stronger CPU producer first." The strongest *free* producer — exact CP-SAT set-cover —
  beats nothing and **proves the records optimal on 4/6 headroom cells** (the other two reproduced/near,
  budget-limited): the Gate-B0 "headroom" was Schönheim weakness, not beatable slack. On the reachable
  small-witness band the record *is* the ceiling, so no producer (free or billable) can beat it. The
  swing is frozen as not-justified; re-open only for a specific larger cell with open optimality AND a
  kernel-renderable witness. Finding:
  [`docs/covering-exact-producer-finding.md`](../covering-exact-producer-finding.md). The measure-before-
  spend ladder thus ran to completion on **zero billable spend**.
- **C** — ✅ DESIGNED ([ADR 0044](0044-first-decider-admission.md)): the first decider-admission — a
  kernel-backed *valid-construction* decider (covering-first; generalizes to CWC), thin-over-the-kernel
  (A6 lighter route), with the §2.2 (a)–(d) + E6′/E7/E8 ritual and a live adversarial-review
  demonstration (valid→PASS, E7 stronger-claim→DEFER, E6 invalid→DEFER). **PROPOSED, awaiting per-kind
  operator sign-off.** The two admission edits (`register_decider` + the `trust.py` `FAITHFULNESS_PRODUCERS`
  producer) are operator-only and **not performed**; the ADR recommends deferring the live edits until the
  amplification→pipeline integration is scoped.
- **Outcome:** the durable product is the **two-domain verification-amplification instrument** (A);
  autonomous record-beating is measured not-justified (now *proven optimal* on the reachable band).

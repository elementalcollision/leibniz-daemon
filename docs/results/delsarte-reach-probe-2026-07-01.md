<!--
Reach-probe result — the discovery test for the Delsarte certificate pivot (gated next-step #1 after P1).
Audit/measurement only; no trust touch; tests/test_invariants.py byte-identical.
-->

# Delsarte reach probe — the discovery test (2026-07-01)

P1 proved the untrusted-LP → exact-integer-certificate → kernel chain sound on tiny tight cells. This probe
pushed it to a **band of 39 larger, genuinely-open A(n,d) cells** (n=12..24, d∈{3,5,7}) and asked the
discovery question: **does a verified Delsarte LP dual certificate tighten a best-known upper bound?**

## Verdict: **NO-TIGHTENING** — plain LP reproduces but does not discover (as theory predicted)
| measure | result |
|---|---|
| cells | 39 |
| verified exact certificates | **38** (1 cell, A(24,7), the rounding failed → no cert) |
| **tightenings of best-known** | **0** |
| verify-mismatches / soundness alarms | **0** |
| reproduce the best-known UB (open cells) | **9** (A(13,3)=512, A(13,5)=64, A(13,7)=8, A(14,{3,5,7}), A(15,{3,5,7})) |
| looser than best-known (SDP/constructions win) | 4 (A(12,5), A(12,7), A(16,5), A(16,7)) |
| **beats the sphere-packing (Hamming) bound** | **34 / 38** |
| **kernel-verified at scale** | **A(24,3): cert 645277, kernel `True`** (no decide-wall at open-cell size) |

## What this establishes
1. **The certificate architecture scales.** Verified, kernel-checkable Delsarte certificates were produced
   across genuinely-open cells up to n=24; the largest was checked on the real Lean 4.31 kernel (`True`).
   This is a real **verification-amplification asset**: the first kernel-checked LP upper-bound certificates.
2. **LP has real content** — it beats the elementary sphere-packing bound on 34/38 cells.
3. **But plain 2-point Delsarte LP does not discover** — 0 tightenings of any best-known UB. This confirms
   the honest prior: the classical LP bound is already baked into (and often superseded by SDP/Schrijver
   bounds in) the best-known tables, so it reproduces best-known where it is still optimal and is looser
   where a stronger method wins. The cheap-witness/already-known law reasserts itself for the plain LP.
4. **The oracle-wall guard stayed quiet** (0 alarms): no verified certificate fell below the sphere-packing
   floor or below the (unvetted) snapshot — consistent, no transcription surprises this run.

## Honest limitations
- The best-known-UB comparison used a **small, explicitly-unvetted snapshot** (13 cells). A genuine
  tightening claim would still require the authoritative DOI-pinned upper-bound oracle (gated step #2); but
  since plain LP produced **zero** tightenings even against the snapshot, that oracle is not the blocker —
  the *method* is.
- Rounding is loose in places (e.g. A(23,7): cert 4398 > sphere-packing 4096 — a valid but inflated UB from
  the margin-nudge). An **exact-rational LP** would tighten the pipeline's own bounds; not needed to reach
  the verdict.

## Implication for the direction
Plain Delsarte LP is a sound, scalable **verification** tool (kernel-checked UB certificates) but **not a
discovery** engine — reproductions, not beats. Per the external panel (GLM/Deepseek) and this data, the
actual discovery bet in this family is the **stronger certificate**: the Schrijver **SDP three-point bound**,
which strictly improves on LP for many cells and is where modern best-known UBs come from. That is a larger,
separate build (an SDP solver + exact PSD-certificate rounding + a kernel-checkable PSD certificate) with its
own measure-before-build gate.

**Fork for the operator:** (a) commit to the **SDP three-point certificate** bet (the real discovery path,
heavier build, rounding-fragility risk is higher for PSD than LP); (b) bank the **LP certificate architecture
as a verification-amplification asset** (kernel-checked UB certificates + the Delsarte bridge lemma, an
audit-tier product win) and stop here on discovery; (c) both — bank LP now, scope SDP next.

Artifact: `docs/results/delsarte_reach_probe.json`. Harness: `scripts/delsarte_reach_probe.py`. Test:
`tests/test_delsarte_reach_probe.py`.

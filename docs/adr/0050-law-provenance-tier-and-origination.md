# ADR 0050 — Law provenance: amplification tier + origination as first-class law attributes

**Status:** Proposed (2026-07-06). Complements ADR 0001 (charter & trust hierarchy), ADR 0017
(the work-log / `cycles` vs `laws` split), ADR 0045 (amplification pipeline), ADR 0048
(cross-kernel deciders). Anchors HANDOFF §6 ("origination vs amplification — the sharpest open
question").

## Context

After 35 cycles the reading-room's two lanes are badly out of balance:

- **`cycles[]`** (the work-log — *what the daemon did*): 35 entries, all **amplification/audit** —
  independently re-deciding *published* results. A cycle promulgates nothing and sets no
  `kernel_verified`.
- **`laws[]`** (promulgated, kernel-verified `Propositio` triads — *the daemon's own settled
  theorems*): **3 specimens** (`two_pow_pos`, `succ_pos`, `add_comm_nat` — toy demos of the
  format) **+ 1 held-back** law awaiting the operator publish gate.

We are about to start promoting genuine kernel-attested results into `laws[]` (the open-problem
resolutions: complex Hadamard order 94, kissing k(19) ≥ 11948, the EFX counterexample), and to
pursue **origination** (a brand-new fact the daemon conjectures and kernel-decides). Before we do,
a law needs to *say honestly what kind of thing it is*. Two facts are currently invisible on a
published law:

1. **How it survived** — the amplification tier / confidence ladder already used informally
   (kernel-decided `decide`; exact-procedure finite-field/exact-rational/enumeration; cross-kernel
   re-decision in a second kernel — ADRs 0045/0048). A `decide`-attested disproof and an
   exact-procedure census are not the same strength of evidence, yet render identically.
2. **Whether it is ours** — a re-decision of a *published* counterexample (**amplification**) versus
   a fact the daemon *originated* and no paper contains (**origination**). This is the distinction
   HANDOFF §6 calls the sharpest open question, and it must be legible, not blurred, once `laws[]`
   fills up. Publishing amplifications as if they were originations would misrepresent the work.

## Decision

Add two **report-only** provenance attributes to every promulgated law, surfaced by
`law_payload` and rendered by the reading-room. Both are descriptive metadata about *evidence and
authorship*; **neither gates promotion**.

1. **`tier`** ∈ {`kernel-decided`, `exact-procedure`, `cross-kernel`} — the confidence ladder of
   ADRs 0045/0048. `kernel-decided` = a Lean-kernel `decide` (or Mathlib-lemma) proof, axiom-clean.
   `exact-procedure` = the finite core carried by an exact finite-field / exact-rational / exact
   enumeration decider outside the `decide` wall (ADR 0047). `cross-kernel` = the same finite core
   additionally re-decided in a second kernel (Rocq/Coq, ADR 0048, report-only).

2. **`origination`** ∈ {`originated`, `amplified`} + provenance. `amplified` laws MUST carry
   `references` (the source they re-decide — the same APA citation shape and `requires_references`
   discipline as cite-worthy cycles, ADR 0017). `originated` laws assert a fact **no cited source
   states**; they carry a novelty attestation (invariant #4: retrieval + a decision procedure,
   never a judge) rather than a source citation.

`law_payload` gains `tier`, `origination`, and (for amplified laws) `references`. Specimens keep
`specimen: true` and are additionally tagged `origination: amplified`, `tier: kernel-decided` so
they never masquerade as discoveries. Fields are additive and default such that existing
consumers and the honesty gate (`export_calculemus.py --check`) are unaffected.

## The trust boundary is unchanged — this is the whole point

`law_payload` lives in `leibniz/calculemus_site.py` (the rendering layer), **not** in
`trust.py`/`verifiers.py`. These attributes are read *off* an already-promulgated Propositio; they
are never consulted by `TrustPolicy.validate_path`, `VerificationGate.is_promotable`, or
`LeanVerifier.discharge`, and they never set `kernel_verified` or mint an edge. A law is still
admitted to the Codex **iff** it carries a real kernel `Q.E.D.` (invariant #7,
`Calculemus.promulgate`), and published **iff** the ADR 0033 PROD + operator gate passes. `tier`
and `origination` change only *how a surviving law is described*, never *whether it survives*.
`tests/test_invariants.py` is untouched.

- A mis-set `tier`/`origination` is a **faithfulness/labelling** defect (a lie in the colophon),
  caught by review and the publish-time reference check — not a soundness hole. It cannot promote
  an unproven claim, because promotion never reads these fields.

## Consequences

- The reading-room can finally render *how* a law survived and *whether it is the daemon's own* —
  the confidence ladder and the origination/amplification split become visible instead of implied.
- Promoting the open-problem cycles (Phase 2) produces laws that are honestly labelled
  `amplified` + their tier, with the source cited — not dressed up as originations.
- Origination (Phase 4) gets a first-class marker, so the daemon's *first genuinely new law* is
  unmistakable in the ledger rather than lost among re-decisions.
- Specimens are explicitly marked amplification/kernel-decided, so "3 laws" never reads as "3
  discoveries".

## Non-goals

- No change to the trust boundary, the gates, or `kernel_verified`.
- No automatic promotion: turning a cycle into a law still requires authoring the Propositio triad
  and a **real** kernel discharge (Phase 2), and publication stays the operator's PROD-gated act
  (ADR 0033).
- `tier` is not a quality score; `cross-kernel` is stronger evidence, not a different truth.

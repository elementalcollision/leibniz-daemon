<!--
Capstone finding of the post-R6 sound-backend discovery investigation. Synthesizes the Walnut
(crawl) and SOS (walk) rungs into one empirical conclusion about WHERE the discovery ceiling is
and WHY. Provenance: docs/results/{observatory_*,sos_walk_*}.json. No trust-boundary change.
-->

# The discovery ceiling is the producer's encoding gap — confirmed across two sound backends

**Status:** measured, 2026-06-26. **The soundly-checkable *and* finitely-encodable region IS the
textbook region — across two independent sound backends. The binding constraint on discovery is novelty
at the *producer*, and it is a structural encoding gap, not soundness, reach, or prover power.**

This is the empirical answer to the ADR 0036 research question ("genuine discovery under a hard trust
boundary"). Two sound backends were taken through the full measure-before-build → build/probe → verify
arc, and both hit the *same* wall for the *same* reason.

## The two data points

**Crawl — Walnut (automatic-sequence FO), built and run live (runs 1–3).** After fixing artifacts
(ADR 0039 lint) and mode-collapse (anti-collapse conjecturer), run-3 produced **11 sound, diverse,
faithful decided records — and a 12-agent verification rated all 11 textbook**, 0 plausibly-novel. The
checkable properties (power-freeness, avoided factors) on the famous sequences (Thue-Morse, Rudin-Shapiro,
Fibonacci, Tribonacci) are exactly the studied ones.

**Walk — SOS/Positivstellensatz, probed (not built).** Soundness + box-OUT reach were GREEN (exact
rational re-check proven stdlib-only; reaches `∀x∈ℝⁿ`). But the **novelty go/no-go came back RED**: a
two-arm micro-probe (default vs explicit frontier-steering) scored 24 conjectures on
in-SOS-reach × box-OUT × plausibly-non-textbook. The GREEN intersection was **0/12 in both arms**, and
frontier-steering *degraded* quality (more false/sign-inverted artifacts, not more reachable novelty).

## The structural finding — a perfect anti-correlation

Across both SOS arms: **every `plausibly_novel` claim was `in_sos_reach = no`, and every `in_sos_reach =
yes` claim was `textbook_competition`. The two desirable properties never co-occurred.** The same shape
held for Walnut (every decided record was sound *and* textbook). The mechanism is identical in both
domains:

- The only objects the LLM conjecturer can hand a sound backend as a **clean, true, modest-cost,
  self-contained** claim are the *catalogued landmarks* — Motzkin / Choi-Lam / Robinson / Horn for SOS
  (which appeared *identically* in both arms), power-freeness of famous words for Walnut.
- The moment it reaches for genuine frontier content, the object **leaves the backend's encodable class**:
  flag-algebra density / hypergraph Turán / clique-density inequalities live over infinite-dimensional
  graphon–flag moment bodies, not finite real-vector semialgebraic sets; proof-complexity statements are
  *non-existence* meta-claims; and the merely-finite ones (copositivity, SOS-Lyapunov) arrived
  dominated by transcription/sign errors. All correctly flagged `faithful_self_statement = false`.

So the wall is not "the checker is too weak" (both checkers are sound and reach box-OUT classes) and not
"the prover is too weak." It is that **the producer cannot emit frontier mathematics in the finite,
self-contained form a sound backend can consume.** Soundly-checkable + finitely-encodable = textbook.

## What this means

- **The trust machinery is vindicated, repeatedly.** Walnut: 3 artifacts → 2 caught → 0 unsound. SOS:
  the soundness re-check is exact and even kernel-grade. No LLM ever decided; `tests/test_invariants.py`
  byte-identical across the entire arc. The project's reason for being holds.
- **Adding more sound backends will keep hitting this wall.** The kernel-bridge "run" rung (task #54)
  faces the same producer constraint, now confirmed twice. Building it for discovery yield is not
  justified by these data.
- **The lever is the producer's encoding, not the checker.** To break the ceiling, the daemon would need
  to translate frontier objects into backend-consumable form (e.g. a flag-algebra/graphon-moment encoder
  that emits the finite Razborov SDP variable space) — a substantial, domain-specific build with
  uncertain payoff — and/or an in-loop symbolic self-check to eliminate the false/misformalized class.
- **The honest framing of the daemon today:** a *sound verification / non-Q.E.D. decision* instrument
  that reliably produces correct, diverse, textbook mathematics behind an unbroken trust boundary — not
  (yet) a novel-discovery engine. That is a real, defensible result; "decided" and "sound" are not
  "novel," and the daemon now measures the difference honestly.

## Disposition
- **SOS rung: build deferred** (ADR 0037 §8, RED novelty gate). Kernel bridge stays gated (task #54).
- **Re-probe gate:** the SOS build goes GREEN when a re-run of the novelty micro-probe shows a non-empty
  GREEN intersection in even the default arm — which requires the producer-side encoder/self-check fixes
  first, not another backend.

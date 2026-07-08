# ADR 0063 — The origination path: fail-closed, novelty-attested `originated` laws

**Status:** **BUILT (machinery); NO originated law promulgated yet.** Implements the *path* for ADR 0050
Phase 4 (origination) as a fail-closed helper + a report-only `novelty_attestation`. Deliberately emits
**no** first originated law: every decidable candidate that passes the gate is novel-to-corpus but
textbook-derivable (the measured novelty wall), and a hollow "first discovery" would misrepresent the
work. The trust boundary is untouched.

## Context

ADR 0050 splits a promulgated law's provenance into **`amplified`** (a re-decision of a *cited*
published result — the KS and Hadamard-94 laws) and **`originated`** (a fact the daemon conjectured
itself, that no cited source states). An amplified law carries `references`; an originated law instead
"carries a novelty attestation (invariant #4: retrieval + a decision procedure, never a judge)."

The optimization roadmap has **twice measured** that the soundly-checkable ∧ finitely-encodable region
*is* the textbook region — so a genuinely non-textbook fact the daemon can kernel-decide is exactly the
novelty wall. This ADR builds the origination path so it is ready, without manufacturing a first law.

## Decision

**1. Fail-closed novelty attestation.** `leibniz/origination.attest_novelty(prop, novelty_gate)` runs the
FULL mechanical novelty gate and returns an attestation dict **iff** the gate returns `Verdict.PASS`,
else `None`. The gate (all kill-only, no judge) runs, in order: ADR 0061 coefficient-degenerate →
`is_trivial` tactic ladder → `contains_equivalent` (formal-hash corpus match) → `structural_known`
(ADR 0032 congruence signature). Any hit ⇒ the claim is trivial / KNOWN / a restatement ⇒ **not
originatable**. There is no path to an `originated` law for a claim the gate does not certify NOVEL.

**2. Report-only attestation field.** `law_payload` gains `novelty_attestation` (default `None`), carried
by an originated law in lieu of `references`. It records the gate's verdict, producer (`NoveltyGate`),
the checks passed, the nearest corpus neighbours, and — crucially — the **honesty caveat**: novelty is
certified *per the daemon's mechanical gate and its known-results corpus* (the daemon's own conjecture,
not a re-decision of a cited source), and is **not** a claim of absolute mathematical novelty — a
false-NOVEL (a textbook fact absent from the corpus) is possible and is the accepted error direction
(ADR 0032). Like `tier`/`origination`, it is report-only: never consulted by the trust gates.

**3. No first law yet.** The path is built and tested, but **no** `originated` law is emitted. Screening
candidates against the real 51-entry corpus, the passing ones (`(a+b)⁵≡a⁵+b⁵ mod 30`, etc.) are
novel-to-corpus yet textbook-derivable; the known ones (`n⁷≡n mod 42`) are correctly refused by
`structural_known`. Promulgating a derivable congruence as the daemon's "first discovery" would inflate
the claim. The first origination is **held** for a genuinely non-textbook candidate — a promulgation from
a real discovery-pipeline run, or an operator-provided candidate — at which point the built path emits it
in one call.

## Trust boundary — unchanged

`kernel_verified` is still written only by `LeanVerifier.discharge`; `origination` /
`novelty_attestation` are report-only and never consulted by `TrustPolicy` / `VerificationGate` /
`Calculemus.promulgate`. No edit to `trust.py` / `verifiers.py` / `tests/test_invariants.py`. The
novelty gate itself is unchanged (invariant #4 intact): origination simply *reads* its verdict as an
attestation, and refuses to proceed without a PASS.

## Consequences

- The origination path is ready and fail-closed: an originated law can never be minted for a
  trivial / KNOWN / restatement / coefficient-degenerate claim.
- The ledger stays honest: no law is mislabelled `originated`, and none is promulgated on a hollow
  novelty claim. When a genuine candidate arrives, `attest_novelty` + discharge + `law_payload(
  origination="originated", novelty_attestation=…)` produces it.
- Reaffirms the measured position: the binding constraint on origination is **novelty**, not prover
  reach or the trust boundary. This ADR provides the plumbing, not a breakthrough.

<!--
F2b external formalization round — the automated-prover (Harmonic Aristotle) leg. Audit/measurement only;
no trust touch. Aristotle PROPOSES; our Lean kernel (LeanVerifier.discharge) DECIDES.
-->

# F2b external round — Aristotle leg: milestone M0 (2026-07-02)

The F2b bridge (codes ⇒ primal-feasible; Schrijver's block-diagonalization Theorem 1) is a multi-week
definitional build — Rmatrix/Mblock/the change-of-basis U are not in Mathlib — so it is **not** a single
Aristotle goal. The well-posed, self-contained, Mathlib-only **milestone** we submitted is the engine of
Theorem 1's block decomposition, which Mathlib genuinely lacks (only `PosSemidef.submatrix` exists):

> **M0** `psd_fromBlocks_zero_iff` — a block-diagonal matrix is PosSemidef iff each diagonal block is:
> `(Matrix.fromBlocks A 0 0 D).PosSemidef ↔ A.PosSemidef ∧ D.PosSemidef`.

Verified to elaborate clean-with-`sorry` locally **before** submission (no paying Aristotle to fail on a typo).

## Result: **no proof returned** (~644 s) — honest negative signal; trust boundary intact

| milestone | Aristotle | our kernel |
|---|---|---|
| M0 `psd_fromBlocks_zero_iff` | no proof (643.6 s) | nothing to verify → **0/1 QED** |

Aristotle PROPOSES; our kernel (`LeanVerifier.discharge`, the sole `kernel_verified` writer) DECIDES — so this
returned nothing to trust, and nothing was trusted (no false positive). The signal is real: **even the
self-contained engine lemma is not a one-shot for the hosted prover**, consistent with the brief's
weeks-to-months estimate for the full theorem. This is the automated leg of the round; the human
Mathlib-community / panel channel (`docs/briefs/terwilliger-f2b-external-brief-2026-07-02.md`) remains the
primary path and is unaffected.

## Next options (operator call)

- **Longer / staged Aristotle budget** on M0, or an even smaller atom (e.g. the ⟨Z,M⟩≥0 congruence step our
  F2a already proved by hand) to find where the hosted prover's reach ends.
- **Send the human brief** to the Mathlib community / review panel (the multi-week definitional build is
  human-formalization-shaped, not single-goal-prover-shaped).
- Either way, F2b stays **audit/Observatory tier** (ADR 0046) until a bridge is *discharged* (not admitted).

Harness: `scripts/terwilliger_f2b_aristotle.py` (re-runnable; BILLABLE, minutes→hours; loads
`ARISTOTLE_API_KEY` from the main-checkout `.env`). Artifact: `docs/results/terwilliger_f2b_aristotle.json`.

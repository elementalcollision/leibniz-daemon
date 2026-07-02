# ADR 0046 — F2c: Terwilliger bridge results publish at the Observatory tier; Q.E.D. wiring stays gated

- **Status**: Accepted (operator decision, 2026-07-02)
- **Context**: The Terwilliger audit→Q.E.D. ladder stands at: three kernel-attested exact certificates
  (A(19,6) ≤ 1280, A(23,6) ≤ 13766, A(25,10) ≤ 503), F1 whole-certificate-in-kernel, and F2a weak duality
  machine-checked in Lean/Mathlib. The remaining gap to a kernel-checked statement *about codes* is F2b
  (codes ⇒ primal-feasible; the block-diagonalization Theorem 1), now out for an external formalization
  round (`docs/briefs/terwilliger-f2b-external-brief-2026-07-02.md`). Stamping Q.E.D. through this path
  would require a new discharge route into `Demonstratio.kernel_verified` — edits inside the guarded core
  (`verifiers.py`, trust tiers), which the charter gates behind a PreToolUse hook, operator sign-off, and a
  witness round (task #68 precedent). The discovery evidence (tickets ① + D6) says this family's value is
  verification amplification, not new bounds — so there is no discovery deadline pressing for Q.E.D. now.
- **Decision**: Terwilliger bridge-theorem-backed results are published at the **Observatory/reading-room
  tier** (ADR 0038 precedent): the kernel-attested certificate, the F2a theorems, and (when it lands) the
  F2b bridge are presented together, clearly labeled `DUAL_CERTIFICATE_CHECKED` — **no trust-surface edit,
  no new discharge route, `Q.E.D.` is NOT stamped through this path**. Revisit Q.E.D. wiring only when
  (a) F2b is discharged (not merely admitted), and (b) a dedicated ADR + hook + operator sign-off + witness
  round per the charter are in place. This ADR is the record that deferring is the *decision*, not an
  omission.
- **Consequences**: `tests/test_invariants.py` stays byte-identical; no guarded-file edits arise from the
  Terwilliger ladder in the current phase. The reading room may present the full evidence chain; consumers
  see an honest tier label. The F2b external round proceeds without any trust-boundary implication until a
  future ADR reopens F2c.

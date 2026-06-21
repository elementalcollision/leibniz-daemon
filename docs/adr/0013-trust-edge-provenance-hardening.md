# ADR 0013 — Trust-Edge Provenance Hardening (Proposed)

- Status: **Proposed**
- Date: 2026-06-21
- Related: ADR 0001 (trust tiers), the original plan review (tier-mislabel risk);
  `types.py` (`EdgeEvidence`), `trust.py`, `tests/`. **Touches the guarded core**
  (operator sign-off). Roadmap item #5 — orthogonal defense-in-depth.

## Context

`EdgeEvidence.tier` is a caller-supplied field; today the boundary rests on every
gate *tagging honestly* (`gates/verifiers` set MECHANICAL/ADVERSARIAL/JUDGED
correctly). Nothing structurally prevents a JUDGED check from being mislabeled
MECHANICAL — the failure mode HANDOFF §6 explicitly warns about. The judged-faithfulness
budget (ADR 0001 §5) is now enforced (R2c); provenance is the remaining gap the
plan review flagged.

## Decision (proposed)

1. **Provenance on the evidence.** Add `EdgeEvidence.producer: Optional[str] = None`
   — appended **after** `cost_units` so the positional construction the invariant
   tests rely on (`EdgeEvidence(edge, tier, verdict)`) is unchanged. Verifiers/gates
   stamp who produced the verdict (`"LeanVerifier.discharge"`, `"Z3Backend"`,
   `"FaithfulnessJudge"`).
2. **Provenance assertions in `validate_edge`.** A proof edge must originate from
   `discharge`; a MECHANICAL tier must not carry a judge producer. Mislabels raise
   `TrustViolation` structurally, not by trust.
3. **Mutation/property test.** Flipping any single edge's tier in an otherwise-passing
   path must make `validate_path` raise; a CI AST-guard that `EdgeEvidence(edge=PROOF_EDGE,
   tier=MECHANICAL, …)` is constructed only inside `discharge`.

## Options considered

- Provenance field vs trusting tags: **provenance** — catches mislabels mechanically.
- Required vs optional/append-only field: **append-only with default** — must not
  break the positional `EdgeEvidence(edge, tier, verdict)` the 11 tests use, or that
  would force editing `test_invariants.py` (a STOP).

## Consequences

- A mislabeled tier is caught by construction, closing the last "honest-tagging"
  assumption. Guarded: `types.py`/`trust.py` changes need operator sign-off and must
  keep the 11 invariant tests byte-identical and green.

## Open questions

- Whether to make `producer` required at the gates (stricter) once all producers
  stamp it, vs leaving it optional for backward compatibility.

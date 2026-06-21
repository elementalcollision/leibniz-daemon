# ADR 0013 — Trust-Edge Provenance Hardening (Proposed)

- Status: **Accepted** (implemented 2026-06-21 — proof-edge provenance: runtime
  producer check + the load-bearing construction-site AST-guard; **§2 also done**:
  the faithfulness/novelty gates stamp producers and validate_edge rejects a
  non-JUDGED edge carrying a judge producer. EdgeEvidence.producer is append-only so
  the 11 invariant tests stay byte-identical.)
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
2. **Runtime provenance check in `validate_edge` (proof edge).** A proof edge that
   *names* a producer must name the kernel (`KERNEL_PRODUCER`); a foreign producer
   raises `TrustViolation`. This is an *advisory* belt — a `producer=None` edge is
   not rejected (so the invariant tests stay byte-identical), and the string itself
   is spoofable — so it is **not** the load-bearing defense. (Generalizing this to
   reject a *judge* producer on a MECHANICAL faithfulness/novelty edge needs those
   gates to stamp producers; that is an Open Question, not yet built.)
3. **Construction-site AST-guard (the load-bearing defense).** A pure-AST test
   (`test_boundary_guards.py::test_proof_edge_is_constructed_only_in_kernel_paths`)
   asserts `EdgeEvidence(edge=PROOF_EDGE, …)` is constructed **only** in
   `LeanVerifier.discharge` and `ProofConsensus.prove` (which copies discharge's
   edge). This bounds *who* may mint a proof edge — which a runtime string can never
   do — and is what actually closes the `producer=None` gap. Plus the existing tier
   mutation property (flipping a proof edge to JUDGED makes `validate_path` raise).

## Options considered

- Provenance field vs trusting tags: **provenance** — catches mislabels mechanically.
- Required vs optional/append-only field: **append-only with default** — must not
  break the positional `EdgeEvidence(edge, tier, verdict)` the 11 tests use, or that
  would force editing `test_invariants.py` (a STOP).

## Consequences

- **What is caught:** a proof edge stamped with a non-kernel producer is rejected
  at the policy (runtime); and — the real guarantee — *no code path outside
  `discharge`/`ProofConsensus.prove` may construct a proof edge at all* (AST-guard).
  Together these close the `producer=None` mislabel for the **proof edge**: a rogue
  function minting `EdgeEvidence(edge=PROOF_EDGE, …)` fails the AST-guard regardless
  of producer.
- **§2 (now done):** the faithfulness/novelty gates stamp producers
  (`SMTVerifier.gaming_witness`, `ClaimProbe`, `FaithfulnessGate`, `FaithfulnessJudge`;
  `LeanVerifier.is_trivial`, `CorpusBackend`, `NoveltyGate`), and `validate_edge`
  rejects any non-JUDGED edge carrying a judge producer (`JUDGE_PRODUCERS`). So a
  judged faithfulness verdict mislabeled MECHANICAL is now caught structurally too.
  The runtime producer string is still advisory (a forger can type any name); the
  AST-guard remains the load-bearing guarantee for the proof edge.
- Strictly additive / monotone-tightening: no existing check removed;
  `test_invariants.py` stays byte-identical and green (the adversarial review of
  this change confirmed it does not weaken the boundary).

## Open questions

- Whether to make `producer` *required* (reject proof `producer=None`) — currently
  impossible without editing the byte-identical invariant tests; revisit if those
  are ever revised.

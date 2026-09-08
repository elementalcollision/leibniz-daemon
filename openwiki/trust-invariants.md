---
type: Reference
title: Trust Invariants
description: The seven non-negotiable executable trust invariants enforced by tests/test_invariants.py and leibniz/trust.py — the enforcement behind the trust boundary, not just documentation.
tags: [trust, invariants, tests, enforcement, trust-policy]
---

# Trust Invariants

`tests/test_invariants.py` turns each non-negotiable rule into a test that fails CI if a future change breaks it. `CLAUDE.md` restates these rules for the agent's benefit, but a memory file is **context, not enforcement** — this file is the enforcement (`tests/test_invariants.py` module docstring).

> If a change would require editing `tests/test_invariants.py` to pass, **STOP** — you are weakening the trust boundary. Surface the change to the operator.

Run: `pytest -q`

## The seven invariants

1. **A proof may only be settled by the kernel (MECHANICAL).** `test_proof_edge_must_be_mechanical` and `test_proof_edge_adversarial_also_rejected` — a `JUDGED` or `ADVERSARIAL` proof edge raises `TrustViolation`. `Demonstratio.kernel_verified` is set only inside `leibniz/verifiers.py::LeanVerifier.discharge`, and the proof edge is always `TrustTier.MECHANICAL`. No "the proof looks right" shortcut.

2. **Novelty is never settled by an LLM judge.** `test_novelty_edge_may_not_be_judged` — a `JUDGED` novelty edge raises. Novelty is settled by retrieval + a decision procedure (the known-results corpus + the non-triviality test).

3. **No promotion without a proof edge present.** `test_promotion_requires_a_proof_edge` — `validate_path` raises if `PROOF_EDGE` is absent. And `test_promotion_requires_a_faithfulness_edge` — a faithfulness edge is also required.

4. **A non-PASS edge can never promote.** `test_non_pass_edge_blocks_promotion` — a `DEFER` on any required edge raises.

5. **JUDGED faithfulness is permitted but flagged as residual.** `test_judged_faithfulness_is_permitted_but_detectable` — `validate_path` must NOT raise for the one judged edge, and `is_judged_faithfulness` returns `True`. The residual is tracked against the budget (`max_judged_faithfulness_fraction = 0.15`).

6. **`Q.E.D.` is earned by the kernel, never hand-set.** `test_qed_requires_kernel_verification` — `Demonstratio.seal()` stamps `Q.E.D.` iff `kernel_verified`, else `Q.E.I.`.

7. **The gate's verdict is a pure function of recorded evidence.** `test_is_promotable_true_only_on_complete_mechanical_path`, `test_is_promotable_false_when_proof_is_judged`, `test_is_promotable_false_without_proof` — `VerificationGate.is_promotable` renders no new judgment and re-runs nothing; it is a pure boolean over the recorded edges.

## How the invariants are encoded

The tests construct `_passing_edges(proof_tier, novelty_tier, faith_tier)` — three `EdgeEvidence` records with the chosen tiers — and assert `TrustPolicy().validate_path(...)` raises or admits. The default is all-MECHANICAL all-PASS, which is the only fully-mechanical path that promotes.

## The broader test suite

Beyond the 11 invariants, the suite is ~120 tests covering the capability ladder rungs and every ADR. Tests tagged `lean` require the pinned container (`leibniz-lean:v4.31.0`) and skip where absent; tests tagged `z3` require the `verify` extra. The stdlib invariant suite stays the universal gate.

See [Trust Boundary](../architecture/trust-boundary.md) for the policy mechanics and [Boundary Guards](../components/boundary-guards.md) for the structural AST guards that keep `kernel_verified` sole-sourced.

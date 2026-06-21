# ADR 0001 — Charter and Trust Hierarchy

- Status: Accepted (founding)
- Date: 2026-06-21
- Supersedes: none
- Related: Newton ADRs 0008 (discovery engine), 0010 (verification-gated promotion),
  0012 (mutation queue) — Leibniz instantiates Newton's *deferred* formal-proving branch.

## Context

Leibniz is a sibling daemon to Newton. Newton deliberately chose an
execution-gated verifier (a mutation-hardened acceptance test in a sandbox) and
named formal theorem-proving / SMT discharge a considered-and-deferred non-goal.
It pre-wired the seam for the deferred branch: `proof_obligation` (hardcoded
`"not_applicable"`) and `NEWTON_REQUIRE_PROOF_OBLIGATION` (default false).

Leibniz exists to occupy that branch: a daemon whose `Demonstratio` is a
**kernel-checked formal proof**, aimed at novel, tractable, provable theorems that
move a field forward — and explicitly designed so that no capricious LLM judgment
sits on the critical path of what becomes a law.

## The problem this charter answers

A proof-bearing daemon has one existential failure mode that an execution-gated
one shares but in a *milder* form: a **kernel-valid proof of a mis-formalized
statement**. The kernel guarantees the proof matches the *statement*; nothing
guarantees the statement matches the human-readable *claim*. Such a law is most
authoritative exactly when it is most wrong, and a public ledger makes it
permanent. This is the 3-body faithfulness problem (claim ↔ statement ↔ proof);
the kernel closes one edge, and our design must close the others without trusting
an LLM to do it.

## Decision

**1. LLMs propose; they never decide.** The only roles an LLM may occupy are the
proposal roles in `leibniz.types.Role`: survey, conjecture, formalize,
proof-draft, analogy. Adjudication is reserved for mechanical checkers.

**2. A trust hierarchy governs every edge.** Each decision edge is tagged with a
`TrustTier`:

- `MECHANICAL` — a kernel or decision procedure. Zero LLM trust.
- `ADVERSARIAL` — a falsification search. The LLM proposes; the search tries to
  refute. Trusted because failure is *constructive* (a witness), not a vote.
- `JUDGED` — irreducible LLM judgment. Permitted on exactly one edge, minimized,
  logged, and budget-bounded.

**3. The three edges and their tiers:**

- **proof ↔ statement: MECHANICAL.** The Lean kernel is the sole arbiter.
  `Demonstratio.kernel_verified` is set in `leibniz.verifiers.LeanVerifier` and
  nowhere else. `Q.E.D.` is stamped iff the kernel verifies; otherwise `Q.E.I.`
- **novelty / non-triviality: MECHANICAL.** Retrieval against a known-results
  corpus (Mathlib + curated analysis-of-algorithms results), compared by
  *structure* (`ClaimSignature`), plus the non-triviality test (a statement an
  automated tactic closes on its own is vacuous).
- **statement ↔ claim: ADVERSARIAL → MECHANICAL → JUDGED.** See ADR 0002.

**4. The policy is enforced at promotion.** `leibniz.trust.TrustPolicy.validate_path`
raises if any promotion path tries to resolve the proof edge at a non-mechanical
tier, or settle novelty by judgment, or promote on a non-PASS edge. The
verification gate calls it before promulgating.

**5. The residual is bounded and visible.** The fraction of promulgated laws whose
faithfulness edge fell back to `JUDGED` is tracked against
`max_judged_faithfulness_fraction`. Judged trust is allowed to exist but not to
creep.

## Consequences

- The system's correctness story reduces to: *the kernel is sound*, *the novelty
  corpus is adequate*, and *the faithfulness gate's adversarial+mechanical tiers
  catch mis-statements*. Only the last is research-hard; ADR 0002 addresses it.
- Laws are humbler and slower than Newton's (a proof obligation is dearer than a
  passing test), and that is the intended trade: fewer, sounder, harder-to-fake
  results.
- The domain is whatever the characteristica (Lean/Mathlib) can express. Initial
  target: analysis of algorithms (complexity bounds, correctness, optimality).

## Non-goals

- Empirical/physical law discovery (PySR/symbolic-regression style). Different
  Demonstratio backend; out of scope for this charter.
- Trusting an LLM as a proof oracle, ever, under any "the proof looks right"
  framing.

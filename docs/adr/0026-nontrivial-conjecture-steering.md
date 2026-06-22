# ADR 0026 — Steer the conjecturer toward non-trivial structure

Status: **Accepted** (2026-06-22)
Resolves a tension between ADR 0022 (encodable contracts) and ADR 0025 (ring-class
non-triviality).

## Context

ADR 0022 steered the conjecturer toward "elementary arithmetic so the contract fits" —
which landed squarely on polynomial identities/inequalities. ADR 0025 then made exactly
those **trivial** (a single `ring`/`nlinarith` closes them → quarantined). Left as-is,
the conjecturer would keep proposing claims the non-triviality gate now filters: high
DEFER/TRIVIAL, near-zero yield. The CONJECTURE prompt's own example
(`(a+b)² ≥ a²+b²+2a`) had become `nlinarith`-trivial.

The two requirements are not actually in conflict — there *is* a non-trivial-yet-
encodable band. The faithfulness DSL (integer vars, `+ - *`, constant powers,
constant `mod`/`div`, comparisons) can express claims that **no single decision
procedure closes**: divisibility/modular facts about non-linear expressions (e.g.
`6 ∣ n(n+1)(n+2)`, `2 ∣ n(n+1)`), parity properties, claims needing a hypothesis a
decision procedure can't exploit. These need induction / case analysis / a helper
lemma — and that is precisely where ADR 0024's decomposition prover earns its keep.

## Decision

Rewrite the `CONJECTURE` prompt (proposal-side; no logic, no trust edge):

- **Name the full filtered set.** Tell the model that any claim a single `decide`,
  `simp`, `omega`, `trivial`, `aesop`, `ring`, or `nlinarith` closes is quarantined
  TRIVIAL and can never be promulgated — mirroring `DEFAULT_TRIVIAL_TACTICS`.
- **Forbid the trivial class explicitly.** No pure polynomial identities or polynomial
  (in)equalities.
- **Steer toward non-trivial structure.** Ask for claims needing induction, case
  analysis, or a helper lemma — divisibility/modular facts about non-linear
  expressions, parity/recursion properties.
- **Keep the ADR 0022 contract requirement.** `claim_domain`/`claim_property` must
  still be inside the DSL, so faithfulness can still certify. Non-triviality and
  encodability are required *together*.
- **Replace the example** with a non-trivial-yet-encodable one:
  `claim_property = "n*(n+1)*(n+2) % 6 == 0"`.

The persisted notebook's stale "proven" lessons (the 32 ring-trivia) would otherwise
steer the conjecturer to *emulate* now-filtered trivia, so a validation run resets the
notebook/band; going forward, TRIVIAL outcomes feed the notebook's avoid-lessons.

## Why this is trust-safe

Prompt text only. No change to any gate, verifier, the DSL, or the trust policy. A
steered claim still runs the full cheap gates (now including ring/nlinarith
non-triviality), the honest faithfulness gate (with the ADR 0022/0024 guards against
domain-narrowing and property-hollowing), and the kernel's N+1 consensus. The kernel and
Z3 still decide. `tests/test_invariants.py` byte-identical.

## Consequences

- The conjecturer should now propose claims in the genuinely non-trivial band. Whether
  the prover ensemble + decomposition can *close* them is the open question the short
  validation run measures — a low yield would point at prover reach (lever 3), not the
  conjecturer.
- Efficacy is empirical: this is a steering hypothesis, validated by the run, not a
  guarantee.

## Validation

- Unit (CI-safe): the prompt names the full trivial-tactic set, forbids the polynomial
  class, steers toward induction/lemma/divisibility, and still embeds the DSL contract.
- Live (billable, next): a short calibration (fresh notebook/band) measuring the
  disposition shift — do conjectures now clear non-triviality, and does anything
  genuinely non-trivial reach the kernel and promulgate.

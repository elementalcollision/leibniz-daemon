# ADR 0053 — Raise the conjecturer's ambition (proposal-side), and name the real ceiling

**Status:** Accepted (2026-07-06). Proposal-side only — no trust-surface change. Complements ADR
0002 (faithfulness gate), ADR 0004/0021/0030 (the faithfulness DSL), ADR 0034 (structure variation),
ADR 0052 (novelty against the ledger). Records both a change and a diagnosis for the next step.

## Context

The daemon now originates and publishes genuinely non-trivial, kernel-proved laws — but they are all
**elementary single-variable polynomial modular-arithmetic facts** (`P(n) % m ∈ {…}`, `m ∣ P(n)`),
across moduli 2–16. The operator asked to raise *what it conjectures*, not *whether it can prove*.

Diagnosis (why the output is elementary):

1. **The real ceiling is the faithfulness DSL, and it is bound to soundness.** A promulgated law must
   pass the faithfulness gate (ADR 0002), which checks a claim's contract (`claim_domain`,
   `claim_property`) by asking **Z3** for a gaming witness (`claim_domain ∧ ¬claim_property`). So the
   DSL is restricted to what Z3 can decide soundly: `+ - * ^`(const) `/ %`(const) `min max`,
   comparisons, booleans. `gcd`, `factorial`, sums, variable exponents, `sqrt`, `log` are **forbidden**
   precisely because Z3 cannot check them soundly. The daemon is elementary **by design of the
   soundness boundary**, not for lack of proving power.
2. **Within that DSL, the conjecturer is in a rut.** It reflexively proposes one-variable
   `P(n) % m` facts; after a long run these are mined out, and (ADR 0052) restatements are now KNOWN.

## Decision (this ADR — the safe lever)

Widen what the conjecturer *reaches for* **inside the sound DSL**, proposal-side:

- **CONJECTURE prompt** (`providers/__init__.py`): add a "RAISE THE AMBITION" directive — the
  single-variable one-modulus reflex is a rut; prefer structurally richer claims the DSL already
  permits: **two-or-more-variable interactions** (`a*b`, `a²+b²`, `(a+b)^k`), **min/max invariants**
  (ADR 0030) needing a case split, **residue-set / relation-between-two-quantities** claims, and
  **uncommon composite moduli** (9, 12, 16, 24) needing CRT-style case analysis. "Depth over another
  safe single-variable residue."
- **Frontier** (`corpus/frontier.json`): add a `multivariable_and_extremal_arithmetic` domain whose
  seeds point at exactly these richer-but-DSL-legal shapes.

This is **proposal-side only**: it changes what the LLM is *asked* to propose, never how a claim is
*decided*. The cheap-refutation, novelty, faithfulness, kernel, and promotion gates are untouched;
`test_invariants.py` is byte-identical. Worst case is a shift in dispositions (more `unproven` or
`gamed` as the conjecturer aims higher) — never an unsound promulgation.

## The real ceiling-raiser (deferred, trust-sensitive)

Genuinely deepening the mathematics — `gcd`, bounded sums/products, factorial, richer relations —
requires **expanding the faithfulness DSL and giving it a sound checker** for the new constructs
(Z3 cannot; a bounded exact-enumeration checker could, at a bounded-soundness posture matching the
current Z3 search). That touches the **faithfulness gate** — a trust-critical component — so, by the
ADR 0051 precedent, it must clear an **adversarial soundness review before implementation** (in
particular: does a finite-prefix faithfulness check let a mis-faithful-but-kernel-true claim through,
and how is that bounded). It is **not** done here; this ADR names it as the gated next step.

## Consequences

- The conjecturer should produce more varied, less repetitive claims within the sound band
  immediately, at zero trust cost.
- The path to genuinely deeper laws is made explicit and correctly gated behind a soundness review,
  rather than reached for by loosening the faithfulness gate on optimism.

# ADR 0002 — The Faithfulness Gate

- Status: Accepted
- Date: 2026-06-21
- Related: ADR 0001 (trust hierarchy); descends directly from the review of
  Newton's `derive.py`/`gate.py` and the 3-body faithfulness analysis.

## Context

The Lean kernel guarantees `proof ↔ statement`. The single edge it cannot close
is `statement ↔ Enuntiatio` — whether the formal theorem actually encodes the
human-readable claim the ledger is held accountable to. This is the entire
residual risk surface of an otherwise-mechanical system.

The naive gate — *ask an LLM whether the statement matches the claim* — is
theater. The judge shares the formalizer's blind spots and rubber-stamps the same
misreading. A faithfulness gate that can be fooled by the same failure that
produced the mis-statement is worse than none, because it manufactures
confidence.

## Decision

The gate (`leibniz.gates.faithfulness.FaithfulnessGate`) tries three strategies,
**strongest first**, and stops at the first decisive result.

### 1. Adversarial — the gaming-witness (the spine)

Try to **satisfy the formal statement while violating the Enuntiatio's
`falsifiable_claim`**. Concretely: search (via Z3 / the witness mechanism) for an
object that the formal `theorem_src` admits but that makes the human claim false.

- If such a witness exists, the statement **underspecifies** the claim →
  `FAIL`, `FinishReason.GAMED`.
- This is *generative*: it catches gaps a concordance judge waves through,
  because it must exhibit a concrete counterexample to the faithfulness, not
  merely disagree. It reuses the same cheap-refutation discipline pointed at the
  faithfulness edge instead of the claim itself.

### 2. Mechanical — the claim-type probe (the fast path)

For claims that assert a **measurable property**, check the property of the formal
statement directly, with no LLM in the loop. Dispatched by `ClaimType`:

- `COMPLEXITY_BOUND` → the statement quantifies over input size and bounds an
  operation count in the claimed direction.
- `CORRECTNESS_OVER_DOMAIN` → the statement's hypothesis is the claimed domain and
  its conclusion the claimed postcondition.
- `OPTIMALITY` / `INVARIANT` / `EXISTENCE` / `STRUCTURAL` → analogous structural
  checks.

This is where the "claim-type router" belongs: **on the faithfulness gate, not as
a prover backend.** A measurable claim with *no decisive probe* returns `DEFER`,
never `PASS` — we refuse to launder an un-probed measurable claim through a judge.

### 3. Judged — round-trip + independent review (bounded residual)

Only legitimate for `ClaimType.OPEN_FORM` (claims that resist operationalization).
Round-trip back-translation (formalize → informalize → compare to the Enuntiatio)
plus an independent judge, thresholded. Every use is logged with `residual: True`
and counts against the trust budget in ADR 0001.

## Ordering and cost

The gate runs inside `FORMALIZE`, **before** any proof compute, in
cheap-refutation-first order:

```
cheap_refutation (cost~1) → novelty/non-triviality (cost~1) → faithfulness (cost~2-3) → proof (cost~10)
```

A faithfulness failure short-circuits before the kernel is ever invoked.

## Why this is structurally better than the predecessor

Newton's faithfulness gap is a 3-body problem with *no edge* tying anything to the
Enuntiatio. Leibniz closes two of three edges mechanically (proof via kernel,
novelty via decision procedure) and makes the third adversarial-first. The result:
the only place LLM judgment can be load-bearing is an OPEN_FORM claim's
faithfulness, and even there a gaming-witness gets first refusal.

## Consequences / open questions

- The gaming-witness is only as strong as the encoding of `falsifiable_claim` into
  a searchable predicate (`_negate` is currently a placeholder). Hardening this
  encoding is the primary R2 research task.
- Claim-type probes must be written per `ClaimType`; coverage of the probe table
  determines how often the system can stay on the mechanical fast path. This is
  the highest-leverage incremental work.
- An alternative considered: **claim-from-verification** — derive the Enuntiatio
  *from* what the statement provably establishes, rather than letting CONJECTURE
  emit free prose that FORMALIZE must then match. Yields humbler but structurally
  faithful claims. Retained as the fallback contract when the gaming-witness
  fires repeatedly on a conjecture family.

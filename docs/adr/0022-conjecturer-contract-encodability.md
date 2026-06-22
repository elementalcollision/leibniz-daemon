# ADR 0022 — Conjecturer contract encodability (steer claims into the faithfulness DSL)

Status: **Accepted** (2026-06-22)
Supersedes/extends: builds on ADR 0004 (structured faithfulness contract), ADR 0020
(refuse vacuous passes), ADR 0021 (widen the DSL soundly).

## Context

The deeper live calibration (6 cycles, 42 conjectures, the honest + widened
faithfulness gate, persisted band) produced a decisive shift: **`reached_proof`
fell 10 → 0**. The first calibration's "10/10 reached proof" was an artifact of the
gate *vacuously passing* un-encodable contracts (ADR 0020/0021 fixed that). Now the
honest gate **DEFERred 40/42** conjectures, caught 1 unfaithful, killed 1 trivial.

So the binding blocker moved **upstream**: it is no longer "the prover is too weak",
it is **"the conjecturer states claims the faithfulness checker cannot mechanically
verify."** Research-paper-seeded conjectures carry contracts
(`claim_domain` / `claim_property` / `established_domain`) full of named functions
(`log`, `gcd`, `factorial`), symbolic exponents (`2^n`), and asymptotics — all
outside the sound DSL — so the probe DEFERs *before any proof compute*, and nothing
can ever be promulgated.

The fix is on the **proposal** side: steer the conjecturer and autoformalizer to
emit contracts that live inside the faithfulness DSL, so the honest gate can
**certify** them and candidates reach proof. This changes *what we propose*, never
*how we decide* — the kernel and Z3 still decide, unchanged.

## The faithfulness DSL (the target grammar)

The sound, Z3-decidable fragment (ADR 0021, `leibniz/backends/smt_z3.py`):

- non-negative integer variables (any number, named freely);
- non-negative integer literals;
- `+ - *`;
- `^` with a **constant** exponent in `[0, 8]` (expanded to repeated multiplication);
- `/` and `%` by a **constant positive** divisor;
- comparisons `< <= > >= == !=`, `and` / `or` / `not`, parentheses.

Outside the DSL (→ DEFER): named functions, **variable** exponents (`2^n`),
division/modulo by a variable, real/rational numbers, quantifiers inside a predicate.

## Decision

Two proposal-side levers, both degrading to today's behaviour without z3 / the LLM
repair hook (the demo's deterministic fakes are unaffected):

1. **Prompt steering.** The `CONJECTURE` and `FORMALIZE` prompts now carry the DSL
   grammar verbatim, with an explicit forbidden list and a worked example, and ask
   the conjecturer to express `claim_domain` / `claim_property` (and the formalizer
   `established_domain`, covering `claim_domain`) *inside* the DSL — restating the
   claim as an elementary-arithmetic statement when the natural phrasing would not
   fit. This aligns conjecturing with the daemon's actual reach: novel **elementary
   arithmetic** (multivariable polynomial inequalities, divisibility, mod/div
   identities) is a large, genuinely-novel space the kernel can close.

2. **Mechanical contract repair (the safety net).** In `Formalize`, after the
   statement compiles and survives cheap-refutation + novelty but **before**
   faithfulness, a bounded repair pass mechanically checks each contract field with
   `Z3Backend.encodable`. If any field is un-encodable, it asks the provider
   (`repair_contract`) to restate the three predicates inside the DSL, preserving
   meaning. A repair is **committed only if it is strictly sound** (every guard needs a
   conclusive `decide_unsat`, so the pass **fails closed** — commits nothing — when the
   backend cannot decide):
   - all three fields become encodable, **and**
   - `claim_domain` stays **satisfiable** (non-empty) — a conclusively-empty domain is
     **rejected**, because an empty domain makes coverage vacuously hold (a laundered
     PASS), **and**
   - `claim_property` is **not weakened** — the repaired property must provably **imply
     the original** over the box (`new ∧ ¬old` UNSAT); an un-encodable original cannot
     be preserve-verified, so the repair is **refused** (→ honest DEFER).

   If repair cannot produce a fully-sound contract within the budget, the candidate is
   left untouched and **DEFERs honestly** at the gate. Repair never weakens, widens, or
   bypasses the gate; it only rewrites a *proposal* the same honest gate then
   independently re-checks (coverage + property).

`max_contract_repairs` is an `Formalize` field (default `0` → off) wired from
`LEIBNIZ_CONTRACT_REPAIRS` in `build_daemon` (default `1`).

## Why this is trust-safe

- It is **entirely proposal-side**. No edit to `trust.py`, `verifiers.py`, the
  gates, or `tests/test_invariants.py` (byte-identical). `kernel_verified` and
  `promulgated` writers are untouched.
- The contract is a *machine-checkable annotation* of the claim; the human
  `statement` is never rewritten by repair, and `theorem_src` — what the kernel
  actually proves — is unchanged.
- The honest gate still decides. A repaired contract faces the **same** coverage +
  property checks; the guards close the optimisation-pressure vectors the automated
  loop could otherwise exploit — emptying the domain, or hollowing the property.
- A repair that fails to reach a sound contract changes nothing — the candidate DEFERs
  exactly as it does today.

## Adversarial review hardening (2026-06-22)

A three-lens review (trust-safety / soundness / robustness), each finding
independently verified against the running code, surfaced four real issues; all are
fixed in this change:

- **(HIGH, soundness) `claim_property` was unconstrained once coverage held.** The
  probe's old "no-gaming" query `¬established ∧ claim_domain ∧ ¬claim_property` is a
  strict superset of the coverage query, so once coverage is UNSAT it is *vacuously*
  UNSAT for **any** property — the property was never actually tested. Allowing repair
  to rewrite `claim_property` made this exploitable (swap a hard, un-encodable true
  property for an encodable tautology → PASS). **Two fixes:** (a) `_steer_contract`
  forbids weakening `claim_property` (must imply the original); (b) `coverage_probe`
  now tests the property **inside** `established_domain` (`established ∧ claim_domain ∧
  ¬claim_property` UNSAT), so the property is genuinely checked — this also closes the
  *pre-existing* hole (a directly-proposed false property now DEFERs/FAILs instead of
  PASSing) and makes the probe match its own docstring. Strictly tightening — no new
  PASS path, and it breaks no existing certification.
- **(MEDIUM, robustness) Z3 could crash a cycle.** Non-boolean predicates (`not n`,
  `n and n>0`) raise `z3.Z3Exception` at *construction*; `encodable`/`decide_unsat`
  only caught `PredicateError`/`RecursionError`, so the exception escaped and aborted
  the whole circadian cycle. The two compile-time `except` clauses in `smt_z3.py` now
  also catch `z3.Z3Exception` → reported as un-encodable/undecided, never a crash
  (matching the module docstring's stated contract).
- **(LOW, robustness) the empty-domain guard degraded open.** A backend with
  `encodable` but no `decide_unsat` would skip the guard and commit. The pass now
  **fails closed**: no `decide_unsat` ⇒ commit nothing.
- **(LOW, test) no end-to-end coverage.** Added tests that drive the real
  `FaithfulnessGate`: a contract that DEFERs before steering and PASSes after, and a
  repair that breaks coverage and is still DEFERred by the gate.

**Residual (documented, not a regression):** a *tautological* `claim_property` that is
genuinely true on the domain still passes the property check — the contract cannot be
mechanically compared to the prose `statement`, so vacuity of the asserted property
relative to the prose is outside the gate's scope (it predates this change; the
non-weakening guard ensures repair cannot *introduce* it). Tightening the gate from
domain-faithfulness toward prose-faithfulness is a separate, larger question.

## Consequences

- More research-seeded conjectures should produce **certifiable** contracts and
  reach proof — the first measurable path to a kernel-verified promulgation.
- Conjecturing is nudged toward elementary arithmetic. This is deliberate: it is the
  band the current corpus + prover ensemble can actually close. The DSL-widening
  follow-up (symbolic exponents, named functions via bounded definitional encodings)
  remains the complementary lever for raising the ceiling.
- Cost: at most `max_contract_repairs` extra proposal calls per candidate that
  survives to the contract step, and only when the first contract is un-encodable.

## Validation

- Unit: the prompts embed the DSL grammar; the repair pass upgrades an un-encodable
  `established_domain` to encodable; an already-encodable contract is left untouched
  (no provider call); a domain-emptying "repair" is rejected; absent z3 / repair
  hook the pass is a no-op (CI-safe; z3 behaviour gated like ADR 0020/0021).
- Live (follow-up, billable): re-run the calibration and confirm the DEFER fraction
  falls and `reached_proof` rises — the success metric for this ADR.

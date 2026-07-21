# ADR 0067 — cvc5 cross-solver attestation for the Z3 probe layer

**Status:** **BUILT — opt-in, default OFF.** The ADR 0048 cross-kernel idea applied at the SMT layer:
every load-bearing probe verdict is a Z3 ``unsat``, and with ``LEIBNIZ_CVC5_CROSSCHECK`` set (plus the
new ``cvc5`` extra installed) each conclusive unsat is independently re-decided by **cvc5** on the
exact SMT-LIB2 script Z3 solved. Agreement is counted; a disagreement **degrades the verdict to
``unknown``** — kill-only in every consumer. The **trust boundary is untouched**: nothing here can
create a PASS, mint an edge, or reach the trust core; fail-closed on every absence or surprise.

## Context

The probe layer (cheap refutation, the gaming spine, ClaimProbe faithfulness, ADR 0035/0066
encodings) rests on Z3's verdicts. A ``sat`` is self-validating — its model can be re-evaluated
against the predicate — but an ``unsat`` ("no counterexample anywhere in the box", "no gaming
witness", "the pair is faithful") is a bare solver claim: single-solver trust, exactly the exposure
the Lean↔Rocq cross-kernel tier (ADR 0048) closes for kernel proofs. cvc5 (BSD-3, independently
developed at Stanford/Iowa, ``pip install cvc5``) is the natural second decider.

## Decision

1. **Re-decide the exact query, not a re-encoding.** ``Z3Backend._decide`` serializes its solver
   state via ``Solver.to_smt2()`` and ``smt_cvc5.Cvc5CrossCheck.redecide`` parses + re-solves it in
   cvc5 (``(set-logic ALL)`` prepended; per-check time limit; hermetic solver per query). This
   attests the **solver's verdict**, deliberately not the DSL encoding — the encoding is validated
   separately by the conformance suites and their brute-force oracles. Prototyped before building:
   7/7 verdict agreement across the encoding shapes (plain modular, multivariable, ADR 0035
   order-chains, ADR 0066 factorial/gcd tables, min/max).
2. **UNSAT-only.** ``sat`` verdicts carry a model that the callers can (and tests do) re-evaluate —
   cross-checking them buys nothing. Only the unfalsifiable direction is attested.
3. **Kill-only degradation.** On disagreement (cvc5 says ``sat``), one of the solvers is wrong about
   this query; the verdict degrades to ``unknown`` with a loud warning. Every consumer treats
   ``unknown`` as inconclusive: a lost refutation or a lost PASS — yield, never unsoundness. A cvc5
   ``unknown``/failure keeps the Z3 verdict (attempted, not established) and is counted separately.
4. **Fail-closed, opt-in.** Default OFF (zero behavior change); requires both the env flag and the
   ``cvc5`` extra; any parse/solve surprise returns ``None`` and the probe proceeds unchanged.
   ``CROSS_STATS`` exposes checked/agree/cvc5-unknown/disagree counts for runs and tests.

## Consequences

- A Z3 soundness bug in the daemon's fragment can no longer silently produce a wrong "no
  counterexample" / "faithful" verdict when the check is on — it now needs two independent solvers
  to be wrong identically.
- The cost is one extra bounded solve per conclusive unsat — small at probe scale, and entirely
  optional.
- Follow-ons (out of scope here, recorded in the 2026-07-09 assessment): a cvc5 second opinion where
  Z3 returns ``unknown`` (fewer DEFERs); lean-smt as a kernel-gated ensemble prover; the GPL-build
  finite-field theory for prime-field audit instrumentation.

## Non-goals

No new encoding surface; no probe-edge schema change (attestation is counters + a loud disagreement
path for now — threading per-edge provenance is a follow-on if ever wanted); no trust-core change.

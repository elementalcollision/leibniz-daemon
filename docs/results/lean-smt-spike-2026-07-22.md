# Spike — lean-smt as a kernel-gated prover leg (Phase γ, leg 3)

- Date: 2026-07-22
- Status: **investigated; image build deferred** (recommendation below)
- Context: the autonomy plan's Phase γ queued "the lean-smt spike (a kernel-gated `smt` prover,
  and optionally in the `is_trivial` ladder, which would honestly tighten non-triviality)".

## What lean-smt is, and why the trust argument is clean

[lean-smt](https://github.com/ufmg-smite/lean-smt) provides an `smt` tactic: it hands the goal to
cvc5, receives a **proof**, and *reconstructs that proof inside the Lean kernel*. Unlike trusting
a solver verdict, the kernel replays every step — so a proof closed by `smt` is `kernel_verified`
in exactly the sense the charter demands. No new trust tier, no solver-trusted promotion: the
tactic either elaborates (kernel accepts) or fails (DEFER). It would be the first **general**
LLM-free prover leg — today's six decision procedures each own a classified fragment; `smt`
covers whatever cvc5-with-reconstruction can close (linear/mixed arithmetic, congruence,
quantifier-free combinations), unclassified.

## Evidence from the live REPL image (Lean 4.31 + Mathlib)

Probed 2026-07-22 against the production REPL image:

| Probe | Result |
| --- | --- |
| `import Smt` in the REPL environment | environment fails to bootstrap ("lean backend unavailable") — the module is not in the image |
| `by smt` under `Mathlib.Tactic` | `unknown tactic` |

So the capability requires a **new Docker image**, not wiring. That is the entire cost of this
leg, and it is nontrivial:

1. A lake project pinning `Smt` to a release matching our exact toolchain (the kernel image is
   Lean **4.31** — lean-smt releases track Lean versions closely and a mismatched pin fails at
   `lake build`); plus Mathlib alongside (both as dependencies of one env project).
2. The cvc5 **binary** in the image (the tactic shells out to it), pinned and hash-recorded.
3. A rebuilt REPL bootstrap importing `Smt` + `Mathlib`, and a soak against the existing kernel
   conformance suites (the REPL contract — timeouts, error surfaces, axiom reporting — must
   survive the new environment; `axiom_closure` must be re-validated on `smt`-closed proofs).
4. Build time ~30–60 min; image size roughly doubles. Every heartbeat preflight then depends on
   the new image tag.

## What it would actually buy (measured, not assumed)

The honest uncertainty is **yield**: our UNPROVEN tail is currently dominated by shapes the six
procedures already classify or the ensemble closes; `smt`'s marginal territory is arithmetic
goals *outside* those fragments. Two cheap measurements can settle it before the image is built:

- Count the notebook/journal's UNPROVEN near-misses whose claims are arithmetic-only but
  unclassified by the six procedures (the fragment `smt` would inherit).
- The ADR 0071 counters: if `unknown_rescued`/`unknown_kept` grow, solver reach beyond Z3 is
  demonstrably being left on the table at the *probe* layer too.

Second payoff once the image exists: an `smt`-backed leg in the `is_trivial` ladder — a claim
closable by `smt` alone is evidence of shallowness, which would **honestly tighten**
non-triviality (a mechanical widening of the triviality test, not a judgment).

## Recommendation

Defer the image build to a dedicated increment ("γ3b") and let the journal justify it: run two
weeks of nightly beats with ADR 0070/0071 active, then read (a) the unclassified-arithmetic
UNPROVEN count and (b) the unknown-rescue counters. If either shows real volume, build the image
with the recipe above (it is fully specified; nothing blocks it but build time and a soak). The
trust boundary is unaffected either way — `smt` proofs are kernel-replayed, and activation would
follow the established `maybe_wrap_*` opt-in pattern behind `LEIBNIZ_LEAN_DECIDED`.

# Audit-runner (T5) — the MCR audit generalized into a re-runnable instrument: GREEN (2026-07-03)

**Result: GREEN.** The MCR formal-verification-as-a-service audit was the daemon's one **measured-positive**
lane, but a one-off (n=1). It is now a **re-runnable, CI-guarded instrument**: an *audit* is a spec of findings,
each carrying a verdict and (where re-runnable) an artifact — numeric, Z3, or Lean-kernel — and the runner
executes the available artifacts into a structured verdict report. `scripts/audit_runner.py`,
`tests/test_audit_runner.py`, `docs/results/audit_runner.json`. No trust surface touched.

## What's built (two of the three T5 increments)

**(a) Audit-runner harness + regression pack.** `mcr_audit_spec()` encodes the 8 MCR findings as
`(id, verdict, artifact)`: P1/P5 pure numeric, P2/P3/P6 Z3, P4 a Lean-kernel proof, P7/P8 reasoning verdicts
(the honest NOT-PROVEN downgrade and the proven-but-exponential steelman). `run_audit()` runs every available
artifact and reports what it actually returned, so an audit that silently rotted (a broken proof, a flipped Z3
result) fails loudly. The regression pack locks the verdicts and reproduces the artifacts. Measured (local, z3 +
Lean): **6/8 artifacts ran, all pass** (P1–P6 ✓; P7/P8 carry no automated artifact).

**(b) P4 Lean leg kernel-attested in CI.** `lean_leg_ok()` runs `mcr_p4_not_derivable.lean` through the real
Lean 4.31 kernel (stripping the umbrella `import Mathlib`, which breaks the REPL image, and passing targeted
`Mathlib.Tactic`), asserting **0 errors / 0 sorries**. Previously the P4 verdict was doc-asserted; it is now
mechanically re-checked, with a **corrupted control** (its core step replaced by `sorry`) that must fail. This
turns "REFUTED (Lean)" from a claim into a CI regression.

## Honest scope

The instrument is now **target-agnostic**: a second external target is simply a second spec. The one increment
that genuinely measures whether the positive EV generalizes beyond MCR — **(c) a second external target** —
needs an actual target (operator-supplied). Until then the harness stands ready and the MCR audit is a locked
regression, not a spreadsheet. This is verification-amplification (the daemon's honest strategic home), not
discovery; behind the unbroken trust boundary, `tests/test_invariants.py` byte-identical.

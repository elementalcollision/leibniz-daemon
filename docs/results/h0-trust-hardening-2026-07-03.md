# H0 — trust-integrity hardening: GREEN (2026-07-03)

**Result: GREEN.** The two cheap guards the roadmap's own adversarial critique flagged as #1 (and that were
never built) are landed. Both are pure trust-integrity, no compute, and edit no guarded-core file — they only
*observe* the boundary. `tests/test_kernel_verified_writers.py`, `tests/test_axiom_closure.py`,
`scripts/export_calculemus.py::axiom_closure`.

## 1. Sole-fresh-writer guard (`tests/test_kernel_verified_writers.py`)

An AST scan of `leibniz/**/*.py` enumerates every `kernel_verified` write — attribute assignments
(`x.kernel_verified = …`) and constructor kwargs (`Demonstratio(kernel_verified=…)`) — keyed by
`(path, enclosing qualname, kind)` (robust to line drift). It asserts the set is **exactly** the two sanctioned
sites:
- `leibniz/verifiers.py :: LeanVerifier::discharge` (attr-assign) — **MINTS** the fresh verdict from the kernel check.
- `leibniz/runtime.py :: _row_to_prop` (ctor-kwarg) — **REPLAYS** a persisted verdict (recall, not decision).

Any new site fails the guard. Teeth verified: the scanner detects a planted attribute-writer and a planted
constructor-kwarg (both absent from the whitelist). This mechanizes the charter invariant "`kernel_verified` is
set only by `discharge`" — previously only stated in `CLAUDE.md`, never enforced.

## 2. Axiom-closure gate (`scripts/export_calculemus.py::axiom_closure`, wired into `--check`)

For every ledger law claiming `kernel_verified`, `--check` now also elaborates `<theorem_src> := <proof_src>`
and runs `#print axioms <name>`, asserting the footprint contains **no `sorryAx`** and **no axiom outside the
standard Lean/Mathlib set** (`propext`, `Classical.choice`, `Quot.sound`). A "proof" that secretly rests on
`sorry` or an admitted lemma (an F2b-style scaffold) fails the gate even if the open term elaborates. Verified
against the real kernel: a clean theorem passes (`[propext]`); a `sorry` theorem is RED (`sorryAx`); an
admitted-axiom theorem is RED (extra axiom). CI-safe unit tests exercise the decision logic via a fake backend.

## Why this matters now

The roadmap's auditability contract says Q.E.D. is minted only by `discharge`, and the F2b ladder's gates are
`#print axioms` closures — but nothing mechanically enforced either. With H0 green, **an admitted-axiom scaffold
can no longer reach the reading-room labeled as discharged, and a second `kernel_verified` writer can no longer
slip in.** These must stay green before any F2b scaffold lands. No trust surface touched;
`tests/test_invariants.py` byte-identical.

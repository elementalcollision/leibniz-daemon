# ADR 0095 — `kernel_verified` must mean kernel-decided: fold the axiom footprint into the writer

- Status: **accepted — landed, and forced by a working exploit against the pinned image**
- Date: 2026-09-10
- Depends on: ADR 0001 (trust hierarchy), ADR 0056/0062 (the axiom-closure contract),
  ADR 0089/0090 (the hardening of `axiom_report` this reuses), ADR 0048 (Lean is the only
  kernel writer)
- Prompted by: Trail of Bits, *A proof of Fermat's Last Theorem that fits the margin*
  (2026-09-09) — `String.Pos.Raw.extract` disagrees between the logical definition and the
  compiled evaluator on all stable Lean ≤ 4.33.1; fixed in 4.34.0-rc1.

## Context

`LeanVerifier.discharge` is the sole writer of `Demonstratio.kernel_verified` (invariant 1),
and it set that flag from `check_proof` alone. `check_proof` bottomed out in `_kernel_ok`,
which was exactly:

```python
return (not has_error) and (not has_sorry)
```

No axiom footprint, no native-evaluation ban. `TrustPolicy.validate_path` does not check
axioms either — it validates edge structure, tiers and verdicts. The axiom footprint was a
**separate call that six providers and the `*_decided` gates each made by convention**. Every
real path called it. Nothing structural forced the next one to.

So the property the project exists to guarantee — *`kernel_verified` ⇒ kernel-decided* — rested
on call-site discipline, while invariant 7 (`Q.E.D.` iff `kernel_verified`) held mechanically
and therefore vacuously.

### This was not theoretical

Measured against the pinned `leibniz-lean-repl:v4.31.0`, not inferred from reading:

```
theorem margin : False := by
  have hk : slice = "" := by decide         -- the kernel's answer
  have hn : slice ≠ "" := by native_decide  -- the compiler's answer
  exact hn hk
```

where `slice = String.Pos.Raw.extract "a truly marvelous proof" ⟨2^63⟩ ⟨2^63 + 1⟩`. On 4.31
`#eval` returns the whole string and `decide` proves it empty. Deriving Fermat's Last Theorem
from `margin` and passing it through the real promotion path returned:

| | before this ADR |
|---|---|
| `LeanVerifier.discharge` | `kernel_verified=True`, `MECHANICAL`, `PASS`, sealed **`Q.E.D.`** |
| `axiom_closure` on the same proof | `ok=False`, `extra_axioms=['margin._native.native_decide.ax_1']` |

The writer was permissive and only the gate was strict. Anything reaching `discharge` without a
provider's by-convention follow-up call would have been stamped.

### A denylist could not have caught it

On the pinned 4.31 the footprint is `margin._native.native_decide.ax_1` — an auto-generated name
derived from the *theorem's own name* (leanprover/lean4#12216: since 4.29 native computation is
one generated axiom per computation). `Lean.ofReduceBool` and `Lean.trustCompiler` never appear.
`STD_AXIOMS` being an **allowlist** is the only reason the gate saw it at all.

## Decision

**1. The Lean backends enforce the footprint inside `check_proof`.** `#print axioms <name>` rides
along in the *same* round-trip as the proof, and both must pass. This covers every caller of
`check_proof`, not just the ones that remember a second call. It is also the only option for
`LeanCliBackend`, which `axiom_closure` cannot drive at all (it needs the REPL's `_run`) — the
asymmetry that made "just call `axiom_closure`" unenforceable there. Both backends share the
ADR 0090 hardened reader: the CLI's flat-text transport goes through a new `axiom_report_text`
adapter rather than a fourth open-coded scan.

**2. `discharge` fails closed for a backend that does not assert it.** A backend must expose
`enforces_axiom_closure = True`. Absent that, `kernel_verified` stays False. A future backend
cannot be wired in and silently mint kernel verdicts, and every opt-out is greppable by one name
instead of being invisible.

An unnamed declaration fails **closed** in both backends: there is no footprint to read, so there
is nothing to certify.

## Consequences

- `native_decide`, `sorry`, admitted lemmas and unaudited axioms can no longer produce
  `kernel_verified=True` through *any* path, including one written next year.
- The by-convention `axiom_closure` calls in the providers and gates are now belt-and-braces
  rather than load-bearing. They are kept: they run against the promoted `theorem_src` and cost
  nothing to keep.
- Test doubles must declare `enforces_axiom_closure`. That is the intended cost — a double that
  mints kernel verdicts should say so out loud.
- It incidentally hardens ADR 0048. The report-only Coq and Isabelle backends do not (and must
  not) assert `enforces_axiom_closure`, so a `LeanVerifier` mistakenly constructed around one now
  fails closed at the writer rather than relying on nobody ever wiring it up that way.
- This does **not** fix the toolchain. The pin is still 4.31, inside the affected range; moving it
  to ≥ 4.34.0-rc1 is tracked separately because it carries Mathlib-compatibility churn. What this
  ADR guarantees is that the bug is no longer *reachable through our trust boundary*, because the
  only route to it — trusting the compiler — is now refused by the writer itself.

## What was NOT decided

`set_option debug.skipKernelTC true` in an ADR 0062 preamble still produces no axiom at all, so a
clean footprint would not prove the kernel ran. No exploit was constructed for it on 4.31 (both
attempts failed at elaboration, before the option matters), and it appears nowhere in the repo.
It is left as a known-unguarded surface rather than being fixed on speculation; a preamble
option-denylist is the obvious remedy if it is ever wanted.

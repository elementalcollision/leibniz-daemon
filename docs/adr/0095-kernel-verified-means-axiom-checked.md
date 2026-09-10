# ADR 0095 — `kernel_verified` must mean kernel-decided: fold the axiom footprint into the writer

- Status: **accepted — landed; forced by a working exploit against the pinned image, and
  substantially rewritten after adversarial review broke the first fix**
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

**3. The name must come from a real declaration.** Found while attacking decisions 1-2, and it
defeated both them and the *pre-existing* gate. `_NAME_RE.search` took the first `theorem <name>`
match anywhere in `theorem_src`, comments included — and that name is what `#print axioms` is asked
about. A statement opening with

```lean
-- theorem Nat.add_comm
theorem evil : (1000000000000 : Nat) % 7 = 1
```

proved `by native_decide` reported the footprint of **Mathlib's `Nat.add_comm`** — clean, and a
different declaration entirely. Measured on the pin before the fix: `discharge` gave
`kernel_verified=True` / `Q.E.D.` *and* `axiom_closure(...)["ok"]` was `True`. `theorem_src` is
proposer-authored (unlike the operator-only preamble), so this was reachable.

`declaration_name` now strips Lean comments — **nesting-aware**, because Lean's block comments
nest and a non-nesting stripper leaks the inner text back out — and requires the keyword to open a
line, so only an actual declaration can name the thing being certified. It replaces `_NAME_RE` in
`axiom_closure` as well; the old regex is **deleted** rather than left in place, so it cannot be
reused. This was a latent hole in the ADR 0090 extraction that the new checks inherited, not a
regression introduced by them — which is the argument for attacking a guard rather than reading it.

### What adversarial review found (decisions 4-6)

Decisions 1-3 were then attacked by a skeptic with kernel access, per CLAUDE.md. **It broke them.**
Three more routes to `kernel_verified=True` on a compiler-trusted proof survived, one driven all
the way to `theorem catastrophe : False`. All three are fixed here; all are frozen as regressions.

**4. `proof_src` must not open a top-level declaration.** The root cause. `Expressio.proof_hints`
asserted that "a smuggled top-level command would be a parse error inside the proof — there is no
separate-declaration surface to poison". **That was false, and it was load-bearing** — it is why
nothing guarded `proof_src`. Lean elaborates

```lean
by native_decide

namespace M
theorem margin : True := trivial
```

as a proof *followed by two more commands*, and the appended `#print axioms margin` then lands
inside the still-open namespace and reports on the decoy `M.margin` — clean, and a different
declaration. `_report_re`'s optional-qualifier allowance (added for ADR 0062 namespaced preambles)
makes `'M.margin'` satisfy "the report names our theorem". Measured: `kernel_verified=True`,
`Q.E.D.`, **and** `axiom_closure(...)["ok"] is True`. One input, both layers.
`smuggles_top_level` rejects a command keyword at column 0; the comment stripper runs first so a
commented example is inert. The `propositio.py` claim is corrected in place.

**5. The CLI transport must not flatten stdout into one message.** `axiom_report_text` wrapped the
whole file as a single message, which defeated ADR 0090's per-message name filter: the filter was
satisfied by *any* report naming our theorem, while the axiom list came from a separate search that
returned the **first** list in the file. **This needed no adversary** — an ADR 0062 preamble
carrying its own `#print axioms` (16 of the `docs/crt/*.lean` artifacts do) lent its clean list to
a dirty theorem, and the two transports the ADR promised were "one hardened reader" reached
*opposite verdicts on identical content*. Fixed twice over: `axiom_report_text` splits per line,
and `_report_re` now captures the name and its axiom list **in a single match**, so the two can no
longer be prised apart by anything.

**6. `sorry` detection must match what Lean reports, not the letters.** Appending
`#print axioms <name>` echoes the declaration's *name* into the message stream, and every
sorry-scanner was a blind substring test — so `theorem sorry_free_addition ... := by decide`
became a silent, unexplained DEFER. `mentions_sorry` matches `sorryAx` and Lean's actual
`uses 'sorry'` warning. The footprint check is the real backstop: a proof using `sorry` carries
`sorryAx`, which no allowlist admits.

Two false-rejects in decision 3 were also caught and fixed: `nonrec theorem` (missing from the
modifier alternation) and `theorem upoly.{u}` (the character class stopped at `{`, leaving a
trailing dot, and `#print axioms upoly.` is a syntax error). Both had failed closed on honest
proofs.

The regression file is now part of `scripts/run_kernel_tests.sh`, which it was not before.

## Consequences

- `native_decide`, `sorry`, admitted lemmas and unaudited axioms can no longer produce
  `kernel_verified=True` through *any* path, including one written next year.
- The by-convention `axiom_closure` call sites get decision 3 for free — they were reading the
  wrong declaration's footprint under exactly the same crafted input.
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

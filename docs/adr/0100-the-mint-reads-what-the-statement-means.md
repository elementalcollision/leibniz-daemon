# ADR 0100 — the mint reads what the statement *means*

**Status:** **BUILT.** The statement-meaning class, open since ADR 0097 round 8 and audited-but-not-
closed by ADR 0099, is **closed at the mint** for its live surface. The trust boundary is untouched:
`trust.py`, `verifiers.py` and `tests/test_invariants.py` are byte-identical. The round-8 strict
xfail is now a passing assertion.

**Closes** the class ADR 0099 documented. **Amends** ADR 0097 round 7 (the reporter protocol).

## The gap

A clean axiom closure does not mean the statement says what it appears to say:

```
notation "False" => True
theorem oops : False := trivial      -- 'oops' does not depend on any axioms
```

The closure is not merely clean, it is **empty** — cleaner than a legitimate proof by the only
measure ADR 0097 applies. The kernel is not wrong; it proved exactly the proposition it was handed.
What changed is *which proposition that was*.

## What the live surface actually is

Measured on `leanprover/lean4:v4.34.0-rc2` before designing anything, because the shape of the fix
depends on it. Of eleven candidate attacks, **four are refused by Lean itself**:

| attempt | Lean's own response |
|---|---|
| `open Foo` / `export Foo (False)` / `open Foo in` after a closed namespace | *Ambiguous term* |
| root-level `def False` / `abbrev False` | *`False` has already been declared* |
| `infix:50 " = "` redefining equality | *Ambiguous term* |
| `variable (h : False)`, unclosed `section` | *unknown identifier* |

Lean does not silently prefer a shadowing name — it refuses the ambiguity. That is a real part of
the trust story and nobody had measured it. The remaining **eight** fall into two classes:

- **Syntax redefinition** — `notation`, `local notation`, `scoped notation` + `open`, `macro_rules`.
  All four make the statement's elaborated type literally the constant `True`.
- **Shadowing through an unclosed scope** — `def` / `abbrev` / `«False»` / `Nat` inside a
  `namespace` with no `end`. All four land the declaration at `Foo.oops` and name `Foo.False` in
  its type.

## Decision — read the denotation off the compiled olean

The compiled `Expr` has **already resolved every notation and every name**. So the mint asks the
compiled environment what the statement *denotes*, and needs no parser-table diff, no reimplementation
of name resolution, and nothing to keep in sync with Lean's grammar. Three signals, all read from
data the pipeline already produces:

| signal | refuses | catches |
|---|---|---|
| `ROOT` | the minted declaration is **absent** | a wrong expected name — fails closed |
| `SHADOW` | the statement's type names a module constant whose bare name already names a different constant | shadowing, 4/4 |
| `VACUOUS` | the statement's type **is** `True` | syntax redefinition, 4/4 |

`DENOTE` reports the type's constant set — the statement's meaning, canonically sorted and pinnable.

### `loadExts := false` is load-bearing, not an optimisation

The five designs an initial research pass produced were all defeated the same way, and none of them
had tested for it: they elaborate the preamble **in-process**. Measured — a preamble carrying
`initialize (IO.Process.exit 0 : IO Unit)` makes such a guard print nothing and exit **0**, so a
caller keying on the exit code accepts the attack; a preamble `run_cmd` can go further and forge the
guard's own success line on its real stdout, reading the nonce out of `ps -o args= -p $PPID`. **A
nonce protocol does not save a design that runs the adversary's code.**

Reading the compiled olean at `loadExts := false` — the mode the existing reporter already used —
neutralises both: the same olean that kills an `loadExts := true` importer reads safely. This flag
must never be raised.

### A nested landing is honest; only shadowing is not

The first version of this guard refused **every** declaration that did not land at its own name.
That is the right *precondition* for shadowing but the wrong *check*: round 6 pinned
`namespace LeibNS` with no `end` as an honest operator shape, and the blunt rule refused it. A guard
that drops real proofs is a defect even though it fails closed — which is exactly what the round-6
regression set exists to catch, and it caught this. The check now targets what makes the attack work:
a statement naming a preamble constant that **shadows an existing name**.

### Why a declaration name is back in the protocol, and why that is not a round-7 regression

Round 7 removed the name because it **aimed** the question: a wrong name made the reporter answer
honestly about the wrong constant, so the failure mode was a clean **pass on a decoy** — fail-open.
The name is now an **assertion**: a wrong name reads as "declaration absent" and **refuses** —
fail-closed. It travels as a **file**, so it never becomes a shell word (round 7 also found the name
reaching `bash -lc` unescaped). `tests/test_native_eval_redteam.py` carries that distinction as the
protocol guard test, rewritten rather than deleted.

### Stale images fail closed

A reporter built before this ADR emits no `ROOT`/`SHADOW`/`VACUOUS` line. Their **absence is a
refusal**, not a pass — the ADR 0093 "a lane that cannot run must say so" shape applied to a check.
Without that, running an old image would silently reopen the whole class.

## What is NOT closed

`@[irreducible] def Riemann : Prop := True` with `theorem rh : Riemann`. At `loadExts := false` the
normal form is `Riemann`; the reporter cannot see through it, and the shape is **structurally
identical to an honest operator helper**.

The structural reason it cannot be closed by a diff: a real law's statement type legitimately names
its own preamble constants — `hadamard94_witness1` names **six** — so any rule of the form "the
statement must not name a preamble-introduced constant" would refuse every honest law. This residue
is a *faithfulness* question (does the formal statement say what the claim says?) and belongs to the
ADR 0002 gate, not here. It is recorded, not hidden.

Also open by construction: a syntax redefinition that rewrites to some true proposition **other**
than `True` passes `VACUOUS`. The `DENOTE` line is what a reviewer reads for that, and pinning the
denotation — rather than the source text — is the ADR 0099 mechanism upgraded to meaning.

## Evidence

- `tests/test_denotation_guard_r0100.py` — 11 parser tests: each refusal, the honest nested landing,
  the empty-closure case, a forged line under another nonce, and stale-image fail-closed for all
  three lines.
- `tests/test_native_eval_redteam.py` — the round-8 xfail is now `test_notation_redefining_the_
  statement_is_refused`, and the protocol guard test records why a name may be asserted but never aim.
- Measured end-to-end through `LeanVerifier.discharge`: all eight attacks `kernel_verified=False`,
  `Q.E.I.`; honest laws `Q.E.D.`
- Kernel lane **90 passed, zero xfailed**, including the five Mathlib-importing laws — the corpus
  that every research lens had left untested.

## Consequences

- `kernel_verified` now means axiom-checked (0097), kernel-replayed (0098) **and** denotation-checked.
- The reporter image must be rebuilt; an old one refuses everything rather than passing anything.
- Two ADRs in a row have said a class was unclosable and been wrong — 0097 about the kernel bypass,
  0099 about this one. Both times the reasoning was sound about the wrong activity: it ruled out
  *scanning* and concluded nothing could *check*. The instrument that worked both times was the same
  one — ask the compiled environment, not the source text.

# ADR 0097 — Landing the axiom check: what four adversarial rounds did to ADR 0096's fix

- Status: **accepted — landed; forced by a working exploit, and rewritten four times after four
  rounds of adversarial review each broke the preceding fix**
- Date: 2026-09-10
- **Fulfils ADR 0096**, which reproduced and measured this gap but explicitly landed no fix. ADR
  0096 is the diagnosis; this is the remedy, and the record of how hard the remedy was to get right.
- Depends on: ADR 0096 (the gap, and its two build obligations — both discharged here),
  ADR 0097 (the 4.34 pin this was re-verified against), ADR 0001 (trust hierarchy),
  ADR 0056/0062 (the axiom-closure contract), ADR 0089/0090 (the hardening of `axiom_report`
  this reuses), ADR 0048 (Lean is the only kernel writer)
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

### What a SECOND adversarial round found (decisions 7-11)

Decisions 4-6 were attacked in turn. **They broke too** — two more end-to-end routes to
`kernel_verified=True`, and decision 6 turned out to be a material *regression*. The pattern is
worth naming: every round, the thing that failed was a **syntactic guess about Lean's surface
syntax or output**, and the fix that held was a **structural check**.

**7. The smuggle guard must allow leading whitespace.** Decision 4 was a column-0 scan whose
stated rationale — "a proof's own continuation lines are indented, a new command is not" — is
simply false: Lean parses a command at any column. One leading space walked past it and drove
`theorem catastrophe : False` to `Q.E.D.` through `LeanCliBackend`. Whitespace is now allowed,
and `set_option ... in` / `open ... in` are exempted as term modifiers (honest proofs use them —
`gates/mixed_modulus_decided.py` emits the first).

**8. The comment stripper must respect string literals.** Lexing `/-` without tracking strings is
itself an attack surface: a proof containing `have s : String := "/-"` opened a block comment that
never closed, so the stripper swallowed the rest and the guard saw nothing — while Lean, which
lexes the string correctly, elaborated the `namespace` decoy that followed. Independent of
decision 7, and it would have survived an indentation-only fix.

**9. The `sorry` scan must stay BROAD — decision 6 was a regression.** Lean writes the warning
with **backticks** (``declaration uses `sorry` ``, verified on 4.31.0, 4.33.1 and 4.34.0-rc2), so
narrowing the scan to `uses 'sorry'` matched *nothing at all*. `LeanCliBackend.check_source`
began returning `True` for `theorem t : 2 + 2 = 5 := by sorry` — the function ~20 audit scripts
call "the trusted re-check", and the one path with **no axiom-footprint backstop**. A sorry-ed
ADR 0062 preamble helper also stopped being caught, falsifying `axiom_closure`'s own docstring.
The scan is broad again; the *echo* of `#print axioms <name>` is what gets excluded, which was
the sole cause of the false DEFER decision 6 was reaching for. `sorryAx` is tested before the
exclusion, so a hole named in the footprint still bites.

**10. The text transport must not split per line — decision 5 over-corrected.** Lean's
pretty-printer **wraps** a long axiom list across lines (measured: a 3-axiom footprint wraps once
the theorem name reaches 60 characters, a native-axiom footprint at 15; `set_option format.width`
does not suppress it). Per-line splitting therefore saw a report with no list and a list with no
report, and the two transports disagreed on identical content *in both directions* — an honest
62-character-named proof got `Q.E.D.` from the REPL and `Q.E.I.` from the CLI, and a wrapped dirty
footprint could lose to an earlier one-line report about the same short name. The blob is kept
intact; the atomic capture from decision 5 is what makes that safe, since `[^\]]*` spans newlines.
Tagged diagnostics (`error(lean.unknownIdentifier):`) are now recognised alongside plain `error:`.

**11. Only the preamble may qualify our name.** The structural check, and the one that does not
depend on anticipating syntax. `_report_re` allows an optional qualifier because an ADR 0062
preamble may open a namespace — without it every namespaced law would silently DEFER. But "any
qualifier" also accepts `'M.margin'` for a decoy the *proof* declared, which is how both rounds'
exploits stood up a clean report for a dirty theorem. The preamble is operator-authored and
trusted; `proof_src` is not. So `expected_report_names` accepts exactly the qualifiers the
preamble could have introduced, plus Lean's own non-spoofable `_private.<Module>.<n>.` mangling.
**Decisions 7 and 8 are keyword scans and cannot be complete; this is what actually holds.**

Four honest-proof false-rejects found in the same round are fixed: `set_option ... in theorem` on
one line, `open ... in theorem` on one line, a name on the line after the keyword, and
`«guillemet names»`. `python demo.py` — a documented command and a blocking CI step — had
regressed from `promulgated: 1` to `0` because its `FakeLean` lacked the decision-2 attestation.

### A THIRD round: the reader never bound the answer to the question (decisions 12-13)

Decisions 7-11 were attacked in turn. **They broke too**, and decision 11 — described above as
"the structural check that actually holds" — turned out to be the *final step of the exploit*.

**12. Read the footprint under an unpredictable PROBE name.** The reader matched report-shaped
*text* anywhere in Lean's output and never bound it to the `#print axioms` command it had itself
issued. A proof can simply print a clean report:

```lean
by native_decide

run_cmd IO.println "'catastrophe' depends on axioms: [propext]"
```

`dbg_trace` inside the proof term does the same with **no imports and no top-level command at
all**, so no keyword scan can ever see it. Combined with a `namespace M` in the proposer-authored
`theorem_src` — which nothing guarded, because `smuggles_top_level` was only ever applied to
`proof_src` — Lean's genuine report read `'M.catastrophe'`, which decision 11 duly **rejected**,
leaving the forgery as the only accepted report. Measured on the pinned 4.31: `kernel_verified=True`,
`Q.E.D.`, on both transports and through `axiom_closure` as well — and the daemon stamps `Q.E.D.`
on **both P and ¬P**, since the kernel proves the negation honestly.

The fix binds the answer to the question. `def <probe> := @<name>` inherits the theorem's whole
axiom closure, so `#print axioms <probe>` reports the real footprint under a name generated
*after* the proof text was fixed (`secrets.token_hex(16)`). Forging it means guessing 128 bits.
The qualifier allowance is permissive again, because unpredictability — not the qualifier — is
what authenticates the report. `expected_report_names` and `_name_acceptable` are **deleted**:
leaving a check that actively enabled an exploit in a trust module is worse than having none.

**13. `theorem_src` must declare exactly one thing.** It is proposer-authored and was entirely
unguarded. `statement_is_single_declaration` allows no top-level command besides the declaration.

### A FOURTH round: the proof can redefine the question's answerer (decision 14)

Decisions 12-13 broke too, and this one settles the architecture.

**14. Confine the proof to a term position.** `proof_src` could redefine the `#print axioms`
command elaborator itself:

```lean
open Lean Elab Command in elab_rules : command
  | `(#print axioms $i:ident) => logInfo s!"'{i.getId}' does not depend on any axioms"
```

It pattern-matches `$i:ident`, so **it never needs to know the probe name** — decision 12's 128
unpredictable bits are irrelevant against it. Measured on the pin: `theorem rp_margin : False`
came back `kernel_verified=True`, `Q.E.D.` on the CLI backend. Two independent gaps let the
keyword scan miss it: `elab\b` cannot match `elab_rules` (`_` is a word character), and the same
hijack written on ONE line slipped past the `set_option/open ... in` exemption, which excused the
whole line rather than just the prefix.

**Extending the keyword list is not the fix**, and this was verified rather than assumed: adding
`elab_rules` still leaves the one-line bypass. The underlying error was asking a question inside
an environment the adversary controls.

So the proof now goes into a **parenthesised term position**. Lean commands cannot appear there,
so a smuggled `elab_rules` is a parse error rather than a registered elaborator — measured:
`unexpected token 'open'; expected ')'`. Honest proofs are untouched (multi-line tactic blocks,
`induction ... with`, `calc`, term proofs, anonymous constructors, `set_option ... in` statements,
namespaced preambles all still earn `Q.E.D.`). The only escape is closing the wrapper early, which
`closes_more_than_it_opens` refuses. The keyword scans keep the newly-found keywords and stay
explicitly labelled as defence in depth.

### The pattern, stated plainly

Four rounds, and the same shape every time. **Every guard that failed was a syntactic guess —
about Lean's surface syntax, its output format, or which names were legitimate. Every one was
bypassed by an input its author had not imagined.** The two that hold do not try to anticipate
anything, and they work the same way: they remove the adversary's ability to answer rather than
predicting what they will write. The probe asks a question that cannot be answered in advance;
the confinement puts the proof somewhere a command cannot be written at all. Where a guard must
remain syntactic (`smuggles_top_level`, `statement_is_single_declaration`), it is documented as
defence in depth and is explicitly *not* relied upon — round 4 is the proof that such a guard
will eventually be wrong.

The corollary is uncomfortable and worth keeping: **decision 11 was more dangerous than no check
at all.** It looked structural, it was described as load-bearing, and its rejection of a
legitimate report is what made the forgery win. A guard that discards true evidence needs the
same scrutiny as one that admits false evidence.

### ADR 0096's two build obligations, discharged

**Obligation 1 — unify the assembly.** ADR 0096 measured that tightening the mint alone regresses
**24 of 63** promulgated rows: those whose stored `theorem_src` carries a `:= <proof>` tail. The
backends' `_join_proof` has always cut that tail; this ADR's `probe_source` did not, and emitted a
doubled `:=` that is a parse error. It would have failed those rows CLOSED and looked like a
soundness win. Both now share one `statement_head`, so the two assemblies cannot drift apart again.

Verified against the live ledger on the 4.34 pin: **28/28 promulgated laws re-discharge**, zero
failures — including the census/Steiner/double-blocking laws that ride in as whole-artifact
ADR 0062 preambles.

**Obligation 2 — move the panel's pre-check with the mint.** `proof_repair.py` gates on
`check_proof_with_error` and discharges what that accepts; its
`"kernel rejected a proof the pre-check accepted"` branch is dead only while the two predicates
agree. Tightening the mint alone makes it live, and the panel would burn rounds proposing
`native_decide` proofs it then discards, with no diagnostic the reasoner could act on. Both
backends' pre-checks now run the same probe assembly and the same footprint check, and a dirty
footprint is reported as `_axiom_complaint` — an error naming `native_decide` and suggesting
`decide` / `norm_num` / `omega`, which the repair loop can actually use.

### The pin move made most of these tests vacuous — measured, not assumed

ADR 0095 moved the pin to 4.34.0-rc2, where the compiled evaluator agrees with the kernel and the
Trail of Bits contradiction cannot be built. Every regression that drives that specific exploit
therefore passes on 4.34 **whether or not the axiom guard exists**. Mutation-checked by disabling
the footprint check (`ok = True`) and re-running: 8 tests fail, and
`test_trail_of_bits_exploit_cannot_be_promulgated`, `test_elab_rules_hijack_cannot_promulgate_false`
and `test_forged_axiom_report_cannot_promulgate` are **not among them**.

They are kept — they bite if the pin ever moves backwards — but they are no longer the evidence.
`test_native_decide_is_refused_BY_THE_FOOTPRINT_not_by_an_error` is: a plain `native_decide` proof
of a TRUE statement elaborates cleanly on every toolchain in scope and carries
`<theorem>._native.native_decide.ax_1`, so the footprint check is the only thing that can refuse
it. That test fails under the mutation. This is the ADR 0093 discipline applied to itself — a lane
that cannot fail must say so.

## Consequences

- `native_decide`, `sorry`, admitted lemmas and unaudited axioms no longer produce
  `kernel_verified=True` on any route tested here, and the check is now structural rather than a
  convention a future call site can forget. That is a weaker claim than "through any path", and
  deliberately so: the first version of this ADR made the stronger claim and adversarial review
  falsified it within the hour, three times over. What is warranted is that the footprint is read
  by the writer, that a backend which does not read it cannot stamp, and that every route found
  so far is frozen as a regression.
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

**The preamble itself remains a trusted input.** `smuggles_top_level` guards `proof_src`, which is
proposer-authored; the ADR 0062 preamble is operator-authored and its whole purpose is to carry
top-level declarations, so it cannot be guarded the same way. Decision 5 means a preamble's own
`#print axioms` can no longer be mistaken for our theorem's, but an operator who writes a hostile
preamble is outside this ADR's threat model — as they always were. If that ever stops being an
acceptable assumption, the remedy is to render the preamble from a checked source rather than to
scan it.

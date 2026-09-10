# Lean native-evaluation exposure assessment — the Trail of Bits `String.Pos.Raw.extract` bug (2026-09-10)

**Result: no published Leibniz law is invalidated. One real defect was found in the trust boundary,
demonstrated with a working exploit, and fixed (ADR 0097). The toolchain pin is still inside the
affected range and is tracked as separate work.**

Prompted by Trail of Bits, *A proof of Fermat's Last Theorem that fits the margin* (2026-09-09).

## The bug

`String.Pos.Raw.extract` disagrees with itself. Asked for a one-byte slice at an astronomically
large position, the **logical definition** returns `""` while the **compiled native code** returns
the whole original string. Both are reachable in one proof, so `"" = "a truly marvelous proof"`
gives `False`. All stable Lean **≤ 4.33.1**; fixed in **4.34.0-rc1**.

**The kernel is correct and the compiler is wrong.** Only native evaluation (`native_decide`,
`#eval`) reaches it. Plain `decide` is unaffected.

Reproduced here on all three locally-installed toolchains:

| toolchain | `#eval String.Pos.Raw.extract s ⟨2^63⟩ ⟨2^63+1⟩` | verdict |
|---|---|---|
| v4.31.0 (**our pin**) | `"a truly marvelous proof"` | vulnerable |
| v4.33.1 | `"a truly marvelous proof"` | vulnerable |
| v4.34.0-rc2 | `""` | fixed |

and `example : ... = "" := by decide` succeeds on 4.31, i.e. both halves of the contradiction are
available simultaneously.

## Corpus exposure: none

1. **Zero String surface.** `String` / `Substring` / `.extract` appear in none of the 39 `.lean`
   files. The specific bug has no direct reach into the corpus.
2. **45 recorded axiom footprints across 14 artifacts, all clean** — every one a subset of
   `{propext, Classical.choice, Quot.sound}`. Now enforced in CI by
   `scripts/audit_axiom_footprints.py`.
3. **One `native_decide` site**, `docs/erdos/erdos_367.lean` — four anonymous `example`s anchoring
   the `B2` definition. Anonymous, so nothing can reference them; the file's load-bearing content
   is a `Prop` definition carrying no proof. Not a trust path.
4. **No `debug.skipKernelTC` anywhere.** Every `set_option` in the repo is a resource limit.

## The defect: `kernel_verified` did not mean kernel-decided

`LeanVerifier.discharge` — the sole writer, invariant 1 — set the flag from `check_proof` alone,
and `check_proof` was "no error and no sorry". The axiom footprint was a separate call six
providers and the `*_decided` gates each made **by convention**.

This was not a reading. Driven end-to-end through the real promotion path on the pinned
`leibniz-lean-repl:v4.31.0`:

```
theorem margin : False := by
  have hk : slice = "" := by decide         -- the kernel's answer
  have hn : slice ≠ "" := by native_decide  -- the compiler's answer
  exact hn hk

theorem fermat_last (a b c n : Nat) (hn : n > 2) (ha : a > 0) (hb : b > 0) : a^n + b^n ≠ c^n
  := (margin).elim
```

| | before | after (ADR 0097) |
|---|---|---|
| `discharge` | `kernel_verified=True`, `MECHANICAL`, `PASS`, **`Q.E.D.`** | `kernel_verified=False`, `FAIL`, `Q.E.I.` |
| `axiom_closure` on the same proof | `ok=False` | `ok=False` |

The writer was permissive; only the gate was strict. Invariant 7 (`Q.E.D.` iff `kernel_verified`)
held mechanically and therefore vacuously. Fixed by folding the footprint into the backends'
`check_proof` (same round-trip) and making `discharge` fail closed for a backend that does not
assert `enforces_axiom_closure`. Frozen as regressions in `tests/test_native_eval_redteam.py`.

### A second defect, found by attacking the first fix

The footprint check reads `#print axioms <name>`, and `<name>` came from `_NAME_RE.search` over
`theorem_src` — the first `theorem <name>` match *anywhere in the text, comments included*. A
statement opening `-- theorem Nat.add_comm`, proved `by native_decide`, therefore reported on
Mathlib's `Nat.add_comm`: clean, and about a different declaration. On the pin this yielded
`kernel_verified=True` / `Q.E.D.` **and** `axiom_closure(...)["ok"] is True` — it defeated the new
writer-side check and the pre-existing gate together. `theorem_src` is proposer-authored, so it was
reachable.

Fixed by `declaration_name` (nesting-aware comment stripping, keyword must open a line); the unsafe
regex is deleted rather than left available. This was a latent hole in the ADR 0090 extraction that
the new checks inherited — found by attacking the guard, not by re-reading it.

### Adversarial review broke the first fix

The above was then attacked by a skeptic with kernel access (a CLAUDE.md standing gate). It found
three further routes to `kernel_verified=True`, one driven to `theorem catastrophe : False`:

- **`proof_src` can open top-level declarations.** `by native_decide` followed by
  `namespace M / theorem margin : True := trivial` leaves a namespace open, so the appended
  `#print axioms margin` reports on the decoy `M.margin`. Both the writer *and* `axiom_closure`
  passed it. The code comment asserting this was impossible ("a smuggled top-level command would
  be a parse error inside the proof") was false and was the reason nothing guarded `proof_src`.
- **The CLI transport flattened stdout into one message**, so the axiom list was read from the
  first report in the file rather than ours. **This needed no adversary**: an ADR 0062 preamble
  carrying its own `#print axioms` — 16 of the `docs/crt/*.lean` artifacts do — lent its clean
  list to a dirty theorem, and the two transports reached opposite verdicts on identical content.
- **Two honest-proof false-rejects**: a theorem whose *name* contains "sorry" (the name is echoed
  by `#print axioms` and every sorry-scanner was a blind substring test), and `nonrec` /
  universe-annotated declaration names.

All fixed and frozen as regressions; the regression file is now in the kernel lane. Details in
ADR 0097 decisions 4-6. The lesson is the one CLAUDE.md already records: re-reading found none of
this, and the most dangerous of the three was reachable by an *honest* input shape, not a crafted one.

### A second adversarial round broke the fixes again

Decisions 4-6 were attacked in turn and also fell — two more end-to-end routes, and one of the
fixes was itself a regression:

- **The smuggle guard was a column-0 scan.** Lean parses a command at any column, so one leading
  space smuggled the namespace decoy and drove `catastrophe : False` to `Q.E.D.` again.
- **The comment stripper mis-lexed string literals.** `have s : String := "/-"` opened a block
  comment that never closed, blinding the guard to a plain column-0 smuggle. Independent of the
  first, and would have survived an indentation-only fix.
- **Narrowing the `sorry` scan was a regression.** Lean writes the warning with **backticks**, so
  the narrowed regex matched nothing and `check_source("theorem t : 2 + 2 = 5 := by sorry")`
  started returning `True` — the trusted re-check ~20 audit scripts call, and the one path with no
  footprint backstop. A sorry-ed preamble helper also stopped being caught.
- **Per-line splitting broke on Lean's wrapped output.** A long axiom list wraps across lines, so
  the two transports disagreed on identical content in both directions — including a silent
  `Q.E.I.` on an honest 62-character-named proof.

Plus four honest-proof false-rejects and a regressed `python demo.py` (a blocking CI step).

The pattern across both rounds is the useful finding: **every guard that failed was a syntactic
guess about Lean's surface syntax or output format, and every fix that held was structural.** The
check that now does the load-bearing work is `expected_report_names` — a report may qualify our
name only with a namespace the *operator-authored* preamble opened, so a decoy declared by the
*proposer-authored* proof is rejected regardless of what syntax introduced it. The keyword scans
are kept as defence in depth and are explicitly documented as incomplete.

### A third round: the reader never bound the answer to the question

Decisions 7-11 were attacked and broke as well — and the check described as "the structural one
that actually holds" turned out to be the *final step* of the exploit.

A proof can print its own `#print axioms` report (`run_cmd IO.println`, or `dbg_trace` inside the
proof term with no imports and no top-level command at all, so no keyword scan can see it). The
reader matched report-shaped text anywhere in Lean's output, never binding it to the command it had
issued. Add `namespace M` to the proposer-authored `theorem_src` — unguarded, since the smuggle
scan only ever covered `proof_src` — and Lean's genuine report reads `'M.catastrophe'`, which the
qualifier check duly **rejected**, leaving the forgery as the only accepted report.
`kernel_verified=True`, `Q.E.D.`, both transports, both layers, and `Q.E.D.` on **P and ¬P** at once.

Fixed by reading the footprint under an unpredictable probe (`def <probe> := @<name>`, 128 bits
generated after the proof text is fixed), and by guarding `theorem_src` too. The qualifier check
was **deleted** rather than kept: a check that discards true evidence is worse than no check.

**The pattern across all three rounds is the finding worth keeping.** Every guard that failed was a
syntactic guess — about Lean's surface syntax, its output format, or which names were legitimate —
and every one was bypassed by an input its author had not imagined. The check that holds asks a
question the adversary cannot answer in advance. Guards that must stay syntactic are documented as
defence in depth and are not relied upon.

### A fourth round: the proof can redefine the answerer

Decisions 12-13 broke too. `proof_src` could redefine the `#print axioms` command elaborator via
`elab_rules`, matching `$i:ident` — so it never needed to know the probe name, and the 128-bit
nonce was irrelevant. `theorem rp_margin : False` came back `Q.E.D.` on the CLI backend.
Extending the keyword list does not fix it (verified: the same hijack on one line still slips
past the `open ... in` exemption).

Fixed by confining the proof to a **parenthesised term position**, where Lean commands are a
parse error, plus a delimiter-depth check so the wrapper cannot be closed early. Honest proof
shapes verified unaffected.

### Where eight rounds left it

| class | status |
|---|---|
| axiom footprint (`native_decide`, admitted axioms, `sorry`) | **CLOSED**, measured with every syntactic guard disabled |
| kernel bypass (`debug.skipKernelTC` + an `unsafe` self-loop) | **OPEN** — not closable by inspecting text |
| statement meaning (`notation "False" => True` in a preamble) | **OPEN** — a preamble-trust decision |

The kernel-bypass class is open *in principle*, not by oversight: a `run_cmd` can assemble the
option name from fragments at elaboration time, so there is no string for any scan to match. It
needs `lean4checker` (stuck at v4.29 against the v4.34.0-rc2 pin) or a confined preamble. Both open
classes are pinned as strict-xfail regressions so a future fix cannot land unnoticed.

## A denylist could not have caught this

Measured on the pin: the footprint of a `native_decide` proof is
**`<theorem>._native.native_decide.ax_1`** — auto-generated, named after the theorem
(leanprover/lean4#12216: since 4.29, one generated axiom per computation). `Lean.ofReduceBool` and
`Lean.trustCompiler` never appear. `STD_AXIOMS` being an **allowlist** is the only reason anything
saw it.

Two test assertions were written as denylists and are corrected:

- `tests/test_covering10080_law.py` — `"Lean.ofReduceBool" not in ax["axioms"]` can never match on
  this toolchain. Harmless (the preceding `ax["ok"]` is the real check) but it read as protection
  it did not provide. Now asserts `set(ax["axioms"]) <= STD_AXIOMS`.
- `tests/test_ziegler_counterexample.py` — scanned joined *message text* for `"sorryAx"` /
  `"native_decide"` on a response that carried **no `#print axioms` report at all**, so it asserted
  almost nothing about axioms. Now requests the footprint and holds it to the allowlist.
  (Note: the substring `native_decide` *does* occur inside the generated axiom name on 4.31, so
  that clause was accidentally load-bearing rather than strictly vacuous — but only by accident of
  Lean's current spelling.)

## Still open

- **The pin is inside the affected range.** `lean-project/lean-toolchain`, both Dockerfiles and the
  `REPL_IMAGE` / `DEFAULT_IMAGE` constants point at 4.31.0. Verified viable target: **4.34.0-rc2** —
  `leanprover-community/repl` carries that tag and Mathlib master is on that toolchain. Deferred as
  its own unit of work because it needs two ~11 GB image rebuilds and carries Mathlib churn.
  ADR 0097 removes *reachability* through the trust boundary; it does not patch the toolchain.
- **`set_option debug.skipKernelTC true` in an ADR 0062 preamble is unguarded.** It produces no
  axiom at all, so a clean footprint would not prove the kernel ran. No exploit was constructed on
  4.31 (both attempts failed at elaboration, before the option matters) and it appears nowhere in
  the repo. Recorded, not fixed on speculation.
- **`erdos_367.lean`'s four `native_decide` anchors** are compiler-trust evidence, not kernel
  evidence. Contained and documented; the word "anchor" overstates them post-bug.

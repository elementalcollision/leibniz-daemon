# ADR 0099 — a clean axiom closure is not a true statement

**Status:** **BUILT** (a hash pin, plus a best-effort lint) and **DEFERRED** (the real closure).
`scripts/audit_preamble_constructs.py` is a blocking CI step over operator-authored preambles at
rest. The statement-meaning class is **not closed** and stays marked open by a strict xfail. The
trust boundary is untouched: `trust.py`, `verifiers.py` and `tests/test_invariants.py` are
byte-identical.

**Amends ADR 0062.** This supersedes one bullet of ADR 0062's soundness argument; ADR 0062 is left
as the historical record.

## Context — what ADR 0097 and ADR 0098 closed, and the shape of what they did not

ADR 0097 made `kernel_verified` mean *axiom-checked* via a compiled reporter the proposer cannot
reach. ADR 0098 added a `lean4checker` replay, closing the kernel-bypass class. Neither answers a
third question, and no kernel check can: a preamble that changes what the statement *means* leaves
every layer reporting honestly, because the kernel proved exactly the proposition it was handed.

## What ADR 0062 got wrong

> **Re-checked in full.** `axiom_closure` elaborates `preamble ⊕ theorem_src ⊕ proof` and rejects any
> `sorryAx` / `native_decide` / axiom outside the allowed set — so a hole or smuggled axiom **in the
> preamble** fails the honesty gate exactly as one in the proof would.

For an **axiom**, true, and ADR 0097 strengthened it. For a **notation**, false, and *"exactly as"* is
the load-bearing overstatement: the honesty gate inspects the axiom closure, and a notation
redefinition never enters one.

Measured on `leanprover/lean4:v4.34.0-rc2`, with `theorem oops : False := trivial` appended exactly
as `_join_proof` appends it:

| preamble | result | `#print axioms` |
|---|---|---|
| `notation "False" => True` | **elaborates** | *does not depend on any axioms* |
| `namespace Foo` / `def False := True` (unclosed) | **elaborates** | *does not depend on any axioms* |
| same, closed with `end Foo` | **type error** | — |

The closure is **empty** — not even `propext` — so by the only measure ADR 0097 applies the exploit is
*cleaner than a legitimate proof*. There is no axiom to catch. This is not a checker defect.

## How exposed this actually is

Settled by execution, not inferred:

| question | method | result |
|---|---|---|
| Does any proposer path write `Expressio.preamble`? | every assignment in `leibniz/` | **No.** Only `scripts/export_*_law.py` and tests. |
| Do the live laws use meaning-changing constructs? | audit of all 11 published preambles | **No.** `maxHeartbeats` / `maxRecDepth` only. |
| What commands does the corpus use? | token census | six: `def`, `theorem`, `abbrev`, `namespace`, `end`, `set_option`. |

ADR 0062's *"never proposer-populated"* holds as an **observed fact**, but it is a convention, not a
structural guard — the ADR 0096 shape, where the sole kernel writer was not the sole checker. The
exploit requires an operator-authored export script to smuggle a redefinition past its own author.

## Decision — pin the data; lint as an aid; do not claim the class is closed

**The pin is the enforcement.** Every non-empty preamble is hashed into
`docs/audits/preamble-pins.json`. A new or altered preamble fails CI until an operator regenerates
the pins (`--update-pins`), which is a reviewed act. The pin makes **no claim about Lean's grammar**,
so it holds however badly the lint is fooled. What makes a preamble safe is a human reading it once;
the pin is what makes "once" stick.

**The lint is an authoring aid.** Allowlisted commands (from the census), a denylist of Lean command
keywords, resource-only `set_option`, scope balance, and core-name shadowing. It catches the common
mistake where it is cheapest to fix. It is explicitly **not sound**.

### The first version of this lint was broken, and that is the useful part of this ADR

Adversarial review (CLAUDE.md's standing gate) found **seven working bypasses** of the lint as first
written — each reported CLEAN *and* confirmed against real Lean. Five distinct root causes:

| # | root cause | how it got in |
|---|---|---|
| A | the comment stripper desynced from Lean's lexer (`«z/-»`, `s!"{"/-"}"`) | a construct nobody considered |
| B | scope balance was a **line-anchored count** — an indented `section`, a mid-line `namespace`, or an `end` inside a string all defeated it | scanning by position |
| C | the core-name check could not see `«False»`, which **is** the name `False` | regex predated guillemets |
| D | the command scan **skipped indented lines** — its own `axiom` test case died to one leading space | scanning by position |
| E | `CORE_NAMES` omitted `Nat`; the ADR had called this gap "a Mathlib name", and it is core Lean | an allowlist of names cannot be complete |

Three of the five are the *same mistake*: scanning Lean by line position, which ADR 0097 round 4
already recorded as wrong ("Lean parses a command at any column"). I wrote that lesson into this
lint's comments and then violated it two checks later. Scanning is now by **token**, never by column.

The honest reading is that a syntactic lint over Lean source is worth having and worth nothing to
rely on — which is why the enforcement is a hash, and why the class stays open.

### The review also found a defect in shipped code — fixed in ADR 0097, not here

`_strip_comments` is shared by five guards, two of them scanning **proposer-authored** text. Lean
lexes `def «z/-» := 1` as one identifier; the stripper treated `«` as punctuation, let the `/-`
inside the name open a block comment, and returned `def «z`, blinding every guard below it.

That is a defect in the guards, not in this audit, so **the fix lands with ADR 0097 where the guards
live** (rounds 9 and 9b there), rather than riding on the branch that happened to find it. A second
adversarial round then broke the round-9 fix — `_lex` did not know character literals — and in one
direction it made the new fail-closed check **refuse an honest law**. Both are recorded in ADR 0097;
the lesson worth repeating here is that the fix for a review finding needs the same review the
original code got.

### The second round also broke this audit's collection

Two bugs in `collect()`, each defeating the pin *and* the lint at once by making a preamble invisible
to both while it still reached the kernel:

- **Multiple preambles per file collapsed to the last.** It keyed by file path — contradicting its own
  docstring. A ledger-shaped `{"laws": [{"preamble": <hostile>}, {"preamble": <benign>}]}` kept only
  the benign one. Latent today (law files hold one preamble each), live the moment any audited
  artifact holds two.
- **A nested `preamble` key overwrote the law's own.** `law_payload` emits `novelty_attestation` and
  `figures` sub-objects; a `preamble` inside either silently repointed the pin at benign text.

Both fixed by keying on the JSON **path**. Path and not content hash, so that editing a preamble keeps
its key and reports as a `PIN MISMATCH` — a content key would make every edit read as a new preamble
plus a stale pin, and the mismatch that catches a silent edit could never fire.

### What this is not

A lint over operator data at rest plus a hash pin. It catches accidents and silent edits. It does
**not** stop an operator determined to defeat an audit they maintain, and nothing consults it at the
mint. `tests/test_native_eval_redteam.py` **keeps its strict xfail**. A passing audit must not be read
as the class being closed.

Stated limitations:

- **String literals are not stripped for the keyword scan**, so `def m : String := "open ..."` raises a
  false finding. Deliberate: a false positive costs a one-line conversation; a string-scanner that
  mis-parses one raw string (ADR 0097 round 5) misses silently. Balance counting *does* strip strings,
  because an `end` inside a literal is not a command — that was bypass B3.
- **`CORE_NAMES` cannot be completed by adding names.** The sound check is "declares nothing that
  already resolves", i.e. the deferred `Environment` diff.
- **The denylist of command keywords cannot be complete.** The pin is what does not depend on it.
- **Scope.** `collect()` walks `*.json` **in this repo only**. The published ledger lives in the
  sibling `codex-calculemus` repo (`ledger/calculemus.json`, per `export_calculemus.py`) and is not
  scanned here; neither are `.leibniz/memory.db`, `.jsonl` journals, or `.md` queues. This audit
  covers the law artifacts committed here, and says nothing about the rest.

### Why not the real closure

The kernel-level answer is an `Environment` diff across the preamble — refuse if it declares notation
or syntax, or introduces a constant shadowing an existing name. That is the *"AST/`Environment` diff
guard"* **deferred in ADR 0045 §10**; reopening a deferred decision costs a design round plus its own
adversarial rounds. Given the measurement — not proposer-reachable, corpus clean, now pinned — that
cost is not justified yet. **Re-open gate:** build it if any proposer-facing path gains the ability to
populate `preamble`, or if a preamble is ever authored by anything but an operator's export script.

## Evidence

- `tests/test_preamble_construct_audit.py` — 33 tests. All **seven bypasses** pinned as regressions,
  eleven preambles that must be refused, six that must pass (including the wrapped declarations a
  positional scan flagged), the pin manifest, a tamper case the lint is *blind* to and the pin
  catches, and a vacuity check (`preambles checked: 0` and `pinned: 0` both fail).
  The four `collect()` regressions pin the multi-law and nested-key shapes, and assert that
  whatever is collected is also linted.
- `tests/test_lexer_desync_guards.py` (on the ADR 0097 branch) — the shared-lexer fix.
- Live corpus: **11 preambles checked, 11 lint-clean, 11 pinned, 0 findings.**

## Consequences

- A meaning-changing construct in a published law fails CI; a silent edit to any pinned preamble
  fails CI even when the lint cannot see it.
- The statement-meaning class stays **open and marked open**, in this ADR and in a strict xfail.
- ADR 0062's "exactly as one in the proof would" no longer stands unqualified.
- Two instances of the standing pattern in one ADR. ADR 0062's bullet was written as an argument and
  held for 37 ADRs without anyone running it. And the lint written to check it repeated, in its own
  comments' words, a lesson recorded two ADRs earlier — *an argument that has not been attacked is a
  guess, including when the author has just finished writing down why.*

# ADR 0089 — Two fail-open guards: require the axiom line, and check coverage semantically

- Status: **accepted — landed, reviewed, and one decision refuted by its own test**
- Date: 2026-09-05
- Depends on: ADR 0088 (whose adversarial review surfaced both), ADR 0062 (the axiom-closure
  contract), ADR 0060 (the fragment whose non-triviality guard this concerns), ADR 0013 (kernel
  provenance)

## Context

ADR 0088's adversarial review turned up two guards that report OK **without having checked the
thing they are named for**. They sit at different layers and have nothing to do with each other
mechanically, but they are the same defect shape — a check whose success path can be reached
without evidence — so they are decided together and should be attacked together.

Neither was introduced by ADR 0088. Both were found only because that change was reviewed rather
than reasoned about, which is the argument for the standing gate.

## Decision 1 — `axiom_closure` must require the evidence it exists to read

`leibniz/backends/lean_axioms.py::axiom_closure` scans the REPL's messages for a
`depends on axioms:` line, and **never asserts it saw one**. Reproduced against a REPL that
answers `{"messages": []}`:

```
theorem bogus : 1 = 2 := by sorry
  ->  ok = True     axioms = []     has_sorry = False
```

`ok` is computed as `not errors and not has_sorry and not extra`. With no messages, all three are
vacuously satisfied and a **false theorem proved `by sorry` passes**. `decide_certificate` gates
every one of its four legs on `check_proof` **and** `axiom_closure`, so this is the whole
faithfulness certificate, and `LeanVerifier.discharge` would stamp `kernel_verified` — CLAUDE.md
invariant 1, reached by infrastructure degradation rather than by any gate being wrong.

**Fix:** `ok` additionally requires `axioms` to be non-empty. `axiom_closure` always appends
`#print axioms <name>`, which always emits on success, so an empty message list means something is
wrong and must never be a PASS.

**Scoping, which matters:** the review reported that `_kernel_ok` passes on the same response and
so "all four legs would PASS". True, but the fix must **not** be applied there. A clean
elaboration legitimately emits no messages at all (`theorem t : True := by trivial`), so requiring
messages in `_kernel_ok` would reject every valid proof. Only `axiom_closure` has a guaranteed
output, and since it gates each leg, tightening it alone closes the hole.

**How reachable is it?** Narrower than it first appears: `_env_for` already probes each new env
with a canary precisely because this REPL is documented to swallow a failed umbrella import and
return "a coreless env with no error". That guards the known path. What remains is that the
function is fail-open *by construction* — any other route to an empty response is an accepted
proof — and a guard on the trust boundary should not depend on every such route having been
enumerated.

## Decision 2 — non-triviality for covering systems must be semantic, not propositional

ADR 0088's `_mixed_content_free` matches `boolean_decided._content_free` exactly (differential
tested: 2497 flat formulas below the branch point, 400 above it, 4000 in a monotonicity diff —
zero disagreements, zero cases admitting what the old guard rejected, zero regressions). That is
the wrong thing to be exactly right about. **Both** guards are purely propositional, and the
family ADR 0088 exists to admit is exactly where that stops being the relevant notion:

```
(n%4==0) ∨ (n%4==1) ∨ (n%4==2) ∨ (n%4==3) ∨ (n%9==0) ∨ (n%9==1) ∨ (n%9==2)
  ∨ (n%6==5) ∨ (n%8==7) ∨ (n%12==11)
```

classifies (M=72, 10 atoms). The first four atoms already cover ℤ; the rest is padding. It is
**true**, so the kernel accepts it, and it promulgates as a law carrying no content. Propositionally
it is not constant — the atoms are independent boolean variables — so neither guard has anything to
say. Pre-existing in kind, but ADR 0088 is what makes the shape reachable at scale, and a daemon
whose binding constraint is novelty should not be manufacturing padded restatements of `n mod 4`.

### The criterion this ADR first specified, and why it is wrong

The original decision was: *reject a covering formula that is not minimal* — build a
coverage-count array over `Z/M`, call atom *i* redundant iff every residue it covers has count
≥ 2, and reject if the formula covers and any atom is redundant. `O(M·k)`, exact, cheap.

**It was implemented and then refuted by the first test written against it.** arXiv 2607.19029 §7
— the published, distinct, minimum-modulus-7, lcm-10080 covering system this entire line of work
exists to admit — **contains a redundant congruence**. Drop `233 (mod 1120)` and the remaining 65
still cover ℤ, still have distinct moduli, minimum modulus 7, and lcm 10080. Verified exhaustively,
and verified again by re-deriving coverage after the drop.

This is **not an error in the paper**. Its theorem is `L_min(7) = 10080` — a statement about the
minimal *least common multiple*, not a claim that the exhibited witness is irredundant. Nothing in
the paper is weakened by it.

What it does refute is the criterion: **redundancy does not imply absence of content.** A covering
system with a droppable congruence still witnesses the existence claim that carries the
mathematics. Shipped, this would have rejected the target of the whole exercise — as a
"content-free" law.

**The criterion that landed instead:** reject when some modulus appears with **all** of its
residues. That is literally the tautology "every integer has some residue mod m", padded with
filler, and it is the actual pathology in the motivating example. It is `O(k)` — no arithmetic
over `Z/M` at all — and it **cannot fire on a distinct covering system**, because a full residue
block needs one modulus repeated *m* times. That impossibility is the property the redundancy test
lacked, and it is what makes the guard safe to point at this family.

It is deliberately weaker: a formula can be padded without any modulus carrying a full residue set,
and this will admit it. That is the right direction. The demonstrated cost of the aggressive
criterion was rejecting a published theorem's witness; the cost of the narrow one is admitting some
padding the kernel will happily prove. Narrow it further only against real instances.

**This is a new guard, not a cap change** — which is why it is here and not folded into ADR 0088.
It can only *narrow* the fragment, so its failure direction is closed, but it changes what
promulgates and therefore wants its own measurements against the live ledger.

## Adversarial review

Run against the finished implementation, per the standing gate. It found **five** defects. The two
high-severity ones are the kind that reasoning does not catch: both are about where a fix was
applied, not whether it was correct.

**1. The fix went to one of two copies, and the publish gate kept the hole.**
`leibniz/backends/lean_axioms.py`'s own docstring says it exists so the faithfulness-time and
publish-time checks run "the SAME code ... not two drifting copies". They had drifted, and
hardening the library copy made them drift further: `scripts/export_calculemus.py` carried a
verbatim old `axiom_closure`, and that is `check_ledger`'s H0 gate — the "honesty gate" the ADR
0033 publish act requires. It still returned `ok: True` for `theorem bogus : 1 = 2 := by sorry`
against a silent REPL, so the ledger would print VERIFIED. Worse, `tests/test_axiom_closure.py`
loads the *scripts* copy, so the existing H0 test pinned the unfixed one while the new tests pinned
the fixed one, and nothing compared them. The duplicate is now **deleted and re-exported** from the
shared module rather than patched, so it cannot drift a third time. (A third open-coded copy in
`scripts/counterexample_domain.py` is audit-only and left as recorded work.)

**2. The new guard was unreachable at the sizes that matter.** `_padded_covering` was called only
from the `> 8` atom branch, so below nine atoms `_mixed_content_free` delegated to the purely
propositional `_content_free`, which cannot see a full residue block. This ADR's own example family
sailed through at 3, 4, 5 and 8 atoms — the sizes the conjecturer most often emits and the kernel
is cheapest to accept. `boolean_decided` refuses the same shape on a single modulus, so the mixed
gate was **laxer than its sibling** on the pathology it had just been hardened against. The check
is `O(k)` and sound at any size; it now runs at every atom count, before the branch.

The new test had concealed it: the small case was asserted against `_padded_covering` directly
while the only end-to-end assertion used the 10-atom example. Testing a helper instead of the gate
is how a guard passes its own tests without being reachable.

**3. Evadable by one token.** Requiring *every* atom to be `==` meant appending a single unrelated
`!=` atom slipped a padded formula through. A complete residue system among the `==` atoms is a
tautology over ℤ regardless of what else is disjoined, so the check now reads only those.

The review also raised splitting a residue class to a finer modulus (`(n%8==0..6) ∨ (n%16==7) ∨
(n%16==15)`) as an evasion. **Not adopted.** That is a valid covering system, and so is the arXiv
paper's; nothing structural separates "trivial covering system" from "interesting" one. That is a
novelty question, and the redundancy refutation above is exactly what over-reaching here costs.

**4. A namespaced declaration was a latent false-DEFER** (not live today, but one authoring choice
away). Lean prints the fully qualified name while `_NAME_RE` reads the short one from the source —
this repo's own recorded output contains both forms. An ADR 0062 preamble that opens a namespace
would have turned a clean footprint into a silent DEFER. The report matcher now allows an optional
qualifier.

**5. Two asymmetries worth closing.** `has_sorry` scanned only *errors* while `_kernel_ok` scans
every message, and Lean reports `declaration uses 'sorry'` as a WARNING — so this check was the
laxer of the two it exists to reinforce. And the axiom list was extracted name-blind, so a
preamble's own `#print axioms` (16 of the `docs/crt/*.lean` artifacts have one, and
steiner/double_blocking ride in as whole-artifact preambles) could be handed back as our theorem's
footprint. Both the report match and the extraction are now bound to the theorem's own name.

The review's remaining finding — that a multi-declaration `theorem_src` could report on the wrong
declaration — is recorded and not fixed: every call site feeds machine-generated single-declaration
sources and runs `check_proof` first. It becomes live the moment an LLM-authored `theorem_src`
reaches `axiom_closure`.

## Consequences

Decision 1 is a strengthening of the trust boundary: strictly fewer things pass, and the thing it
newly refuses is a certificate nobody should ever have accepted. `TrustPolicy.validate_path` and
`tests/test_invariants.py` are untouched. It needs a test pinning the silent-REPL response as a
FAIL, and a check that no legitimate proof regresses — the whole `LEIBNIZ_LEAN_E2E` battery is the
regression suite.

Decision 2 narrows the mixed fragment. The padded example classifies as `None`; the arXiv
2607.19029 system and ADR 0088's lcm-2520 fixture still classify — pinned by test.

The parenthetical in this ADR's first draft read: *"its moduli are exactly the 66 divisors of 10080
that are ≥ 7 — nothing is droppable, so it is minimal by construction, but that is an assertion to
TEST, not to assume."* Tested, it was false: `233 (mod 1120)` is droppable. The instinct to write
the caveat was right and the guess inside it was wrong, which is the whole argument for writing
guesses down as tests rather than as prose.

**What this does not do:** it does not touch `MAX_NODES`, so the motivating paper stays unreachable
through the DSL — still its own decision. It does not enumerate the other routes to an empty REPL
response; it removes the need to. And neither fix should be declared sound on the strength of this
document — both get attacked before they land, on the ADR 0088 precedent, where reasoning missed
two defects that a mutation and a wiring trace caught.

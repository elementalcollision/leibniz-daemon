# ADR 0089 — Two fail-open guards: require the axiom line, and check coverage semantically

- Status: **proposed — reproduced, not yet landed**
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

**Fix:** in the flat-Or branch, reject a covering formula that is not minimal. In that branch
`M ≤ MAX_LCM = 20160`, so this is exact and cheap:

1. build a coverage-count array over `Z/M` — one pass, `O(M·k)`;
2. atom *i* is **redundant** iff every residue it covers has count ≥ 2;
3. if the formula covers `Z/M` and any atom is redundant, it carries no content ⇒ REJECT.

`O(M·k)` is ~1.45M operations at the worst admissible shape (M=20160, k=72), against a `decide`
that already costs seconds. Naively re-testing coverage per dropped atom would be `O(M·k²)` and is
not worth it. A formula that does **not** cover `Z/M` needs no check: it is false, and the kernel
refuses it.

**This is a new guard, not a cap change** — which is why it is here and not folded into ADR 0088.
It can only *narrow* the fragment, so its failure direction is closed, but it changes what
promulgates and therefore wants its own measurements against the live ledger.

## Consequences

Decision 1 is a strengthening of the trust boundary: strictly fewer things pass, and the thing it
newly refuses is a certificate nobody should ever have accepted. `TrustPolicy.validate_path` and
`tests/test_invariants.py` are untouched. It needs a test pinning the silent-REPL response as a
FAIL, and a check that no legitimate proof regresses — the whole `LEIBNIZ_LEAN_E2E` battery is the
regression suite.

Decision 2 narrows the mixed fragment. The padded example above must classify as `None`; the real
arXiv 2607.19029 system must still classify (its moduli are exactly the 66 divisors of 10080 that
are ≥ 7 — nothing is droppable, so it is minimal by construction, but that is an assertion to
TEST, not to assume).

**What this does not do:** it does not touch `MAX_NODES`, so the motivating paper stays unreachable
through the DSL — still its own decision. It does not enumerate the other routes to an empty REPL
response; it removes the need to. And neither fix should be declared sound on the strength of this
document — both get attacked before they land, on the ADR 0088 precedent, where reasoning missed
two defects that a mutation and a wiring trace caught.

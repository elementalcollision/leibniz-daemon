# ADR 0090 — Bound what the predicate guard admits, then widen it

- Status: **accepted — landed, measured against live Lean 4.31, adversarially reviewed**
- Date: 2026-09-07
- Depends on: ADR 0088 (whose caps this unblocks), ADR 0089 (the fail-open lineage this continues),
  ADR 0061 (the vacuity kill that was silently disabled), ADR 0004 (the gaming spine the defect
  reached), ADR 0035/0066 (the bounded encodings the node cap still bounds)

## Context

ADR 0088 widened the mixed-modulus fragment to admit covering systems and then could not use it:
`smt_z3.MAX_NODES = 200` refused the motivating target — arXiv 2607.19029 §7, 531 AST nodes — at
the *parse* boundary, before any gate saw it, and made `MIXED_MAX_ATOMS = 72` dead code. That ADR
deliberately declined to raise the cap, on the grounds that it guards untrusted input and deserved
its own decision and its own skeptic.

It got both. The investigation found that raising the number was the least important thing in the
question, because **the cap was the wrong instrument and two live defects were sitting behind it**.

## Decision 1 — bound the COST, which is what a hostile predicate spends

`MAX_NODES` counts AST nodes. It never bounded the cost of what it admits. `_conv` expands `a**k`
into a literal product of k copies of `a`, and it validates `k <= MAX_POW` on each `Pow` node
**individually**, so nesting composes multiplicatively:

```
((((((((((n)**8)**8)**8)**8)**8)**8)**8)**8)**8)**8 > 0     # 36 nodes, 55 chars, degree 8**10
```

Three AST nodes and five characters per level. The shipped cap admitted ~65 levels — expanded size
on the order of 10^68. Measured on the real code path at the shipped cap:

| L | nodes | chars | wall | peak RSS |
|---|---|---|---|---|
| 6 | 24 | 35 | 0.06 s | 76 MB |
| 7 | 27 | 40 | 0.49 s | 262 MB |
| 8 | 30 | 45 | 3.90 s | 1766 MB |
| 10 | 36 | 55 | **process dead** | — |

It reached `SMTVerifier.cheap_refute` — the **first** gate — and `find_gaming_witness`, the ADR 0004
faithfulness spine. Death is by *signal*, so no `except Exception` catches it, and the nightly
launchd beat has no `KeepAlive`: one hostile `claim_property` ends the cycle with nothing in the
journal to explain it. `encodable()` returns `True` in 2 ms without building the term, so the
screening check says yes and the solve is what explodes.

**`MAX_EXPANDED = 4096`** bounds the expanded term size `_conv` will build. The value is measured,
not judged: over **545 predicates harvested from this repo**, expanded size has median 9 and
maximum 51, so the bound is ~80x the observed maximum and refuses the attack from L=4 (8778)
upward. `expanded_size()` saturates at the cap — the check must never become the DoS, and `8**65`
must never be evaluated exactly.

## Decision 2 — cap the source before `ast.parse`, which dies first

`ast.parse` raises `MemoryError("Parser stack overflowed")` on deeply nested source **before any
node count exists to check**, and `MemoryError` is neither `SyntaxError` nor `ValueError`, so it
escaped every guard. Bisected exactly: 5975 unary minuses were refused correctly; **5976** raised
out of `Z3Backend.encodable`, `dsl_to_lean.render_pred`, and both `structural` entry points.
Nothing length-capped the LLM-authored predicate fields anywhere. **`MAX_SRC_CHARS = 4000`**.

Stated plainly because it was mutation-checked: the accompanying `except MemoryError` clause is
**not** load-bearing and is not the fix. Within 4000 chars no shape reaches `ast.parse`'s limits
(3950 unary minuses parse; 950 `not`s parse; nested parens hit Python's own `SyntaxError` at 250).
The length cap does the work. The clause stays as defence in depth for shapes not enumerated —
"I could not construct one" is not "none exists" — and the code comment and test docstring both say
so, so nobody later mistakes it for the guard.

## Decision 3 — one guard, because this is the fourth drifting copy

`structural.py` carried its own `MAX_NODES = 200  # bound the AST against adversarial input
(matches smt_z3)`. "(matches smt_z3)" was a **comment asserting a coupling that did not exist** —
the same shape as the four copies of the axiom check that ADR 0089 and the commit before this one
spent their length closing.

It mattered, because both `structural` consumers fail **open** above their cap:
`is_coefficient_degenerate` returns `False` ("keep content") and `congruence_signature` returns
`None` ("stays NOVEL"). A copy silently lagging `smt_z3` opens a band where the ADR 0061 vacuity
kill and the novelty signature both go quiet on exactly the claims that just became reachable.
Measured: a 213-node vacuous, variable-independent conjunction reports `degenerate=False` at cap
200 and `True` at 600.

All three parse sites — Z3 backend, Lean renderer, structural signatures — now route through one
`smt_z3.guard_source()`, which carries the `^`→`**` rewrite, the length cap, the node cap and the
expansion cap together. The test asserts **object identity**, not equality, so a future copy cannot
drift without going red.

## Decision 4 — and only now, raise `MAX_NODES` to 600

A flat disjunction of `k` modular atoms is exactly **8k+3** nodes. So the old cap admitted 24
congruences while the fragment's own semantic caps allowed 72 — the guard bound the fragment more
tightly than the fragment did, and `MIXED_MAX_ATOMS = 72` was unreachable by construction.

| k | 2 | 18 | 24 | 25 | 66 | 72 | 74 | 75 |
|---|---|---|---|---|---|---|---|---|
| nodes | 19 | 147 | 195 | 203 | **531** | **579** | 595 | 603 |

531 is the target. 579 is the floor that makes `MIXED_MAX_ATOMS` reachable. **600** admits 74,
clearing that floor with two congruences of slack.

This is safe to widen **only because Decision 1 exists**. Raising a size cap while cost rode on
nesting depth would have widened the blowup surface rather than the fragment.

## Evidence

End to end on live Lean 4.31, after all four decisions:

```
classify_mixed(arXiv 2607.19029 §7)  -> M=10080, 66 atoms
render_pred                          -> 1712 chars
decide_certificate                   -> ok=True,  29.6 s
near-miss control (one class open)   -> ok=False, 29.4 s, "kernel did not accept property"
congruence_signature                 -> a real signature (novelty no longer blind to it)
is_coefficient_degenerate @213 nodes -> True (the ADR 0061 fail-open band is closed)
```

The DoS, after: every depth L=6..65 refuses in 0.00 s / 50 MB at both gates it previously reached.
Suite: 1829 passed. Mutation-checked: removing the expansion guard turns two tests red.

## Consequences

The daemon can, for the first time, be *posed* the claim ADR 0088 taught it to decide. The
amplification is unblocked.

**No trust surface.** Every change here only narrows what is accepted, except the node cap, which
widens what is *attempted* while the kernel still decides everything. `TrustPolicy.validate_path`,
`tests/test_invariants.py` and `verifiers.py` are untouched; `kernel_verified` is still written
only in `LeanVerifier.discharge`.

**What this does not do:**

- It does not bound the ADR 0066 `factorial`/`gcd` If-table expansion, whose cost is O(bound²) per
  call and is not visible to `expanded_size`. The node cap bounds the *number* of such calls and
  nothing bounds their product. Untouched, pre-existing, and the next thing a skeptic should attack.
- `compile_pred` still runs **outside** every timeout — `solver.set("timeout", …)` is set after it.
  A ≤600-node predicate was measured at 5.15 s of untimed compile on the gcd-table shape.
- `MIXED_MAX_ATOMS = 72` at `M = 20160` is now reachable for the first time; ADR 0088's live-kernel
  figures are at 66 atoms / M=10080. That corner is unmeasured.
- A caution for anything measuring this repo: `import leibniz` resolves to the editable install —
  a **different checkout** — from any cwd outside the worktree. It produced a false "the fix does
  not work" reading during this very change, and `scripts/counterexample_domain.py` had been
  publishing records under it. Pin `PYTHONPATH`, or run from the worktree root.

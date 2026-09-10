# ADR 0096 — The sole writer was never the sole checker: `kernel_verified` must mean axiom-checked

- Status: **proposed — the gap is reproduced live and measured against the whole ledger; no fix
  landed, and two build obligations must be met before one can be**
- Date: 2026-09-10
- Depends on: ADR 0001 (the charter's trust hierarchy; invariant 8 is CLAUDE.md's, enforced through
  the ADR 0056/0062/0089 axiom lineage), ADR 0013 (the producer and `TrustTier.MECHANICAL` on the
  proof edge), ADR 0029 (the repair panel, one of the three LLM-authored discharge sites), ADR 0056
  (`axiom_closure` on the faithfulness path — the decision this extends to the proof path), ADR 0089
  (the fail-open lineage and the `saw_axiom_report` hardening), ADR 0095 (the work that surfaced this)

## Context

CLAUDE.md states two invariants that this ADR exists because the code does not enforce:

> 7. `Q.E.D.` is stamped iff `kernel_verified`. Never hand-set it.
> 8. **Kernel hygiene.** `native_decide` is forbidden; `sorry`, admitted lemmas and unaudited axioms
>    are never a kernel decision.

Invariant 7 holds. Invariant 8 does not hold on the path that mints `kernel_verified`:

```
LeanVerifier.discharge(expr, demo)  with  demo.proof_src = "by native_decide"
  -> kernel_verified=True   qed='Q.E.D.'   verdict=Verdict.PASS   tier=TrustTier.MECHANICAL
axiom_closure(backend, same theorem_src, same proof_src, same imports)
  -> ok=False   extra_axioms=['nd_probe._native.native_decide.ax_1']
```

Two mechanical checks, same kernel, same source, disagreeing — and only the weaker one gates the
Codex. A `native_decide` result is a decision by the *compiled evaluator*, not by the kernel; calling
it `kernel_verified` and stamping `Q.E.D.` is the claim the charter forbids. The proof prompt makes
the same false promise: `Role.PROOF_DRAFT` carries no prohibition on `native_decide`, and all three
provider `_PROOF_SYSTEM` constants close with *"You PROPOSE; a Lean kernel DECIDES."*

## The gap — what the sole-writer guard actually binds

`tests/test_kernel_verified_writers.py` is doing its job. It enforces **who may write**
`kernel_verified`, whitelisting `LeanVerifier::discharge` (mints) and `runtime._row_to_prop`
(replays). It says nothing about **what the written value is computed from** — and the whole defect
lives inside the whitelisted site, so the guard passes unchanged through it and would keep passing if
`discharge` were weakened further. The predicate at `verifiers.py:63-64` is
`ok = bool(demo.proof_src) and self.backend.check_proof(...)`, and `check_proof` bottoms out in
`_kernel_ok` (`lean_repl.py:191-198`; `lean_cli.py:119-121` is identical) — a text scan for
`severity == "error"` and the substring `sorry`. No `#print axioms`, on either backend.

Nothing downstream re-checks: `VerificationGate.is_promotable` validates edges, the trust policy and
the ADR 0079 canonical-statement binding, but no axioms; `Calculemus.promulgate` (`calculemus.py:61`)
admits on `kernel_verified and qed == "Q.E.D."` alone. `axiom_closure` *does* run, in three
categories of site (~18 calls, mostly operator exports doing discharge-then-check by hand) — and the
shape of that list is the point:

| where | covers | reaches the general proof path? |
|---|---|---|
| the six `*_decided` faithfulness fragments | their own kernel-decided reductions | no |
| the six provider fast-paths | their own template-generated `decide` proofs | no |
| `export_calculemus.py:98-102` (`clean = ok and ax["ok"]`) | publication | no — after the Codex |

The three discharge sites taking an **LLM-authored** `proof_src` — `pipeline.py:197`,
`consensus.py:112`, `proof_repair.py:115` — are precisely the three with no axiom check anywhere
between the kernel call and the Codex.

## Has it bitten?

No. Against the live ledger (`.leibniz/memory.db`, 453 rows, read-only): 64 rows have
`kernel_verified=1` (63 promulgated), and **0** contain `native_decide`, `ofReduceBool`, `sorry` or
`admit` in `proof_src`. Every tactic present is kernel-legitimate — counting each row once per tactic
occurring in it: `rw` 44, `decide` 34, `simpa` 33, `push_cast` 32, `simp` 22, `omega` 19, `ring` 10,
`norm_num` 9, `nlinarith` 4.

The publish gate is why nothing unsound reached the *public site*. It does not explain the Codex
being clean, and that wants saying plainly: **nothing stopped a proposer from emitting
`native_decide`; none happened to.** Containment upstream of publication is a property of the
producers, not of any gate. Two caveats cut the same way — this audit is a **substring scan of
`proof_src`**, exactly the discipline this ADR condemns in `_kernel_ok`, so it would miss a macro or
alias route; and it measures one instance's DB.

A **latent** fail-open, then — the ADR 0089 shape, found by review rather than by damage. Recorded
and fixed on that basis, not because the ledger is dirty.

## Decision 1 — mint `kernel_verified` from an axiom-checked run

`LeanVerifier.discharge` becomes the sole *checker* as well as the sole *writer*:

```
ok  ⟺  elaborates with no error  ∧  no message mentions `sorry`
   ∧   `#print axioms` REPORTED on this declaration    (ADR 0089 — no vacuous pass)
   ∧   its footprint ⊆ {propext, Classical.choice, Quot.sound}
```

On the **same assembled source** `axiom_closure`'s `ok` is at least as strong as `check_proof`'s on
the first two conjuncts, so this is a replacement, not an addition, and on a backend that can run it
it is round-trip neutral — one `backend._run` (`lean_axioms.py:53`), the same single elaboration
`check_proof` costs today. Two obligations stand between that sentence and a landable change.

**Build obligation 1 — one source assembly.** `check_proof` goes through `_join_proof`
(`lean_repl.py:40-49`, mirrored in `lean_cli.py`), which truncates `theorem_src` at the **first
`:=`**; `axiom_closure` (`lean_axioms.py:50-51`) concatenates it verbatim. Either `axiom_closure`
calls `_join_proof`, or `discharge` pre-truncates and the duplicate concatenation is deleted. See
Consequences for the 24/63 regression if this is skipped.

**Build obligation 2 — the check must enter through the backend contract.** `axiom_closure` calls
`backend._run`, which is **not** in the `LeanBackend` Protocol (`verifiers.py:44-47` declares only
`compile_statement`, `check_proof`, `closed_by_decision_procedure`). `LeanReplBackend` has `_run`;
**`LeanCliBackend` does not** — it has `_run_lean`/`_run_oneshot`/`_run_persistent`. Since
`assembly.py:443` builds `LeanVerifier(LeanCliBackend(...))`, Decision 1 as stated would raise
`AttributeError` on the CLI path rather than tighten it. The honest shape is a new `LeanBackend`
method returning the footprint alongside the verdict, implemented by both backends and every CI-safe
fake, with `axiom_closure` refactored to consume a response rather than reach for a private runner.
That is wider than "swap one call", and pretending otherwise is how the original gap was reasoned past.

The allowlist is what makes the check robust, and the module's own prose gets it wrong.
`lean_axioms.py:94` is `extra = [a for a in axioms if a not in allowed]` — name-agnostic. The
docstring and the comment above `STD_AXIOMS` name `Lean.ofReduceBool`, but **neither pinned toolchain
emits that name**; both emit a generated `<thm>._native.native_decide.ax_*`. A blocklist written to
match the documentation would not have caught the reproducer above. Fix the prose at
`lean_axioms.py:6-9` and `:15-16` — it is what a future maintainer would write a blocklist against.

## Decision 2 — the writer guard must bind the predicate, and be mutation-checked

Extend `tests/test_kernel_verified_writers.py` so whitelisting a write site is not enough: assert
that `discharge`'s verdict actually consults the axiom check. A guard that cannot fail when the thing
it guards is removed is not a guard (the ADR 0094 standard) — deleting the axiom conjunct must turn
it red. The same guard pins the **ordering**: drive one `(theorem_src, proof_src)` pair through both
paths and assert the axiom-checked verdict never passes where `check_proof` fails, with
`theorem tdef (n : Nat := 3) : n + 0 = n` as the regression fixture.

The general lesson outlives this defect: **a sole-writer guard binds provenance, not soundness.**
Every future "only X may write Y" invariant needs a companion "and Y is computed from Z".

## Decision 3 — a live negative control, in a lane that runs

A Docker-gated test that discharges `by native_decide` on a **true** statement and asserts
`kernel_verified is False` — true, so it fails for the right reason (the footprint) rather than
because the proposition is false. It goes in `scripts/run_kernel_tests.sh`'s file list, which treats
a skip as a failure; that lane's availability probe must be extended to the REPL image. The placement
is the point, and it is the lesson ADR 0095 learned one layer out: a negative control that skips
silently is decoration.

## Consequences

**Touches the proof edge.** This changes what `kernel_verified` means — the single value the whole
trust hierarchy rests on. The property that makes such a change landable is REFUSE-ONLY: the new
predicate may reject what the old accepted and must never accept what the old rejected, so it cannot
manufacture a law (`gates/verification.py:99-101`). **That property is not free here.** Because the
two predicates assemble different sources they are incomparable in *both* directions:

```
theorem tdef (n : Nat := 3) : n + 0 = n     by simp        # default-arg binder
  check_proof   'theorem tdef (n : Nat := by simp'          -> syntax error, REJECTS
  axiom_closure 'theorem tdef (n : Nat := 3) : n+0=n := by simp'          -> ACCEPTS
theorem foo : 1 + 1 = 2 := by sorry         by norm_num    # ':='-tailed theorem_src
  check_proof   'theorem foo : 1 + 1 = 2 := by norm_num'    -> ACCEPTS
  axiom_closure 'theorem foo : … := by sorry := by norm_num' -> error + sorry, REJECTS
```

The first falsifies "can never accept what the old rejected"; the second is the likelier in practice
— `_join_proof` exists *because* autoformalizers emit `:=`-tailed `theorem_src`. So the ordering is a
property of the assembly, not of `axiom_closure`, and this change must establish it, not assert it.

**The reject-direction cost is already measured.** Applying Decision 1 without build obligation 1
regresses **24 of the 63** promulgated rows — exactly the 24 carrying a `:=` tail, e.g.
`theorem n_sq_add_n_add_two_div_two (n : ℕ) : (n^2 + n + 2) % 2 = 0 := by sorry`. 39/63 pass, and the
failure is statically predictable from the DB without running Lean. So "re-discharge the 63 and
confirm 63/63" is not an open to-do with an expected pass — **it is a known failure until the
assembly is unified**.

**The ADR 0029 panel's pre-check must move with the mint.** Only the repair panel splits the check in
two: `proof_repair.py:110` gates on `check_proof_with_error` and discharges what that accepts. Its
`"kernel rejected a proof the pre-check accepted"` branch is dead code today precisely because the
two predicates are identical. Tightening only the mint makes it live, and the panel would start
discarding proofs it had already accepted.

**What this does not do:**

- It does not defend against an unsoundness *inside* the kernel. A `False` from corrupting the
  kernel's own refcounting (lean4 #14838, ADR 0095) has a clean footprint; no axiom-level guard can
  see it. Taking a fixed kernel is the whole defence there.
- It does not re-check the replay path. `runtime._row_to_prop` re-hydrates a stored verdict with no
  re-verification, by design. The ledger audit is evidence that no historical row needs it — a
  measurement of one DB, not a guarantee about another instance's.
- The ledger cannot supply the verification measurement alone: `memory` has `theorem_src` and
  `proof_src` but **no `imports` and no `preamble`**, so a re-discharge harness must reconstruct both.
  A run assuming `Mathlib.Tactic` measures the assembly bug (import-independent) but not the
  report-resolution risk.
- It does not add a `native_decide` prohibition to the proof prompts, and should not be mistaken for
  one. An instruction to a proposer is not a mechanical check — that is the project's whole thesis.
- It does not audit what else reads `kernel_verified` downstream of the Codex; `Q.E.D.` propagates
  into `.leibniz/review_queue.md` and `newton_exchange.py` folios, neither surveyed here.

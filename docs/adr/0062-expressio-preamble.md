# ADR 0062 — `Expressio.preamble`: legible multi-definition amplification laws

**Status:** **BUILT.** An **additive**, default-empty definitional preamble on `Expressio`, prepended to
the kernel source before `theorem_src := proof`, so a multi-definition amplification law keeps a
**legible** `theorem_src` instead of an inlined blob. The **trust boundary is untouched**:
`kernel_verified` is still set only in `LeanVerifier.discharge`; `trust.py` / `verifiers.py` /
`tests/test_invariants.py` are byte-identical; with the default empty preamble the discovery path is
byte-for-byte unchanged.

## Context — the single-declaration discharge vs a 12-definition theorem

The discharge assembles ONE Lean declaration via `_join_proof(theorem_src, proof_src)`, which cuts
`theorem_src` at its **first `:=`** and appends the proof. This is deliberate (ADR 0027): the kernel
sees exactly one self-contained declaration, so an LLM proposer has no separate-declaration surface to
poison. It works because discovery-fragment theorems are self-contained (`∀ …, … := by …`, any helpers
coming from `imports`).

ADR 0050 Phase 2 (the first amplified law, #361) hit the wall: the Kochen–Specker uncolorability theorem
needs **12 helper definitions** — Eisenstein-integer arithmetic, a fuel-bounded backtracking `solve`,
the 33 rays / 14 bases — none in Mathlib. To route it through the existing `_join_proof` it was inlined
into a **2610-char `:=`-free nested-λ + `@Nat.rec`** single declaration. That is correct and sound but
essentially **unreadable** — which defeats the purpose of a *reading-room* law.

Extending the discharge to *construct a theorem from typed data* (object-hash binding, AST/`Environment`
diff guard, …) was **deferred** in ADR 0045 §10 ("discharge HELD"). This ADR is a **narrower, additive**
change and is explicitly **not** that construction branch (see Non-goals).

## Decision — an operator-authored top-level preamble, re-checked in full

Add `Expressio.preamble: str = ""`: gate/operator-authored top-level declarations (`def`s,
`set_option`s) prepended to the assembled source, ahead of `theorem_src := proof`. Threaded through
every place the kernel source is built:

- `_join_proof(theorem_src, proof_src, preamble="")` — both backends (`lean_repl`, `lean_cli`);
  `f"{preamble}\n{body}"` when non-empty, else the previous `body` verbatim.
- All source-builders pass `expr.preamble`: `check_proof`, `compile_statement`, `check_proof_with_error`,
  `closed_by_decision_procedure` (and `compile_with_error`).
- `axiom_closure(…, preamble="")` (both the library and the honesty-gate copy) elaborates the WHOLE
  source — preamble included — before `#print axioms`.
- `law_payload` stores `preamble`; the honesty gate (`export_calculemus.py --check`) reads it back and
  re-verifies the SAME full source the kernel saw.

The KS law is refactored onto this: `theorem_src` is now the one-liner
`theorem cabello_uncolorable : solve rays bases [] [] 30 = false`, with the legible definitions (identical
to `docs/crt/cabello_ks.lean`) in the preamble. Re-discharged: `kernel_verified`, `Q.E.D.`,
`axioms=[propext]`; honesty gate `VERIFIED`.

## Why this is sound

- **Additive / discovery byte-identical.** `preamble` defaults to `""`; every discovery-path `Expressio`
  leaves it empty, so `_join_proof` returns exactly the old single declaration. The ADR 0027
  anti-poisoning shape is preserved for every proposer-emitted theorem. (Guarded by a test:
  `_join_proof(t, p) == _join_proof(t, p, "")`, and a real-kernel `lean_decided` e2e still passes.)
- **Never proposer-populated.** The preamble is written ONLY by operator-authored amplification scripts
  (`export_*_law.py`). No proposer/formalizer path sets it; the LLM still gets no separate-declaration
  surface. Populating it from proposer output would be a review-caught defect, not a silent hole.
- **Re-checked in full.** `axiom_closure` elaborates `preamble ⊕ theorem_src ⊕ proof` and rejects any
  `sorryAx` / `native_decide` / axiom outside the allowed set — so a hole or smuggled axiom **in the
  preamble** fails the honesty gate exactly as one in the proof would.
- **Trust core untouched.** `kernel_verified` is still written only by `discharge`; `Q.E.D.` only via
  `seal` on `kernel_verified`; `TrustPolicy` / `VerificationGate` / `tests/test_invariants.py` unchanged.
- **Faithfulness posture unchanged.** For an `amplified` law the operator+review vouch that the preamble
  definitions faithfully encode the cited published result — the same discipline ADR 0050 already
  requires (references + review); the preamble does not add a new soundness obligation, only relocates
  the (kernel-checked) definitions out of the statement.

## Non-goals

- **Not the ADR 0045 §10 construction branch.** No generate-a-theorem-from-typed-data, no object-hash
  tri-edge binding, no `Environment`-diff guard. The preamble is inert Lean text prepended to a
  hand-authored theorem; the kernel checks the whole thing as usual.
- **Not for the discovery pipeline.** Proposers keep emitting single self-contained theorems; the
  preamble is an amplification/operator affordance only.
- **Not a legibility guarantee for arbitrary results.** It removes the *inlining* tax; a law whose
  definitions are themselves illegible is still illegible.

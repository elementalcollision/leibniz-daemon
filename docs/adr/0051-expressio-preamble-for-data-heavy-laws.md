# ADR 0051 — A kernel-checked `Expressio` preamble, so data-heavy certs can become laws

**Status:** **REJECTED (2026-07-06)** by an adversarial soundness review — do **not** implement.
The review reaffirms ADR 0027's decision to forbid a separate-declaration surface. Recorded here so
this path is not re-attempted without a fundamental redesign. Complements ADR 0001 (charter), ADR
0002 (faithfulness gate), ADR 0027 (the "no separate-declaration surface" property this ADR tried
to reopen), ADR 0050 (law provenance).

## Review outcome — REJECTED (needs fundamental redesign, high confidence)

A four-lens adversarial review (axiom smuggling / vacuity / allow-list bypass / gate plumbing) found
**five independent critical/high holes**, two of which attack the design core and re-open exactly the
ground ADR 0027 settled:

1. **`discharge` never runs axiom-closure.** `LeanVerifier.discharge` sets `kernel_verified` purely
   from `check_proof`/`_kernel_ok`, which checks only `error` severity and a literal `"sorry"`
   substring — never `#print axioms`. `native_decide` (`Lean.ofReduceBool`) and transitively-reached
   smuggled axioms yield `kernel_verified=true`, `Q.E.D.`, and `promulgate()` admits them **before**
   the export-time H0 gate ever runs. The guard the ADR calls load-bearing is absent from the sole
   writer of `kernel_verified`.
2. **`axiom_closure` fails OPEN.** `axioms` defaults to `[]` and any parse miss (the
   `does not depend on any axioms` form, a reformatted/multiplexed message, a wrong name) returns
   `ok=True` on a term whose axioms were never read. A soundness gate must fail **closed**.
3. **`axiom_closure` checks only the first theorem name** (`_NAME_RE.search`), so the mandatory
   negative control — the whole anti-vacuity argument — is never axiom-checked.
4. **Attribute/instance poisoning (the ADR 0027 class, reopened).** The `def`/`abbrev` allow-list
   does not reject attributes: `@[instance] def badDecEq : DecidableEq Foo := ⟨fun _ _ => isTrue …⟩`
   installs a bogus `Decidable` instance (zero axioms → clean `#print axioms`), so `theorem … := by
   decide` **and** the negative control both resolve `decide` against the poisoned instance and
   elaborate regardless of the honest predicate. A keyword denylist cannot cover Lean's open
   metaprogramming surface — precisely what ADR 0027 concluded.
5. **The single-input negative control is non-discriminating.** A predicate `if a == a1bad then false
   else true` satisfies both the `=true` law and the `=false` control while asserting nothing — so
   the ADR's central anti-vacuity claim is false. A control must be **gate-generated and
   multi-corruption**, never promoter-chosen by name.

**Conclusion:** the sound path forward is **not** a preamble surface. Either (a) fill `laws[]` via
**origination of compact, self-contained theorems** (ADR 0050 path A — no reopened surface), or (b)
if data-heavy amplifications must become laws, a *much* larger redesign is required first
(axiom-closure hardened fail-closed **into `discharge`** over **every** declaration; a
Lean-frontend-parsed allow-list that inspects the elaborated environment delta and forbids all
attributes/instances/shadowing; a gate-generated multi-corruption faithfulness control; the preamble
threaded through identity/serialization/persistence) — and that redesign must clear its own review.
Absent that, this ADR stays rejected.

---

*Original proposal (rejected — retained for the record):*

## Context

The `laws[]` ledger is empty of real content (3 toy specimens + 1 held-back) after 35 cycles, and
the reason is structural, not neglect:

- A promulgated law is a single `Propositio` triad whose `Expressio.theorem_src` is **one
  self-contained declaration**. `leibniz/backends/lean_repl.py::_join_proof` truncates
  `theorem_src` at the **first `:=`** and appends `:= <proof_src>`, so `theorem_src` cannot carry
  any `def … :=`. Every promulgated/corpus law today is a one-liner over **standard Mathlib
  predicates** (`add_comm_nat`, `comparison_sort_lower_bound`, …).
- Every genuine cycle result is a **multi-declaration** `.lean` certificate: data (`def a1 : List
  Int := …`) plus helper functions (`def autocorr`, `def eq1`) plus several `decide` theorems and a
  negative control. Complex Hadamard order 94 and kissing k(19) ≥ 11948 are of this shape.

So the data-heavy results are shipped as **cycles** (downloadable certs) and can never reach
`laws[]` without either impractical full inlining of every function and datum into one term, or the
extension proposed here. (Exact-procedure results with **no** Lean proof — e.g. the EFX census —
remain non-promulgatable regardless; `promulgate` requires a real kernel `Q.E.D.`, and that is
correct.)

## Decision (proposed, pending review)

Add an optional **kernel-checked preamble** to `Expressio`: a block of auxiliary Lean
**definitions** (`def`/`abbrev` only — the data and the total helper functions the theorem
references) that `check_proof`/`compile_statement` prepend to the theorem before submitting to the
kernel. The kernel then sees, as one submission:

```
<imports>
<preamble : def a1 := … ; def eq1 := … ; …>
<theorem_src> := <proof_src>
```

The preamble is the **same** declarations the cycle's certificate and its Python cross-check
already validated; promotion carries them across, it does not invent them.

## Why this does not weaken soundness

The kernel still *decides*; nothing here lets an LLM's word stand in for a proof. Three guards, in
order of strength:

1. **Axiom-closure is the load-bearing guard (extended to cover the preamble).** The H0 gate
   (`scripts/export_calculemus.py::axiom_closure`) already re-derives, for every published law, the
   exact axiom set the theorem depends on and rejects anything beyond Lean's canonical trusted
   axioms (`propext`, `Classical.choice`, `Quot.sound`). A preamble that smuggles `axiom evil : P`,
   `native_decide` (→ `Lean.ofReduceBool`), or an admitted lemma makes the **theorem depend on that
   axiom**, so H0 rejects the law. This ADR requires H0 to run on the **combined** source
   (preamble + theorem + proof), and — a hardening beyond today — that `LeanVerifier.discharge`
   itself enforce axiom-closure, so a preamble-smuggled axiom fails at **discharge** (never
   `kernel_verified`), not only at export.
2. **`sorry` is caught at discharge.** `_kernel_ok` already fails on any `sorry` diagnostic, so a
   preamble `def` that is `sorry`-filled never verifies.
3. **A closed syntactic allow-list for the preamble.** Only `def`/`abbrev` declarations; **reject**
   `axiom`, `sorry`, `native_decide`, `opaque`, `unsafe`, `partial`, `macro`/`elab`/`syntax`,
   `@[implemented_by]`/`@[extern]`, `import`, and any `set_option … in`. Belt-and-suspenders behind
   H0, and it keeps the surface to pure total definitions the kernel elaborates.

The distinction from ADR 0027's removed surface is exact: **`proof_hints` were LLM-drafted,
UNCHECKED lemma *statements*** that would have been unsound if trusted — so they are kept
prover-context-only and never reach kernel I/O. A preamble is **definitions the kernel
elaborates**; a `def` cannot *assert* a falsehood, and any axiom it tries to lean on is caught by
(1). The preamble is part of the certificate the kernel checks, not a claim taken on faith.

## The real risk this shifts: faithfulness, not soundness

A custom preamble can make a theorem **vacuously true** without any unsound step — e.g. a preamble
defining `eq1 := fun _ _ _ _ => true` makes `eq1 a b c d = true` hold trivially, and the kernel
would (correctly) verify it. The kernel is not fooled about *truth*; the **claim** is fooled about
*meaning*. This is a faithfulness failure (ADR 0002), and it must be guarded as strongly as the
one-liner model guards its trusted Mathlib predicates:

- **Mandatory discriminating negative control.** A promulgated data-heavy law MUST carry, in its
  certificate, a negative control — the same predicate applied to a corrupted witness, proven to
  return `false` (e.g. `had94_control : eq1 a1bad b1 c1 d1 = false`). The honesty gate verifies the
  control theorem holds. A vacuous predicate (`eq1 := fun _ => true`) **cannot** satisfy a
  `= false` control, so this mechanically rejects the trivial-definition attack.
- **Non-triviality.** `LeanVerifier.is_trivial` (the aesop/`decide`-closes-on-its-own test) flags a
  statement an automated tactic closes with no content.
- **Faithfulness gate reads the preamble.** The ADR 0002 faithfulness contract
  (`claim_domain`/`claim_property`) and the OPEN_FORM fallback must be evaluated against the
  preamble's definitions, not just `theorem_src`, since the predicate now lives there.
- **Provenance link.** The preamble must be byte-identical to the definitions in the cycle's
  published certificate (whose Python cross-check independently reproduced the same computation),
  recorded via ADR 0050 `references`/`tier`. The law inherits the cycle's faithfulness evidence.

## Scope / guardrails

- `TrustPolicy.validate_path`, `VerificationGate.is_promotable`, and the "`kernel_verified` set only
  in `discharge`" invariant are **unchanged**. `tests/test_invariants.py` must stay byte-identical.
- The preamble is admitted **only** through the discharge path with (1)–(3) enforced; there is no
  way to attach a preamble that bypasses axiom-closure.
- This ADR is **inert until the adversarial soundness review clears** and its findings are folded
  in. If the review finds an unguarded vacuity or axiom-smuggling path, the ADR is amended or
  rejected — it is not implemented on optimism.

## Consequences

- Data-heavy amplifications (Hadamard 94, kissing k(19)) and future originated results whose proof
  needs helper definitions become promulgatable as `laws[]`, honestly tagged (ADR 0050) with tier +
  `amplified`/`originated` + the source cite.
- The kernel-source surface widens from one declaration to (kernel-checked defs + one theorem);
  the soundness burden moves onto axiom-closure (hardened into discharge) and the anti-vacuity /
  faithfulness apparatus — which is why this ships only after an adversarial review.

## Alternatives considered

- **Full inlining** (no preamble; inline every function and datum into one term): impractical and
  unreadable for autocorrelation over 47-element lists or 1280-word censuses; rejected.
- **Keep the model strict; laws fill only via origination of compact facts** (ADR 0050 path A):
  sound and zero-change, but permanently excludes the data-heavy records/existence results from
  `laws[]`. Pursued in parallel (origination), not instead — the operator chose *both*.

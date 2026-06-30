<!--
Synthesis of the 8-model external-witness round on the construction PROOF-edge (discharge trusted-surface
expansion). Raw responses: external-witness-round-construction-proof-edge.md. Advisory (invariant 4: no
LLM decides). Decision-determining for whether/how to edit the sole kernel_verified writer.
-->

# Witness round synthesis — the construction PROOF-edge (8 reviewers)

**8 reviewers:** Fugu, Fugu Ultra, Deepseek v4 Pro, Kimi, GLM 5.2, Gemini 3.5 Thinking, Qwen 3.7 Max,
Nex N2-Pro. **The convergence is overwhelming.** Raw:
[`external-witness-round-construction-proof-edge.md`](external-witness-round-construction-proof-edge.md).

## Headline (8/8)
1. **DEFER editing `LeanVerifier.discharge` now.** *Every* reviewer: do not edit the sole
   `kernel_verified` writer for **dormant** infrastructure — no record beat exists on reachable cells, so
   the edit is "maximum risk for zero current reward" (GLM), "a trust bridge to nowhere" (Qwen). Keep
   constructions **audit-tier** (already kernel-checked, not promulgated); greenlight only when a real
   record beat is in hand *and* the full guard suite + a human ADR are green.
2. **Even the *hardened* design is still wrong in shape.** My hardened sketch (allowlist *parse* of a
   candidate `theorem_src`) is "too source-text-centric." The panel's correction is categorical →

## Unanimous design consensus (7–8/8 each)
- **GENERATE, don't parse/guard candidate source.** The construction path must take **typed witness data
  + canonical params** and have the **trusted verifier generate the entire Lean source from a fixed
  template**. The witness controls **only data literals**. Candidate `theorem_src` is either not accepted
  at all, or accepted only to be **byte-compared against the trusted rendering**.
- **Tri-edge canonical-object-hash binding is MANDATORY** — and it's *the* central risk. The dangerous
  failure is **statement laundering**: a *true* theorem for an easy/different cell attached to a record
  claim for a hard cell (a ledger-integrity failure, not a kernel failure). Proof/faithfulness/novelty
  must all bind to one `object_hash = hash(domain, params, bound, witness)`; the theorem is *rendered
  from* it and the oracle *reads* it. (≥6 reviewers name this the #1 thing we're getting wrong.)
- **Explicit typed marker, not prefix detection.** Route on `expr.kind == CONSTRUCTION` (set by trusted
  ingestion, immutable); prefix-match is at most a secondary sanity assert. Confused-deputy / misroute
  in both directions otherwise.
- **AST-/Environment-level guard, not text.** Lean source is a *compiler* problem, not a string problem:
  text counting is bypassable by `theorem`/`:=`/`def` hidden in comments/strings, and by binder
  **shadowing** (`let validCovering := fun _ => true` inside the theorem *type* → `by decide` proves
  `True`), and by `abbrev`/`inductive`/`structure`/`instance`/`macro`/`notation`. Mandate: parse, then
  **diff `Environment.constants`** against the pristine prelude env — require **exactly one new
  `TheoremVal`**, zero new defs/axioms/instances, zero macro/typeclass changes.
- **Axiom-closure audit.** After check: the theorem's axiom footprint (`#print axioms`/`collectAxioms`)
  must be **empty** (reject `sorryAx`/`axiom`/`opaque`/non-whitelisted) — catches axiom injection
  regardless of entry.
- **Hermetic, fail-closed run.** Pinned image/toolchain hash, no candidate imports, fresh tmpdir, no
  network; timeout / nonzero exit / missing-or-mismatched-type theorem / uncomputable axiom closure =
  **failure**. "Absence of error text" is not success.

## The one split (with a shared bright line)
- **Inlined locked prelude vs in-image library module.** ~4 (Fugu, Fugu Ultra, Deepseek, Nex): inlined is
  acceptable *if* hash-pinned + axiom-audited + verifier-generated. ~3 (Kimi, GLM, Gemini): in-image
  module is mandatory; inlined is a **security regression**; "the absence of a Dockerfile is not a
  justification for weakening the kernel boundary" — build the image. Qwen adds inlining's **re-elaboration
  cost / DoS** vector.
- **Shared bright line (all):** the prelude must be **content-addressed (hash-pinned), operator-owned,
  axiom-audited, non-substitutable, and reviewed as TCB** — whichever packaging.

## New findings beyond my internal adversarial review
My internal pass caught **axiom-injection** (denylist bypass) and **missing tri-edge binding**. The panel
adds, importantly:
- **`let`/`have` shadowing inside the theorem type** (Deepseek, Fugu Ultra, Gemini) — defeats a guard
  that merely bans top-level defs. Fix: namespaced/`protected` prelude names used fully-qualified, or
  generate the statement.
- **Comment/string-literal hiding** of guard tokens (Kimi, Gemini, Qwen) → AST guard.
- **The prelude isn't safe just because it's locked** (Kimi, "trusted-because-operator-owned fallacy"):
  a wrong `Decidable` instance / `@[inline] abbrev` can make `decide` return true for an *invalid*
  witness with **no axiom**. Need: algorithmically-derived `Decidable`, no `opaque`/classical, and ideally
  a **kernel-checked bridge lemma** that `validCovering` ≡ the mathematical spec.
- **`validCovering = true` ≠ the record claim** (Fugu, Fugu Ultra, Kimi): prove the *actual* claim —
  `∃ blocks, blocks.length = B ∧ validCovering …` (or a bridge to `C(v,k,t) ≤ B`), not just witness
  validity.
- **The `by decide` scaling wall** (Qwen, Kimi) — echoes the Gate-B2 finding: pure `decide` OOMs/times-out
  on large witnesses; `native_decide` expands the TCB. The TCB-safe route for large finite objects is an
  **external fast-checker emitting a small certificate the kernel checks** — a certificate architecture,
  not `decide`.

## The constructive path (multiple reviewers)
Build it now as a **NON-PROMOTING audit verifier** — a `ConstructionVerifier.check` /
`construction_kernel_checked` field that exercises the *whole* path (typed objects → trusted-generated
source → hermetic Lean → Environment-diff + axiom audit → tri-edge object-hash) **without** setting
`kernel_verified`. Flip to a real PROOF edge only when a record beat exists, the guard/regression corpus
is green, and a human ADR approves the TCB expansion. (Fugu, Fugu Ultra, GLM, Gemini.)

## Disposition (recommended)
The panel + my internal review agree and reinforce: **HOLD the `discharge` edit (8/8 defer).** The
hardened-but-still-source-centric design is superseded by **generate-from-typed-data + object-hash
tri-edge binding + AST/Environment-diff + axiom audit + a semantically-bridged, hash-pinned prelude +
the actual-claim theorem + a certificate path for large cells.** That is a substantial, well-specified
build — appropriate as a **non-promoting `ConstructionVerifier`** now (if wanted), with the
`kernel_verified` flip reserved for an actual beat + ADR. This vindicates running the witnesses and the
internal review: we did not edit the sole `kernel_verified` writer on an unsound, premature design.

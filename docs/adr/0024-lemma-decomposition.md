# ADR 0024 — Lemma decomposition (a structured-proof prover in the ensemble, lever 2)

Status: **Accepted** (2026-06-22)
Extends: ADR 0006 (N+1 consensus proving). Pairs with ADR 0023 (weaken-and-retry).

## Context

After ADR 0022/0023 the binding blocker is the **prover**: conjectures reach the kernel
but the HF ensemble (DeepSeek-Prover-V2 class) cannot close them under N+1 consensus
(ADR 0022 run: 31/39 reached proof, 0 closed). Two complementary levers attack this:

- **Lever 1 (ADR 0023)** — *weaken* the claim until a variant is provable.
- **Lever 2 (this ADR)** — keep the claim, *decompose the proof*: establish the
  intermediate facts as lemmas, prove each, then compose. A structured multi-step proof
  routinely closes goals a one-shot tactic script misses.

## Decision

A `DecompositionProver` (`leibniz/providers/decomposition_prover.py`) wraps any base
prover. For a `PROOF_DRAFT` it prepends a **decomposition instruction** to the goal —
"prove by establishing `have <name> : <stmt> := by <proof>` steps (or `suffices`), then
close the goal using them" — and delegates to the base prover; other roles pass through
unchanged. It is a drop-in ensemble member.

`prover_ensemble` (assembly) adds `LEIBNIZ_DECOMPOSE` (default `1`) decomposition
variants of the first/strongest base provers, so each such model runs **both** one-shot
and structured strategies — two *ways for that model to find a proof*, not two
independent voters (see the consensus fix below).

The decomposition lives **inside the `by` block** as `have`/`suffices` lemmas, so the
whole structured proof is one artifact checked by the existing pipeline — no change to
`Expressio`, the Lean backend, or `discharge`.

## Why this is trust-safe

- **Pure proposal-side.** It only reshapes the proof prompt. `LeanVerifier.discharge`
  stays the **sole** `kernel_verified` writer (invariant 1), unchanged; `verifiers.py`,
  `trust.py`, the gates, and `tests/test_invariants.py` are untouched (byte-identical).
- **Every sub-lemma is kernel-checked.** A `have h : T := by …` inside the proof is
  elaborated and verified by the kernel as part of the whole — a decomposed proof is
  *exactly* as trustworthy as a flat one. There is no "trust the lemma" shortcut.
- **Consensus is only strengthened (and was hardened here).** Promulgation still needs
  `min_consensus` kernel-verified proofs. The adversarial review caught that
  `ProofConsensus` counted *passing attempts*, not *distinct provers* — so a model plus
  its own decomposition wrapper could have self-satisfied N+1 from effectively one model
  (a pre-existing gap this default would have made reachable). Fixed: consensus now
  counts **distinct prover identities** (`_prover_identity` unwraps strategy wrappers to
  the base model), so a model that proves the goal by two strategies is **one voter**.
  A decomposition variant therefore gives a model another *way* to find a proof but never
  a second *vote* — strictly more conservative, and it makes the "distinct/independent"
  promise true. (Never a soundness issue: every counted proof was always genuinely
  kernel-verified.)
- The output shape is unchanged (a `by` block), so it flows through `normalize_proof` +
  `discharge` identically to any other prover draft.

## Consequences

- The ensemble gains a strategy aimed squarely at the current bottleneck (hard goals
  one-shot proving misses), at a bounded extra cost (`LEIBNIZ_DECOMPOSE` attempts per
  theorem; default +1).
- **Deferred (future ADR, guarded-core):** *independent* sub-lemma proving — extract
  sub-lemma statements, prove each through the full gated pipeline, reuse proven ones as
  a verified preamble + as stepping stones. That needs the Lean backend / `Expressio` to
  carry a proven-lemma preamble (a `verifiers.py` change) and so requires operator
  sign-off; this ADR deliberately stays within the existing `discharge` contract.

## Validation

- Unit: `PROOF_DRAFT` is decomposed (instruction injected, goal preserved); other roles
  pass through verbatim; `available()` delegates; the structured output survives
  `normalize_proof`; `prover_ensemble` adds/omits variants per `LEIBNIZ_DECOMPOSE`;
  consensus counts a model's two strategies as **one** voter (`_prover_identity`) while
  two distinct models still reach consensus.
- Live (billable): a run with decomposition enabled, measuring whether any hard
  near-miss now closes at the kernel (a first promulgation).

# ADR 0058 — A deterministic modular-polynomial prover, promotable without LLM consensus (refines ADR 0006)

**Status:** **AMENDED — review returned `needs-amendment` (2026-07-07); the build-time obligations
A1–A4 below are binding before code.** The ≥3-lens adversarial review **validated the core principle**
(promote-on-one for a genuine decision procedure is sound — §"Review outcome") but found the ADR's
*implementation* of "decision procedure" unsafe: it keyed promotability on a **self-declared `model`
string** (`_prover_identity`, `consensus.py:63`), which lets a stochastic LLM named after the residue
prover masquerade and inherit promote-on-one. No path promulgates an *unproven* law (the kernel
re-verifies every draft — `discharge` is unchanged), so this is a defense-in-depth/policy defect, not a
kernel-soundness break — but it cannot ship as first drafted. The corrected design is A1–A5 below.

Adds the *prover-reach* half of the ceiling-raiser: a **deterministic decision-procedure prover** for
the modular-polynomial fragment, and a **refinement of the N+1 consensus policy (ADR 0006)** so that a
kernel-verified proof from such a procedure is promotable on its single verification — the same
principle by which a mechanical faithfulness gate (ADR 0056 `lean_decided`) or the novelty gate needs no
LLM judge/consensus. The **trust boundary is untouched**: the kernel still decides every proof
(`LeanVerifier.discharge`, the sole `kernel_verified` writer); `TrustPolicy.validate_path` and
`tests/test_invariants.py` stay byte-identical (the new counting policy is *additionally* pinned by A3).
Complements ADR 0006 (consensus), ADR 0013/0041 (producer allowlists), ADR 0056 (the faithfulness
backend this unblocks).

## Review outcome & corrected design (A1–A5) — supersede the identity/binding text below

The review **confirmed the crux**: promote-on-one is sound — N+1 was *never* a kernel-soundness
mechanism (every proof is checked by the *same* kernel, so consensus adds zero kernel assurance; the
kernel + faithfulness + `axiom_closure` are the sole soundness mechanisms, all unchanged). Its only
function was a weak hedge against *LLM-proposer stochasticity*, which a fixed, audited, non-sampled
algorithm has none of. "Judgment is quorum-gated; decision is kernel-gated" holds. But three lenses
independently found the masquerade defect, plus a binding gap. **Corrected design, binding before code:**

- **A1 — class-based identity in the trust core (unblocks the masquerade, B1).** `DECISION_PROCEDURE_PROVERS`
  membership is decided by **operator-imported class identity** — `isinstance(prover, ResiduePolyProver)`
  where `ResiduePolyProver` is imported *into `leibniz/trust.py`* (the PreToolUse-guarded core), never a
  `model`/name string and never a self-set flag. The check runs against the prover that **actually
  produced the kernel-verified draft** (`verified[i][0]` in `ProofConsensus.prove`), **not** the
  `_prover_identity` string and **not** the unwrapped `.base`. An `OpenRouterProvider(model="residue-poly-prover")`
  (a colliding string) is *not* an instance of the class, so it still needs `min_consensus`.
- **A2 — bind `theorem_src` to the faithfulness-vetted statement (unblocks B2).** `validate_path`
  checks edge *presence*, not that the faithfulness edge and proof edge concern the *same* statement.
  Promote-on-one is scoped to claims whose `theorem_src` is **gate-rendered from the vetted DSL
  contract**; the promotion path pins `theorem_src` against the canonical statement the faithfulness
  gate certified (reuse `lean_decided.canonical_statement` / the ADR 0056 binding), and the ℕ-vs-ℤ
  domain must be reconciled (the prover proves the *same* domain the gate vetted, not a Nat re-phrasing
  that only *looks* equivalent). Absent this, faithfulness vets statement A while the ledger publishes B.
- **A3 — pin the new counting policy in `test_invariants.py` (B3).** Green invariants today prove
  nothing about promote-on-one because the policy is invisible to them. Add regressions: an **LLM-only**
  path needs `min_consensus`; a kernel-**rejected** draft never promotes; the allowlist is consulted
  **only** against provers in `verified`; a colliding-`model` LLM still needs `min_consensus`.
- **A4 — pin the generator to kernel `decide`, with a promotion-time axiom check (B4).** The residue
  generator emits only kernel tactics (never `native_decide`); a promotion-time `axiom_closure` (or a
  binding of the publish-time check to promotion) rejects `sorryAx`/`Lean.ofReduceBool`. Fixes the
  promulgate-vs-publish conflation.
- **A5 — single-procedure promotion, explicitly justified (the residual).** The review's one honest
  residual: promote-on-one rests on a *single technique* (the ZMod bridge) over a *single kernel* with
  no independent recomputation. **Justification (accepted over requiring two procedures):** the ZMod
  substrate is **already trusted, load-bearingly, by `lean_decided` faithfulness** (a false faithfulness
  PASS mis-labels a law; the prover's output is *not* load-bearing — the kernel re-verifies the actual
  `theorem_src`, so a generator bug is a DEFER). Requiring a second technique for the *proof* while the
  *faithfulness* gate already promotes on the same substrate would be inconsistent and add no substrate
  independence the system doesn't already accept. **Cross-kernel replay** (the standing backlog) is the
  correct backstop for a substrate/kernel flaw and applies to *all* laws, not just these. A second
  independent decision procedure (e.g. a `polyrith`/Gröbner-cofactor prover) may later be *required to
  agree* as a hardening, but is not a precondition. The premise is restated per the review: consensus
  never added kernel-soundness.

The original identity/allowlist prose below (§Decision-2/3) is **superseded by A1** wherever they
conflict (it described string-identity keying).

### Increment-2 implementation note (2026-07-07): a DEMONSTRATE fast-path, not a pluggable prover

Increment 2 realises decision-procedure promotability as a **DEMONSTRATE fast-path**
(`leibniz/providers/residue_prover.py::ResidueDemonstrate`, opt-in via `LEIBNIZ_LEAN_DECIDED`) rather
than a pluggable prover in the consensus ensemble. For a modular claim it proves the gate-rendered
canonical ℤ-box law by the ZMod bridge and records the proof edge on the **single** kernel
verification; everything else falls through to the unchanged N+1 ensemble. This is **strictly more
conservative** than the reviewed ensemble-prover design and satisfies the same obligations more simply:

- **A1 is obviated, not merely fixed.** There is *no registrable prover object* to masquerade as — the
  decision procedure is one fixed, operator-activated code path reached only for claims `residue_law`
  accepts. No identity string or class to forge; `_prover_identity` is not involved.
- **A2** — the promoted `theorem_src` is re-rendered *in the fast-path* from the faithfulness-vetted DSL
  contract, so the proven statement is the certified one.
- **A4** — a promotion-time `axiom_closure` rejects `sorryAx`/`Lean.ofReduceBool`; the proofs use only
  kernel `decide`.
- **Trust boundary byte-identical** — `consensus.py`, `trust.py`, `TrustPolicy.validate_path`, and
  `tests/test_invariants.py` are **unchanged**. The promoted edge is `discharge`'s own
  `MECHANICAL/PASS/KERNEL_PRODUCER` edge; promulgation is still gated by `validate_path`. The fast-path
  merely does not *add* the N+1 requirement (a consensus-layer policy, never a trust-core one) to a
  deterministic, kernel-verified proof — exactly the ADR's decision.

Kernel-validated end-to-end (the live claim `((a·b)²+a·b) % 6 ∈ {0,2}` is proved and promoted; a false
claim's generated proof is kernel-rejected → fall-through). **Fail-closed** until the operator sets the
flag; **activation is gated on a code-level review** (as ADR 0056 increment 2 was).

## Context — the binding constraint moved to the prover

Activating the Lean-decided faithfulness backend (ADR 0056) let the daemon's richer two-variable
modular-polynomial claims **pass faithfulness and reach DERIVE** for the first time. A live cycle
confirmed it: `reached_proof = 1` (up from the old 0 — the ceiling lifted), but `promulgated = 0` —
the claim `((a·b)² + a·b) mod 6 ∈ {0, 2}` (a genuine law: `ab(ab+1)` is a product of consecutive
integers) reached the prover and the **LLM ensemble could not prove it**. The binding constraint is no
longer faithfulness certification; it is **prover reach** on exactly the fragment we just unblocked.

The resolution is already in hand: **the same ZMod-bridge math that certifies faithfulness proves the
theorem.** Validated against the real Lean 4.31 kernel (`scratchpad/proto_prover2.py`) for ℕ and ℤ, all
three shapes — including the exact live theorem:

```lean
theorem live (a b : Nat) : ((a*b)^2 + a*b) % 6 = 0 ∨ ((a*b)^2 + a*b) % 6 = 2 := by
  have key : ∀ (x y : ZMod 6), (x*y)^2 + x*y = 0 ∨ (x*y)^2 + x*y = 2 := by decide
  have hc  : (((a*b)^2 + a*b : ℕ) : ZMod 6) = ((a:ZMod 6)*(b:ZMod 6))^2 + (a:ZMod 6)*(b:ZMod 6) := by
    push_cast; ring
  rcases key (a:ZMod 6) (b:ZMod 6) with h | h
  · left;  have hme : (((a*b)^2 + a*b : ℕ):ZMod 6) = ((0:ℕ):ZMod 6) := by rw [hc, h]; norm_num
           rw [ZMod.natCast_eq_natCast_iff] at hme; simpa [Nat.ModEq] using hme
  · right; have hme : (((a*b)^2 + a*b : ℕ):ZMod 6) = ((2:ℕ):ZMod 6) := by rw [hc, h]; norm_num
           rw [ZMod.natCast_eq_natCast_iff] at hme; simpa [Nat.ModEq] using hme
```

This proof is **generated by a fixed algorithm** from the claim's structured contract (the modulus, the
polynomial, the residue set), not sampled by an LLM. The `decide` is a **kernel** reduction over the
finite `ZMod m` (no `native_decide`), so the axiom footprint stays clean.

## Decision (proposed, pending review)

### 1. A `ResiduePolyProver` — a decision procedure in the prover cascade

A prover that, for a claim in the **modular-polynomial fragment** (reusing
`lean_decided.classify_property` — `poly % m ⋈ c`, eq/neq/residue-set, over ℕ or ℤ), **deterministically
emits the ZMod-bridge proof** and proposes it through the normal path
(`propose(Role.PROOF_DRAFT, …)` → `ProofConsensus._attempt` → `LeanVerifier.discharge`). It is a
**PROPOSER, not a decider of trust**: the kernel re-verifies its every draft, so a bug in the generator
makes the kernel **reject** the malformed proof → that draft simply does not count → fall through to the
LLM ensemble. **A generator bug costs yield, never soundness.** (This is the crucial difference from
`lean_decided`, whose PASS is load-bearing; a prover's output is not — the kernel gates it.)

Fragment-guarded and total-or-abstain: on anything outside the classified fragment it returns no draft.
The proof is robust to polynomial rephrasing in `theorem_src` because the bridge's `push_cast; ring`
step normalises, and `rcases` on the `decide`-closed key supplies the residues.

### 2. Consensus refinement — decision-procedure proofs are promotable on one kernel verification (amends ADR 0006)

**What N+1 consensus actually guards.** ADR 0006 requires `min_consensus` distinct kernel-verified
proofs from *independent provers*. Since every proof is checked by the *same* kernel, N+1 adds no
kernel-soundness; it is a hedge against **LLM-proposer stochasticity** — the chance that one stochastic
sample produces a kernel-accepted proof that rests on some pathology a different model would not
reproduce. Independence across *models* reduces that correlated-failure risk.

**A decision procedure is not a stochastic sample.** The `ResiduePolyProver` runs a fixed, audited,
adversarially-reviewed algorithm; identical input yields the identical proof term; there is no sampling
and no model. Requiring N independent *LLMs* to also prove the theorem adds nothing it was designed to
add — and, empirically, they cannot. So:

> **N+1 consensus applies to LLM proposers. A kernel-verified proof from an operator-allowlisted
> DECISION-PROCEDURE prover satisfies promulgation on its single verification.**

This is the exact principle already in force elsewhere in the trust model: the faithfulness gate's
mechanical PASS needs no judge (ADR 0002/0056); novelty is settled by a decision procedure, never a
vote (ADR 0001). Proof gains the same distinction: **judgment (LLM) is quorum-gated; decision (exact
procedure) is kernel-gated.**

### 3. The trust boundary is untouched; only the counting policy changes

- The emitted `PROOF_EDGE` is **still `MECHANICAL` + `Verdict.PASS` + `producer = KERNEL_PRODUCER`**
  (straight from `discharge`). `TrustPolicy.validate_path` (which requires exactly that, and never
  inspects a consensus count) and `tests/test_invariants.py` are **byte-identical and green**.
- The **only** change is inside `ProofConsensus.prove`: a kernel-verified draft from a prover whose
  identity is in the operator-owned allowlist `DECISION_PROCEDURE_PROVERS` makes the edge PASS on its
  own; LLM-only drafts still require `min_consensus`.
- **`DECISION_PROCEDURE_PROVERS`** is a new allowlist in the trust core (`leibniz/trust.py`,
  PreToolUse-guarded), mirroring `FAITHFULNESS_PRODUCERS` (ADR 0041): **operator-added, never
  autonomous.** A prover's decision-procedure status is *not self-declared* — an LLM prover cannot
  masquerade, because promotability keys on membership in this operator-pinned set, not on a flag the
  prover sets.

## Why this does not weaken the trust boundary (do not relitigate)

- **The kernel decides every proof, unchanged.** `discharge` remains the sole `kernel_verified` writer;
  the residue prover only *proposes*.
- **Faithfulness is separate and upstream.** A decision-procedure proof of a *mis-stated* theorem is
  impossible to promote: the faithfulness gate (now including `lean_decided`) must already have
  certified `theorem_src` faithful before DERIVE runs. The residue prover proves the theorem the
  faithfulness gate vetted.
- **Clean axiom footprint.** The proof uses kernel `decide`/`rcases`/`simpa` — never `native_decide`;
  the publish-time `axiom_closure` gate (ADR H0) rejects `sorryAx` / `Lean.ofReduceBool` regardless.

## Red-team targets for the adversarial review

- **Masquerade.** Can a non-allowlisted prover (an LLM) get a proof counted as decision-procedure — via
  identity collision, a wrapper, or `_prover_identity` unwrapping? The allowlist must key on a
  forgery-resistant identity in the trust core, and the promotion path must consult *only* it.
- **Is N+1 really unnecessary here?** Stress the core claim. If a decision-procedure proof is
  kernel-verified, does anything the N+1-for-LLMs hedge guards still apply to it (a Mathlib
  inconsistency the `decide` exploits; a `Decidable` instance pathology; determinism that is actually
  input-dependent nondeterminism)? Argue the residue prover's failure modes are all kernel-caught or
  regression-caught.
- **Fragment / mis-encoding.** Can the generator emit a proof that closes a *different* goal than
  `theorem_src` (so it "proves" the wrong theorem)? The kernel checks the proof against the *actual*
  `theorem_src`, so a mismatched proof fails to elaborate → DEFER; confirm there is no path where a
  generated proof elaborates against a theorem_src weaker than the published claim.
- **Promotability composition.** Does promote-on-one interact badly with the other required edges
  (faithfulness, novelty) or the `is_promotable` path? Confirm all three edges are still independently
  required.
- **Determinism & reproducibility.** Confirm the generator is genuinely deterministic (no RNG, no
  time), so "decision procedure" is an honest label; a promulgated law's proof must be reproducible.
- **The consensus refinement as new surface.** The change to `ProofConsensus.prove` is trust-adjacent
  even though the edge stays kernel-produced; pin it with a regression that an LLM-only path still needs
  `min_consensus` and only an allowlisted decision-procedure draft promotes on one.

## Consequences

- The modular-polynomial laws the daemon already conjectures and now certifies faithful become
  **promulgable** — the ceiling-raiser delivers end-to-end (conjecture → faithful → proven → law).
- The binding constraint moves once more — from prover reach back to **what the conjecturer proposes**
  (novelty / ambition), the pre-ADR-0053 frontier. That is the healthy place for it to sit.
- A clean, reusable distinction enters the trust model — **judgment is quorum-gated; decision is
  kernel-gated** — that future exact provers (a Gröbner/`polyrith`-cofactor prover, an ECPP replay)
  can inherit by joining `DECISION_PROCEDURE_PROVERS` after their own review.
- Not implemented until this clears its ≥3-lens adversarial review. If the review finds a masquerade
  path, a case where N+1 genuinely still matters, or a proof-of-wrong-statement path, the ADR is
  amended or the consensus refinement is dropped in favour of the more conservative hint-only route.

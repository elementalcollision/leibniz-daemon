# T9 — Tier-2 "attested" counterexample family: scoping

*Scoped 2026-07-04 (in parallel with the Tier-1 domain build). The Tier-1 domain
(`scripts/counterexample_domain.py`) is Tier-1-only for now, per operator direction; this doc scopes Tier 2 so
it can be folded in later. Input: a 4-agent per-problem attestation-spec pass over the pipeline-math
formalizations we already audited FAITHFUL + `lake build`-re-verified this session.*

## The boundary — why these are *attested*, not *self-certified*

Tier 1 (shipped) certifies counterexamples whose witnessing property is a **bounded, decidable** check: a
monomial `∉ I²`, a divisibility that fails on a finite prefix, an absorbing number over `ℤ/m`. `certify(object)`
emits a `decide`-closed Lean cert; the download is a single self-contained `.lean`.

Tier 2 (the pipeline-math Problems 4b / 20 / 27b / 30c) is different **in kind**: the witness lives over an
**infinite ring**, and the failing property is universally quantified over all finitely-generated ideals /
arbitrary tuples — there is no finite model to enumerate, so it can *never* be a `decide`. The unanimous finding:

| Problem | Witness object (infinite) | Headline theorem |
|---|---|---|
| **4b** | `R = Δ(B) + C^(ℕ)` — a subring of `ℕ → C` (countable power) | `problem4b_false : ∃ S, FiniteConductor S ∧ ¬ QuasiCoherent S` |
| **20** | `D = 𝔽₂ + 𝔪`, a conductor pullback in `𝔽₂(t)` | `problem20_answer : ∃ D K …, ¬ Injective (θ₂) ∧ ¬ (Int(D²) ⊆ range θ₂)` |
| **27b** | `D = 𝔽₂[π]`, `B = K ⊗_D A` — polynomial rings | `problem27b_false : ∃ g₁ g₂ ∈ IntA, g₁·g₂ ∉ IntA` |
| **30c** | `A_q = 𝔽₂[t][X₀,X₁,X₂]/Arel` — a quotient poly ring | `problem30c_false : ∃ R I, absorbingNumber(I.map C) ≠ absorbingNumber I` |

So the certificate can only be an **attestation**: the external kernel-verified Lean proof, an independent
`lake build` re-verification, the `#print axioms` footprint, and hash pins — *not* a re-encoding as `decide`.

## The attestation certificate (what `certify(pipeline_ring, {problem})` returns)

```
Certificate(tier=2) = {
    "family": "pipeline_ring", "tier": 2, "problem": "4b" | "20" | "27b" | "30c",
    "headline_theorem": <name + Lean type>,
    "verdict": "attested",
    "checker": "lake build (Lean 4.31.0 + Mathlib rev v4.31.0) + verify.sh 5-check harness",
    "axioms": ["propext", "Classical.choice", "Quot.sound"],   # recorded from our re-verification; NO sorryAx
    "repository": "Pengbinghui/pipeline-math @ 69d7df765a8f… (public)",
    "reproduction": <the exact clone → cache get → verify.sh recipe>,
    "references": [CFFG 2014, pipeline-math repo, + problem-specific],
    "artifact": <see "the download problem" below>,
}
```
The checker is the authors' own `scripts/verify.sh` (five checks: frozen SHA pins → banned-keyword scan → clean
`lake build` → `#print axioms` = standard set → `@Frozen = @Proof := rfl` no-drift gates). A pass means the
frozen statements are byte-identical to what we audited, the proofs have exactly those types, and the axiom
footprint is standard — the honest Tier-2 verdict.

## The open design question (unanimous, load-bearing): the download problem

A Tier-2 artifact is **a whole multi-file Lake project** (9–11 first-party `.lean` + `lakefile.toml` +
`lean-toolchain` + `lake-manifest.json` + `scripts/`), and it only re-verifies **against a specific Mathlib**
(rev `fabf563…`). So the Tier-1 recipe — "download one self-contained `.lean`, run the kernel" — does not carry
over. The three options:

1. **Recipe + pins (recommended).** Publish the *pinned* `lake-manifest.json` + `verify.sh` + `frozen.sha256`
   + a reproduction recipe, and link the **public** `Pengbinghui/pipeline-math @ 69d7df7` for the sources. The
   "artifact" is the recipe + the hashes + our recorded axiom footprint; re-verification clones the public repo
   and runs `lake exe cache get && scripts/verify.sh`. **Smallest, and honest** — the sources are already
   public, so nothing is hidden; the only dependency is that the Mathlib olean cache stays hosted.
2. **Vendor the first-party tree** as a downloadable tarball (tens of KB) — removes the dependence on the source
   repo staying up, but still needs Mathlib fetched. Marginal gain over (1) since pipeline-math is public.
3. **Full self-contained bundle** with Mathlib oleans (multi-GB). Impractical for a static site; rejected.

**Recommendation: option 1.** Because pipeline-math is *public*, the Tier-2 "download" is a **reproduction
recipe + pins + our independent axiom-footprint attestation**, not a file. Honest caveats to state on the page:
re-verification needs `elan` + network + the leanprover-community Mathlib cache for rev `fabf563…`, and costs
minutes–to–tens-of-minutes (vs a Tier-1 `decide`, which is instant and self-contained). This is the genuine
Tier-1/Tier-2 asymmetry, and naming it is part of the value.

## Folding Tier 2 into the domain (later)

- Add a `pipeline_ring` family to `counterexample_domain.py` whose `certify` returns the attestation record
  above (no Lean emission — it references the external proof + recipe).
- The `Certificate` shape already accommodates it (`tier` field; `kernel.check = "lake-build"` instead of
  `"decide"`). Publishing maps to a Calculemus cycle exactly as Tier 1 does, but the "artifact" is the recipe.
- **Trigger to fold in:** when we want the pipeline-math attestations surfaced *through the domain* (one
  `certify` entry point) rather than as their own standalone cycles. Until then, Tier 1 stands alone and Tier 2
  is fully specified here.

## Honest EV
Audit / verification-**amplification** — the value is a *reproducible, independently-attested* record of
someone else's kernel proof, plus the honest statement of what re-verification costs. It mints nothing and
touches no trust surface. Not a re-derivation; not new mathematics.

## Open questions for the operator
1. **Fold-in timing** — keep Tier 2 as standalone cycles (current) or add the `pipeline_ring` family now?
2. **Download option** — confirm option 1 (recipe + pins, lean on the public repo) vs vendoring the first-party
   tree (option 2)?
3. **Mathlib-cache durability** — do we want a fallback if leanprover-community stops hosting rev `fabf563…`
   oleans (e.g. record the toolchain + a note that a from-source Mathlib build reproduces it)?

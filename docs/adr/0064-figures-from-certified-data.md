# ADR 0064 — Figures: deterministic SVGs generated from kernel-checked data

**Status:** **BUILT.** Adds report-only ``figures[]`` to a published law — SVG renderings of the
*geometric content* of a law's witness data, so the reading room can show what a certified object
looks like (a cap set on the SET board, an orthogonality graph, a difference family). The **trust
boundary is untouched**: a figure is a *rendering of kernel-checked data, never evidence*; nothing
reads ``figures`` on the promotion path.

## Context

The amplified shelf now carries genuinely geometric laws (Kochen–Specker rays, cap sets, Steiner
difference families, blocking sets), rendered as text only. The operator direction: geometric results
should also be *graphed*, as SVGs. The risk to avoid is a dishonest figure — one drawn from prose, a
paper's picture, or an LLM's imagination rather than from the certified object itself.

## Decision

1. **Figures are generated, never drawn.** Each figure comes from a checked-in generator
   (``scripts/figures/gen_*.py``, pure stdlib) that PARSES the witness data out of the audited
   ``docs/crt/*.lean`` artifact — the exact lists the kernel decided over — and emits SVG. No
   randomness, no timestamps: regeneration is byte-identical (pinned by tests).
2. **Arithmetic consistency is asserted, not assumed.** Where a figure re-computes a relation the
   kernel decided (e.g. the KS orthogonality edges under the Hermitian form over ℤ[ω]), the generator
   re-derives a kernel-decided fact in Python and asserts it (every basis pair orthogonal — the
   Python twin of ``cabello_bases_orth``), so the figure's arithmetic can never silently diverge from
   the kernel's.
3. **Report-only payload field.** ``law_payload(..., figures=[{svg, caption, generated_by}])``; the
   SVG rides INLINE in the law JSON/ledger (single source of truth across the producer and site
   repos), ``generated_by`` names the generator + source artifact. Like ``tier``/``origination``/
   ``novelty_attestation``, it is never consulted by ``TrustPolicy`` / ``VerificationGate`` /
   ``Calculemus.promulgate``.
4. **Site rendering.** The codex-calculemus renderer (schema + ``sync-ledger.mjs`` + ``LawFolio``)
   carries ``figures`` through and renders each as ``<figure>`` with its caption and provenance line.
   Inline SVG is acceptable because every figure enters via a reviewed PR from a deterministic
   generator in this repo — there is no user-supplied SVG path.

## Consequences

- The reading room can show the certified objects themselves; every figure is reproducible from the
  artifact by re-running its generator.
- A wrong figure is a *rendering* defect (caught by the determinism/consistency tests and review),
  never a soundness hole — promotion never reads it.
- First figures: the 20-point SET cap in AG(4,3) and the 9-point EvenQuads cap in AG(6,2)
  (``capset_subgroups`` law), and the 33-ray orthogonality graph retrofitted onto the published
  Kochen–Specker law.

## Non-goals

- No figure generation from prose, papers, or model output; no hand-tuned coordinates beyond fixed
  deterministic layouts (grids, circles).
- No new trust surface: figures do not gate, attest, or certify anything.

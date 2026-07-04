# T9 — approach for the two next candidates

*Formulated 2026-07-04; for review before execution. Both candidates funnel into the publishing spine
we just built (kernel-attestable artifact → Calculemus cycle → downloadable hash-pinned `.lean` + APA
references + GitHub code trail), so neither is a one-off — each auto-produces auditable, public output.*

The T9 corpus (`docs/crt-open-problems-corpus.md`) named these two as the next moves:
- **A. the counterexample-certificate domain** — fold the pipeline-math + Problem-41 counterexamples into one
  `certify(object)` family;
- **B. the Erdős statement-formalization lane**.

This doc formulates both. TL;DR recommendation: **do A first** (it extends the shipped Problem-41 checker and
the shipped domain pattern with the least new mathematics), then **B** (which reuses A's publishing wiring and,
for finite/combinatorial Erdős problems, A's `certify`).

---

## A. The counterexample-certificate domain

### Idea
A reusable `certify(object)` interface — a sibling of the shipped `process_complexity_domain.py` and the
code-bound domain — that turns the one-off open-problem counterexamples into a single, legible,
kernel-attestable family. New module: `scripts/counterexample_domain.py`.

### The honest two-tier structure
Not every counterexample is a finite `decide`. Being honest about that is the design:

- **Tier 1 — self-certifying.** Finite/exact-decidable families where *we* generate a kernel-checkable
  certificate. `certify(object)` runs a bounded exact check and emits a `decide`-closed Lean cert (axiom-free
  where possible), exactly like Problem 41.
  - `monomial_normal` (Problem 41) — **already built** (`scripts/prob41_normality_lean.py`); refactor in as the
    first family.
  - `self_ordered` (Problem 16) — the divisibility predicate `∏_{k<n}(a_n−a_k) ∣ ∏_{k<n}(a_m−a_k)`; refute
    `{n²}` / `{nᵏ}` with an explicit `(m,n)` witness (`decide` over `Int`), positive certs for the base families
    up to a bound.
  - `n_absorbing` (Problem 30a/30b) — the `IsNAbsorbing` / `absorbingNumber` decidable check; reuse the
    Prob30c scaffolding (`IsNAbsorbing`, `absorbingNumber`) already formalized in pipeline-math.

- **Tier 2 — attested.** Structural counterexamples over *infinite* rings (pipeline-math Problems 4b/20/27b/30c)
  whose witnessing property is a genuine proof, not a `decide`. Here `certify` returns the *attestation* — the
  external kernel-verified Lean + our independent `lake build` re-verification + the `#print axioms` footprint —
  with hash-pinned downloadable references. We do **not** re-encode these as `decide`; that boundary is the
  honest line, and stating it is part of the value.

### Interface (sketch)
```python
def certify(obj: dict) -> Certificate:
    # obj = {"family": "monomial_normal" | "self_ordered" | "n_absorbing" | "pipeline_ring", "params": {...}}
    ...

Certificate = {
    "family": str, "tier": 1 | 2, "object": dict,
    "verdict": str, "witness": Any,
    "kernel": {"lean": str, "check": "decide" | "lake-build", "axioms": list[str]},
    "references": list[dict],       # APA — the source paper(s)
    "repositories": list[dict],     # the code trail (source repo @commit, our PR)
    "artifact": {"path": str, "sha256": str},   # feeds the downloadable-cert publishing
}
```
A `registry()` lists the corpus (one entry per certified object); `main()` certifies it all and writes
`docs/results/counterexample_domain.json`, matching the shipped domain pattern.

### Composition with Calculemus (the payoff)
Every `Certificate` maps directly onto the publishing spine: a cycle **finding** (verdict + note), a
**downloadable, hash-pinned** `.lean` artifact (Tier 1) or an attestation record (Tier 2), its **APA
references**, and the **code trail**. So `certify(object)` isn't only internal — a thin `publish_cycle(cert)`
step emits a ready-to-deploy Calculemus cycle. The domain *is* a producer for the reading room.

### Build plan
1. Extract the shared `Certificate` shape + `certify` dispatcher + `registry()`; refactor Problem 41 in as the
   first Tier-1 family (no new math — pure consolidation).
2. Add `self_ordered` (Problem 16) — the cleanest *new* Tier-1 family (pure `Int` divisibility, `decide`).
3. Add `n_absorbing` (Problem 30) on the Prob30c scaffolding.
4. Add the Tier-2 `pipeline_ring` adapter (attestation, using the `lake build` + hash-pinned downloads we shipped).
5. `publish_cycle(cert)` → a Calculemus cycle (finding + downloadable cert + refs + trail).
6. Tests (CI-safe `certify`; REPL-gated kernel) + `docs/results/counterexample_domain.json` + roadmap T9 update.

### Honest EV
Audit / **verification-amplification**. The value is a legible, reusable, kernel-attestable certificate family
plus auto-publishing — *not* new theorems. Same disposition as the shipped domains; no trust surface touched.

---

## B. The Erdős statement-formalization lane

### Idea
A systematic practice for faithfully formalizing Erdős problem **statements** in Lean (not solutions), gated on
faithfulness, feeding the erdosproblems.com *"Formalised statement? — Create a formalisation here"* mechanism.
New producer: `scripts/formalize_erdos.py`, generalizing `docs/erdos/erdos_367.lean`.

### Why statements, not solutions
The Erdős DB is dominated by asymptotic problems the kernel cannot decide (established: Problem 367 explicitly
"cannot be resolved with a finite computation"). Leibniz cannot *solve* them. But it *can* state them faithfully
in Lean — a real contribution the site solicits — and **faithfulness of a formal statement is a
kernel-adjacent judgment**: does the Lean `Prop` capture the English, and do the definitions compute correctly?

### Pipeline
1. **Scout** (parallel workflow) — survey a batch of Erdős problems; tag each by *statement-formalizability*
   (can we write a faithful Lean `Prop`?) and *attackability* (finite/combinatorial vs asymptotic). Output: a
   prioritized worklist. (Do this only once the operator picks the batch — don't pre-run a huge sweep.)
2. **Formalize** — `def`s for the objects + the conjecture as a `Prop`, kernel-checked to elaborate, with
   `#eval` / `decide` anchors on the definitions (Problem 367 pattern: `B₂(9800)=9800`, etc.).
3. **Faithfulness gate** — the crux (below).
4. **Publish** — a Calculemus cycle (`kind: "formalization"`) + downloadable `.lean` + APA ref + the
   erdosproblems.com problem link in the code/source trail; optionally submit to the site.

### The faithfulness gate (the crux — a mis-stated formalization is worthless)
A statement passes iff:
- **Elaborates** — the `Prop` type-checks under a pinned Mathlib.
- **Definitions verified** — every defined object `#eval`s (or `decide`s) correctly on the problem's own worked
  examples (the site and papers give these).
- **Non-vacuous** — not trivially true/false; check by attempting a trivial disproof / a sanity instance, and by
  confirming the quantifier structure matches (a common failure: `∀`/`∃` swapped, or `o(1)` dropped).
- **Independent review** — LLM proposes the Lean; a skeptic lens checks it line-by-line against the English; the
  operator confirms. This is the project's "propose / decide" discipline applied to the *faithfulness of a
  statement*, since the kernel alone can't certify "this matches the intended problem."

### Build plan
1. Generalize `erdos_367.lean` into a reusable pattern + a `formalize_erdos(problem)` scaffold + the
   faithfulness-gate checks.
2. Scout a first batch (operator picks size/filter) → worklist.
3. Formalize 2–3 exemplars — 367 is done; add a couple, ideally including one **finite/combinatorial** problem
   that is *also* attackable (e.g. a tiling/covering question like Erdős 477), which bridges to Candidate A.
4. Publish as cycles; investigate the site's submission mechanism (outward-facing — needs operator sign-off).

### Honest EV
Presentation / amplification. Faithful, kernel-checked formal statements + a contribution to the Erdős
formalization project — **not** solving Erdős problems. The bridge: a finite/combinatorial Erdős problem can
graduate from "statement formalized" (B) to "instance/counterexample certified" (A).

---

## Open questions for the operator

1. **Sequencing** — A then B (recommended: A extends shipped code with least new math), or interleave?
2. **Tier 2 scope** — include the attested `pipeline_ring` family in the domain, or keep the domain Tier-1-only
   (pure `certify(object)`) and leave the pipeline-math attestations as their own already-shipped cycles?
3. **Erdős batch** — which slice to scout first (by tag? by problem-list? a fixed first-N?), and how many
   exemplars to formalize before publishing.
4. **Submitting back to erdosproblems.com** — worth doing (outward-facing contribution), and if so, via what
   mechanism? Needs your sign-off (public, attributed).
5. **New families for A** — beyond {monomial_normal, self_ordered, n_absorbing, pipeline_ring}, any others worth
   seeding (e.g. a McCoy-counterexample family from the now-resolved Problem 9)?

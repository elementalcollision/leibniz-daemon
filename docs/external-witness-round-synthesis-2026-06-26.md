<!--
Synthesis of the 7-model external-witness round on "what should Leibniz focus on next?"
Inputs: Fugu, Fugu Ultra, Deepseek v4 Pro, Kimi, GLM 5.2, Gemini 3.5 Thinking, Qwen 3.7 Max
(operator-collected). Witnesses advised on DIRECTION; invariant 4 keeps the novelty verdict
with the human panel. This narrows the cross-backend conclusion and names the next probe.
-->

# External-witness round (7 models) — synthesis & the correction it forces

**Unanimous on direction, and unanimous on one correction we must accept.** All seven independent
witnesses converged, and — importantly — all seven judged our capstone conclusion **over-generalized**.
Per the project's attack-the-synthesis discipline, we accept the correction.

## 1. The correction (all 7 agree): our slogan was too broad

We wrote: *"soundly-checkable ∧ finitely-encodable = textbook."* Every witness rejected this as
confounded. The defensible claim is narrower:

> **Free-form LLM theorem-*ideation* into two *human-mined, decidable, landmark-dense* showcase domains
> rediscovers catalogued landmarks (or emits malformed frontier prose).**

The confounds they identified (consistent across all seven):
- **Producer sampling/catalogue bias.** An LLM's distribution collapses to densely-tokenized named
  objects (Thue-Morse, Motzkin, Choi-Lam, Robinson, Horn). We measured *"can an LLM ideate frontier
  claims?"*, not *"is the finitely-encodable region exhausted?"*
- **Domain choice.** Walnut (FO over automatic sequences) and SOS (real semialgebraic) are both
  **decidable theories already mined by humans** — the decision procedure *is* the exhaust (Deepseek's
  sharp framing: `finite + sound-checkable + theory-already-mined-by-humans = textbook`).
- **"Finitely encodable" is too broad to carry the claim.** Every Lean theorem is finite; decades of
  computer-assisted mathematics (codes, designs, Ramsey, covering arrays, SAT records) are finite,
  sound-checkable, and *not* textbook. Those are produced by **search over a finite object space**, not
  by an LLM reciting a theorem-shaped sentence.

Net: the binding constraint is real and is at the **producer** — but the fix the witnesses point to is
**search-based production over un-mined finite-object spaces**, not a better LLM and not another decidable
backend.

## 2. Convergence across the six questions

| Q | Convergent answer (7/7 unless noted) |
|---|---|
| 1 Attack | Conclusion over-generalized; confound = LLM catalogue bias + human-mined decidable domains. |
| 2 Missed escape | **Certified finite-witness / extremal combinatorics** via untrusted search (SAT/ILP/CP) with Lean checking only the witness: constant-weight codes `A(n,d,w)≥M`, covering arrays, Ramsey colorings, SAT/DRAT records. (Variants: small finite algebras — Deepseek; term-rewriting termination/confluence — Qwen; Zeilberger/holonomic identities — Gemini.) Objective novelty = improves a public table. Caveat (≥2): this is *computational-record* novelty, may not satisfy a *conceptual*-novelty panel. |
| 3 Flag-algebra bet | **Low EV, not the first move** — estimates 5-12% (mostly <5-10%) for one expert-confirmed result; the float-SDP→exact-rational gap + LLM transcription errors dominate. Cheaper variant if pursued: wrap *existing* flag tooling as an untrusted oracle, restrict the LLM to finite choices, require exact rational re-check; or a fixed small-graph (≤8-vertex) density-inequality micro-DSL via exact rational LP. |
| 4 Goal ranking | **(c) Verification amplification #1 — unanimously.** Then (b) high-volume correct output; (a) autonomous discovery **last, unanimously.** Added framings worth noting: certified finite-witness *record factory* (best remaining autonomous bet); formalization-sanding / boundary-curation / proof-refactoring / certificate-ingestion. |
| 5 Honest call | **Conclude the free-form-LLM autonomous-discovery track as a measured negative result** — but state it *narrowly* (do NOT claim sound systems can't do new math). Stop adding decidable backends. Allow **exactly one** remaining autonomous lever: replace LLM theorem-ideation with finite-object *search* over externally-benchmarked frontier tables. |
| 6 Next step | Two cheap, decision-changing probes recur: **(α) zero-LLM enumeration audit** (brute-force the backend grammar, filter vs literature, blind-grade — directly falsifies *our* slogan); **(β) finite-witness table pilot** (codes/covering-arrays; Lean-checked witness; GREEN = ≥1 expert-confirmed public-table improvement). Gemini/GLM also propose a verification-amplification probe (feed in-reach human-posed *open* problems; GREEN = ≥1 Q.E.D.). |

## 3. What this changes

- **Amend the recorded conclusion** to the narrow form above (done in this doc; the roadmap capstone
  should cite this correction).
- **The autonomous-discovery quest is not quite dead — it has one untested lever**: *search-based
  production* (LLM proposes parameters/encodings/mutations; an untrusted solver finds the finite witness;
  Lean checks only the witness). This sits squarely inside the trust boundary (propose/decide preserved)
  and gives **objective** novelty criteria (public-table improvement), sidestepping the subjective
  textbook-grading the panel struggled with.
- **The strategic home is verification amplification** (7/7) — the best use of a system whose proven,
  earned strength is *soundness, not ideation*.

## 4. Recommended next move (measure-before-build, cheapest decisive probe first)

**Run the zero-LLM enumeration audit (Probe α) as the liquidation audit of our own conclusion**, because
it is the cheapest test that *directly* attacks the unanimous objection and is decision-changing either
way:
- Build: a pure symbolic/brute-force enumerator over a backend grammar we already run (e.g. all small
  uniform morphisms × pattern-avoidance / power-free predicates within a pre-registered complexity
  ceiling), batch-decide with the existing Walnut backend, exact-match-filter against OEIS/known
  literature, blind-grade survivors. **No LLM in the producer.**
- **GREEN:** ≥1 sound, faithful, decided theorem survives literature-filtering and is blind-graded
  non-textbook — *the LLM never proposed it.* → our slogan is falsified; the lever is **search**, and
  Probe β (finite-witness table factory) becomes the autonomous direction.
- **RED:** 0 survivors after sweeping the bounded space → even absent LLM bias, the *decided* region of
  these mined theories is human-exhausted; autonomous discovery in decidable showcase domains closes
  cleanly, and the project pivots wholesale to verification amplification.

Either outcome is publishable and decision-changing. Verification amplification is the strategic
direction **regardless** of α's result; α only decides whether a narrow autonomous *search* track lives
alongside it.

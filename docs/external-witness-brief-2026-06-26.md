<!--
External-witness elicitation for the post-arc direction decision. §1 is the operator-facing
framing (what we are asking, the candidate directions, how responses are used). §2 is the
verbatim, self-contained prompt to give EACH witness. Precedent: the ADR 0036 multi-model
external review rounds. Witnesses advise on DIRECTION; they do NOT decide novelty (invariant 4
reserves the novelty verdict for the human blind panel).
-->

# External-witness brief — what should Leibniz focus on next? (2026-06-26)

## §1 The decision we are putting to the field (operator-facing)

The post-R6 **sound-backend discovery arc is concluded with a measured finding**
(`docs/discovery-ceiling-cross-backend-finding.md`): across two independent sound backends, the
*soundly-checkable **and** finitely-encodable region is the textbook region*, and the binding
constraint is **novelty at the producer — a structural encoding gap** — not soundness, reach, or prover
power. The trust machinery is vindicated (0 unsound; no LLM ever decided; `test_invariants.py`
byte-identical throughout).

We are asking a field of external witnesses one question — **what should Leibniz focus on next?** — and
asking them to *attack the conclusion first*. The candidate directions we already see (witnesses may
reject or extend these):

1. **Producer frontier-encoder** — build a flag-algebra / graphon-moment encoder (+ in-loop symbolic
   self-check) so the conjecturer emits frontier inequalities as finite SDP-ready objects the SOS
   backend can consume. The only identified ceiling-breaker; substantial, domain-specific, uncertain.
2. **Conclude discovery; pivot to yield-mode** — accept the daemon as a vindicated sound-verification
   instrument and redirect it to high-volume *correct* output (e.g. seeding a Lean library of true
   elementary math), where breadth, not novelty, is the goal.
3. **Reframe the goal as verification amplification** — stop chasing *autonomous* novelty; let humans
   propose frontier conjectures and have the daemon soundly decide/check them (the producer constraint
   then moves off the critical path).
4. **A lever the witnesses identify** that we have not — explicitly solicited.

How responses are used: we collate the witness recommendations, look for convergence and for the
strongest unanticipated objection or lever, and turn the result into the next ADR / measure-before-build
probe. **Witnesses advise on direction only** — per invariant 4, the novelty verdict on any actual
output remains the human blind panel's, never a model's.

---

## §2 The prompt (verbatim — give this, unedited, to each witness)

> **You are an external witness reviewing the strategic direction of an automated mathematics project.
> Be adversarial, concrete, and calibrated. No flattery. Attack the reasoning before you advise. If you
> are uncertain, say so and say what would resolve it.**
>
> ### The project (fixed constraints — do not propose weakening these)
> "Leibniz" is an agentic theorem daemon with one inviolable rule: **LLMs only PROPOSE; only mechanical
> checkers DECIDE.** A statement earns `Q.E.D.` *only* when the Lean kernel verifies a proof; faithfulness
> (does the formal statement match the intended claim?) and novelty are separate gates. Soundness — "nothing
> false is ever stamped" — is the project's reason to exist and is non-negotiable. Any proposal that relaxes
> the trust boundary is out of scope; assume it stays exactly as is.
>
> ### What was done, and the measured result
> The post-R6 goal was to turn a sound *re-prover* of known math into a *discovery* engine without weakening
> the boundary. An earlier finding localized the limiter to the faithfulness **test** (a bounded
> integer-box `[0,64]` linter over a tiny arithmetic DSL — it can only certify elementary, locally-checkable
> facts). The escape built and measured was **proof-carrying faithfulness**: pluggable *sound backends* that
> decide unbounded/exact classes the box cannot, each behind a measure-before-build reachability gate.
>
> Two backends were taken through the full build/probe → verify arc:
>
> - **Walnut (first-order logic over k-automatic sequences) — built and run live.** It soundly decides
>   ∀n statements over sequences like Thue-Morse / Rudin-Shapiro / Fibonacci / Tribonacci. After fixing
>   encoding artifacts (a faithfulness lint) and conjecturer mode-collapse (session memory + breadth
>   rotation), a live run produced **11 sound, diverse, faithful decided records** — and an independent
>   12-agent verification rated **all 11 textbook** (0 plausibly-novel). Checkable properties (power-
>   freeness, avoided factors) of *famous* sequences are exactly the studied ones.
> - **SOS / Positivstellensatz (real polynomial nonnegativity) — probed, build deferred.** Exact rational
>   certificate re-checking is feasible and cheap; it reaches genuine ∀x∈ℝⁿ claims the box cannot state; and
>   uniquely, an SOS certificate can be re-checked by the Lean kernel itself, so this rung has a genuinely
>   **Q.E.D.** path. But the *novelty* go/no-go came back **RED**: a two-arm probe (a default conjecturer
>   vs. one explicitly steered toward the research frontier) generated 24 polynomial-inequality conjectures
>   and scored each on three axes — *in-SOS-reach*, *unbounded-real* (beyond the box), and
>   *plausibly-non-textbook*. The intersection of all three was **0 of 12 in both arms**. Frontier-steering
>   did not help; it *degraded* quality (more false / mis-stated conjectures).
>
> ### The conclusion we drew (steelman it, then try to break it)
> Across both backends a **perfect anti-correlation** held: every conjecture that was *plausibly-novel* was
> *not* in the backend's reach, and every conjecture *in reach* was *textbook*. The two never co-occurred.
> The mechanism: the only objects an LLM can hand a sound backend as a clean, true, modest-cost,
> self-contained claim are the catalogued landmarks (e.g. Motzkin / Choi-Lam / Robinson / Horn for SOS;
> power-freeness of famous words for Walnut). The moment it reaches for genuine frontier content, the object
> *leaves the backend's finitely-encodable class* — flag-algebra / hypergraph-Turán / clique-density
> inequalities live over infinite-dimensional graphon–flag moment bodies, not finite real-vector
> semialgebraic sets; proof-complexity statements are *non-existence* meta-claims; the merely-finite ones
> arrived riddled with transcription errors. **Conclusion: the soundly-checkable *and* finitely-encodable
> region is the textbook region; the binding constraint on discovery is novelty at the *producer* — a
> structural encoding gap — not soundness, reach, or prover power.**
>
> ### Your task — answer all six, briefly and concretely
> 1. **Attack the conclusion.** Is "soundly-checkable ∧ finitely-encodable = textbook" actually right, or is
>    it an artifact of our setup (sample size, the two domains chosen, the LLM conjecturer used, the
>    "textbook" labeling, the finite-encoding assumption)? Give the single strongest reason it might be
>    *wrong*, and the cheapest experiment that would expose the error.
> 2. **Name an escape we may have missed.** Is there a sound-checkable class — or a *reformulation* of a
>    frontier class into a finite, backend-consumable form — that is plausibly **non-textbook** and that an
>    LLM could actually produce? Be specific (domain, certificate type, why it's both reachable and novel).
> 3. **The producer-encoder bet.** We could build a flag-algebra / graphon-moment encoder so the
>    conjecturer emits frontier density inequalities as finite SDP-ready objects. Estimate, with a
>    confidence level: the probability this yields even one genuinely-novel (expert-confirmed) result within
>    a bounded effort, and whether it is the highest-expected-value move. Propose a cheaper variant if one
>    exists.
> 4. **Alternative goal framings.** Rank these for a sound, trust-bounded daemon, and add any you prefer:
>    (a) autonomous novel discovery; (b) high-volume *correct* output (e.g. auto-seeding a verified Lean
>    library); (c) *verification amplification* — humans propose frontier conjectures, the daemon soundly
>    decides them. Which is the best use of a system whose proven strength is soundness, not ideation?
> 5. **The honest call.** Should the autonomous-discovery quest **continue** (and on which single lever) or
>    **conclude as a measured negative result**? Defend the choice on expected value, not optimism.
> 6. **One falsifiable next step.** Give exactly one next measurement or build, stated so its result would
>    *change the decision*, with a clear GREEN/RED criterion — in the project's measure-before-build style.
>
> Constraints on your answer: respect the trust boundary (no soundness relaxations); prefer concrete
> mechanisms over generalities; distinguish what you *know* from what you *guess*; and end with a single
> prioritized recommendation in one sentence. You are advising on **direction**, not judging the novelty of
> any specific result — that is decided separately by a human panel.

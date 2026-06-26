# ADR 0036 — Genuine discovery under a hard trust boundary

**Status:** Proposed (design only — no code, awaiting operator approval). Synthesis of an in-harness
5-design panel + adversarial pass + an **independent 5-model external review** (Fugu, DeepSeek V4 Pro,
Kimi, GLM 5.2, Gemini 3.5 Thinking — `docs/external-review-novelty-frontier.md`).
**A round-2 external review of *this synthesis* (6 models incl. Fugu Ultra —
`docs/external-review-2-genuine-discovery.md`) substantially revises the recommendation. §10 records
that reconciliation and SUPERSEDES §3, §6, and §8 where they conflict. Read §10 first.**
**Date:** 2026-06-25
**Predecessors:** ADR 0034 (conjecturer-side novelty — §12 kill), ADR 0035 (faithfulness-DSL
expressiveness — Stage A killed as a novelty lever; **§7.1 correction**).
**Trust boundary:** untouched. Nothing here weakens "an LLM never decides a proof; nothing false or
un-faithful is ever stamped `Q.E.D.`" Design only; the eventual builds keep `gates/` and
`tests/test_invariants.py` byte-identical on the proved path.

---

## 1. The premise (corrected)

The measured arc (0034 + 0035) ruled out two orthogonal novelty levers — the proposal **source**
(mining: 2× yield, 0 blind-novel) and the DSL **grammar** (sound `a^n mod m`: genre moved, 0
blind-novel). The first draft concluded "the bounded-mechanical-faithfulness *model* caps the
daemon." A 5-model external review **unanimously** corrected that, and the correction is right
(ADR 0035 §7.1):

- **What is true and measured:** Leibniz *as built* — a **pointwise, bounded-box `[0,64]` semantic
  linter over a tiny arithmetic DSL, used as the *sole* faithfulness test** — is capped at
  elementary, locally-checkable facts.
- **What was over-stated:** "bounded mechanical trust caps novelty" is false. **Bounded *trust* (a
  small checker) ≠ bounded *domain* (a small evaluation box).** A small kernel checks arbitrarily
  deep proofs — four-colour, Kepler/Flyspeck, Feit–Thompson, Robbins (auto-proved, *not* trivial),
  Boolean-Pythagorean (a 200-TB SAT certificate, independently re-checkable). The wall is the
  *pointwise bounded-box linter*, not the kernel and not mechanical trust.
- **Why the box is the wall (Gemini's sharpening):** pointwise-local checking is structurally blind
  to global/asymptotic structure. Pólya fails at 906,150,257; Mertens past 10¹⁴; Skewes past 10¹⁹;
  Fermat-primes at F₅. A small window cannot see the phenomena that make mathematics non-elementary.

So the question is not "accept the boundary" but **"replace the *linter* while keeping the
*boundary*."**

## 2. The reconciled landscape

The strongest cross-source signal (5 external witnesses + the in-harness panel agreeing
*independently* — these are different model families, so convergence is real signal, not a shared
blind spot):

- **Convergent (high confidence):**
  1. The 3-body faithfulness gap (formal-statement ⟷ human-claim) **relocates to *validation***
     (human-intent → formalized-claim) under any kernel-checked scheme — it never vanishes, and that
     *validation vs verification* boundary is the right, auditable place for it (classic formal
     methods: VDM, Event-B, refinement, CompCert's spec boundary).
  2. A **separate conjecture/evidence ledger** (Ramanujan-Machine precedent) is a real contribution
     **iff** strictly separated from `Q.E.D.` and its evidence is *sound* — and noise/dilution
     otherwise.
  3. **Proof-carrying faithfulness** (kernel/CAS-checked *certificates*, with bounded Z3 demoted to
     lint) is the sound escape from the box — including **exact, unbounded** classes.
- **Divergent (open — record, don't resolve):** whether the escape *reaches genuine novelty* (Fugu /
  DeepSeek: yes-in-principle; Kimi: relabels the wall to autoformalization; GLM: accept the boundary
  but pivot to *abstraction mining*; Gemini: yes via structural invariants). This ADR treats the
  escape as **sound-but-novelty-unmeasured** and pre-registers the test.
- **Skepticism note:** Gemini's specific benchmark numbers/citations (BPF "89.6%", "Chao Wang 2026",
  Verus-SpecGym, HierSVA) are unverified and possibly synthetic — its *concepts* (structural-invariant
  verification, bidirectional fingerprinting) are used here; its *numbers* are not cited as fact.

## 3. Recommendation — two tracks

### 3a. Track 1 (ship now): the CONJECTURE tier — honest output stratification

A **separate ledger** of machine-observed-but-unproved candidates, never `Q.E.D.`, never touching the
proved path. Trust holds *vacuously* (no proof edge exists). Its value is honest classification and a
curated proof-backlog; it almost certainly inherits the 0-novel read and does **not** claim to break
the ceiling.

The adversarial pass found the naïve spec **unsound as written** — these fixes are mandatory:

1. **Sound evidence or no stamp.** `find_gaming_witness`/`find_counterexample` return `None` ("no
   witness") for *un-encodable* predicates — exactly the richer claims this tier hopes to surface. So
   the evidence stamp must gate on **`encodable(claim)` AND a *conclusive* `decide_unsat == True`**,
   and must **distinguish "searched `[0,64]`, none found" from "could not mechanically search"** —
   never collapse `None` into a "no counterexample" banner. (This is the ADR 0020/0030 vacuous-PASS
   failure mode; it must not reappear in a new ledger.)
2. **Use the *fixed* probe, not the bare spine.** Route through the ADR 0022 coverage+property probe
   (search *inside* `established_domain`), not the legacy gaming form that is vacuously UNSAT for any
   tautologized property.
3. **Publication bar ≥ the proved path.** A conjecture is *lower* confidence than a kernel-proved law,
   so it must carry **at least** the same operator + PROD publish gate (`calculemus.publish`), never
   a lower one.
4. **Capture refutations.** When the search *finds* a counterexample in `[0,64]`, record it
   (`REFUTED` with the witness) — the single most valuable output of the tier.
5. **Dedup with the Codex.** A conjecture later promulgated must transition out of the conjecture
   ledger (a `PROMOTED_TO_CODEX` reason), never live in both.
6. **Cost budget.** The evidence search runs on the hot path; bound it (it reuses the existing Z3
   timeout/box, so cost is the same order as the faithfulness gate — state the bound).
7. **An invariant-adjacent guard test** that the "[0,64], none found" banner is *never* emitted on a
   `None`/un-encodable search (the new path is otherwise unguarded — `test_invariants.py` guards the
   proved path, not this one).

**Retirement condition (so it can fail):** if a blind sample of the conjecture ledger is
indistinguishable from the promulgated corpus (same 0-novel, same genres) **and** the operator
consumes <X% of the backlog within N cycles, the tier is dead weight and is removed.

### 3b. Track 2 (the real technical bet): PROOF-CARRYING faithfulness

Replace the bounded-box linter *as the `Q.E.D.`-earner* with a **checkable certificate** of the
statement↔claim correspondence. Bounded Z3 stays — demoted to a cheap **lint** pre-filter, never the
faithfulness authority. Staged by soundness-risk / TCB-growth, lowest first:

- **Stage A — exact-unbounded structural-invariant certificates (the safe first rung).** For claims
  expressible as **algebraic identities** (e.g. a polynomial identity `P ≡ 0` in `ℤ[x,y]`, or a
  conservative-matrix-field commutator), faithfulness is decided **exactly and over an *infinite*
  domain** by polynomial-identity testing / a Gröbner certificate — finite linear algebra on
  coefficients, independently re-checkable. This escapes `[0,64]` for a real class **without a new
  untrusted oracle** (the certificate is re-verified, not trusted). It is the concrete counter to
  "everything checkable is elementary," and the lowest-TCB way to test the escape.
- **Stage B — kernel-proved statement↔claim bridge (harder; gated on Stage A).** Render the claim as
  a Lean `Prop` and require a **kernel-checked** `claim_prop ↔ statement` (or `→`) proof, unbounded
  and sound by the kernel. Two honest costs, both named: (i) the bridge proof is **undecidable in
  general** — for a genuinely novel claim the prover may not close it, so the path collapses to DEFER
  (the expressiveness wall becomes a *proof-synthesis* wall); (ii) the **claim→Lean renderer is a new
  load-bearing trusted artifact** whose bug is a kernel-checked proof of a *mis-statement* — the
  TCB-growth hole ADR 0035 §3 named, here load-bearing. Therefore Stage B ships only behind an
  **adversarial soundness review of the renderer** (ADR 0021/0030 precedent) and **DEFERs on
  synthesis failure** (never falls through to a judge).

## 4. Why the trust boundary stays intact — and where the residual gap lives

| Edge | Proved path (unchanged) | Conjecture tier (3a) | Proof-carrying (3b) |
|---|---|---|---|
| proof ↔ statement | `LeanVerifier.discharge` (sole `kernel_verified` writer) | **absent** — never `Q.E.D.` (invariant #1 vacuous) | unchanged kernel proof |
| statement ↔ claim | bounded-box gaming-witness | **sound** evidence stamp (§3a fixes) or none | **certificate**, kernel/independently re-checked; fail → DEFER |
| residual gap | human-intent → claim (today: hidden in the box) | same, but the bound is *stamped & visible* | human-intent → *formalized*-claim (validation), **auditable** |

- **`test_invariants.py` stays byte-identical** on the proved path; the new paths add **their own**
  guard tests (the adversarial pass correctly noted "byte-identical" proves the new path is
  *unguarded*, not safe — hence §3a.7 and the Stage-B renderer review).
- **The residual 3-body gap is relocated to validation, not eliminated** (5/5 external agreement).
  Mitigation (Fugu): **formal-first publication** — the formal theorem is the source of truth, the
  human-readable statement is *generated* from it, prose is commentary. That shrinks the gap to the
  trusted glossary + rendering discipline, where it is audited rather than hidden. Adopt this.

## 5. Honest verdict on the §4 recursion

- Track 1 (conjecture tier) does **not** reach novelty and says so; it relocates the *output
  category*, not the math ceiling. Its risk is a **credibility** surface (an unsound evidence stamp),
  closed by the §3a fixes.
- Track 2 (proof-carrying) **soundly removes the expressiveness ceiling** — this is the one direction
  that is not pure relocation (it changes *what can be faithfully stated*, not just the genre). **But
  whether it yields *blind-novel* results is unmeasured.** Algebraic identities could be a third
  textbook genre. So the honest claim is: *the sound path out of the box*, to be **measured** exactly
  as Stage A was, with a pre-registered kill — not "novelty achieved." We do not let the correction
  swing from over-pessimism to over-optimism.

## 6. Recorded alternative — abstraction mining (GLM)

Instead of outputting *theorems*, output **optimal abstractions** — definitions and lemma-schemas
that compress a surveyed proof space (anti-unification over many elementary proofs → a new definition
+ schema). An "abstraction telescope": it does not find new stars (theorems) but grinds the lenses
(definitions) humans see them through. Trust-trivial (definitions are checked, not claimed true).
Recorded as a genuine alternative contribution; not the primary, because its *interestingness* is as
unmeasurable as novelty and it is a larger build than Track 1.

## 7. Pre-registered success measures / kill conditions

Reuse the **blind human novelty read** (ADR 0034 §5) verbatim — the only referee, and it must stay
human (an LLM novelty judge violates invariant #4). The mechanical signature-distance / `None`-
coverage metric is a **tripwire only, never a gate**.

- **Conjecture tier:** ships on the §3a soundness fixes (value = honest classification, delivered on
  merge); retired per §3a's retirement condition if it is dead weight. A blind sample is read purely
  to confirm the ceiling (predicted: still 0-novel).
- **Proof-carrying Stage A:** kept iff a blind read of certificate-faithful promulgations **beats the
  0/N baseline by a pre-set margin** AND they clear triviality above chance. A rightward
  signature-distance shift is **not** a success signal. Still-0-novel with sound certificates is the
  *failure-with-a-finding*: it would show the ceiling survives even exact-unbounded faithfulness, and
  Stage A reverts to opt-in.
- **Proof-carrying Stage B:** built only if Stage A's blind read is non-zero **and** the renderer
  passes adversarial soundness review; killed if synthesis rate is too low to produce data.

## 8. Staged plan — what to build first, and what we do NOT do

1. **First: Track 1, the conjecture tier, *with all §3a fixes*** (~moderate; the soundness fixes are
   the point). Honest, shippable, zero trust cost, immediately useful as a curated backlog.
2. **Then: Track 2 Stage A** (exact-unbounded structural-invariant certificates) — the lowest-TCB
   probe of the real escape; measured by the blind read.
3. **Only if Stage A's blind read is non-zero: Track 2 Stage B** (kernel bridge), behind the renderer
   soundness review.
4. **Do NOT:** weaken the proved path's gate; introduce an LLM faithfulness/novelty judge; ship the
   conjecture tier without the §3a sound-evidence gate; build Stage B before Stage A measures; or cite
   the external review's unverified numbers as fact.

## 9. Consequences

- If approved: the daemon gains an honest conjecture/backlog tier (now), and a sound, staged path to
  *unbounded* faithfulness (next) — the first direction in this arc that escapes the box without
  weakening trust. The novelty question becomes *measurable* on the proof-carrying track rather than
  conceded.
- The trust boundary is unchanged throughout: the proved path and its invariants are untouched; every
  new path is sound-evidence-or-DEFER, with its own guard tests and (for the renderer) an adversarial
  review.
- This ADR ships its own objections: the conjecture tier's evidence-stamp unsoundness (§3a, fixed),
  the proof-carrying TCB growth + undecidability (§3b), and the honest "novelty unmeasured" caveat
  (§5). The 5-model external review corrected the premise; this records the correction rather than
  defending the original over-claim. *Calculemus.*

---

## 10. Round-2 external review — revised recommendation (supersedes §3, §6, §8)

The round-1 synthesis above was itself sent back to the panel (now **6 models**, +Fugu Ultra —
`docs/external-review-2-genuine-discovery.md`) with one instruction: *attack the synthesis.* They did,
and the result changes the plan more than round 1 changed the premise. The net is not a new build
order — it is **measure before you build any of this**, plus a re-ranking of the levers. The four
substantive corrections, then the disposition.

### 10.0 Retraction first — discount the convergence

§2 weighted as "high confidence" the points where the external models *independently converged*,
arguing different model families ⇒ real signal. **Round 2 retracts this, and the panel retracts it on
itself:** the reviewers note (unanimously) that they share a training distribution and the
formal-methods Zeitgeist, so their agreement on "3-body → validation / proof-carrying is the escape"
is a **shared inductive prior, not independent expert confirmation**. Consequence: weight the
*falsifiable, cheap experiments* they propose over the *conceptual consensus* they reached. Everything
below is organized around experiments, not opinions.

### 10.1 Stage A is inert — confirmed 6/6; killed as a novelty rung (supersedes §3b Stage A, §8.2)

The triviality-trap worry is correct and unanimous: pure polynomial-identity / Gröbner certificates
prove exactly what `ring` already closes, so the **non-triviality gate quarantines them before
faithfulness ever runs** — "a bridge to a town already razed" (GLM). DeepSeek is sharpest: anything
*exact-certificate-checkable* is, by that token, *decidable*, hence trivial-gated — so there is **no
class that is simultaneously (a) exact-cert-checkable, (b) non-trivial, and (c) expressible without
enriching the DSL.** Stage A as specified (§3b) is therefore **dead.** It is *salvageable only* by
enriching the claim language into specific **certifying fragments**, each a real DSL extension and (GLM)
"a specialized scalpel, not a general escape":

- **SOS / Positivstellensatz** — semialgebraic inequalities `P ≥ 0` (external SDP finds a rational
  SOS cert; the *kernel check* is `ring` on the decomposition; `nlinarith` fails on e.g. Motzkin).
- **Wilf–Zeilberger / creative telescoping** — hypergeometric sums `Σₖ F(n,k) = S(n)` (rational
  certificate `R(n,k)`; the check reduces to a rational-function identity = `ring`; needs sums /
  binomials / factorials in the DSL).
- **Ideal-membership / Nullstellensatz** — algebraic entailment `⋀ hᵢ = 0 ⟹ f = 0` via `f = Σ qᵢ hᵢ`.
- **Recurrence / automata / C-finite (Walnut-style)** — modular periodicity, linear recurrences,
  automatic sequences (needs recurrence primitives).

These are genuine — but each is a build of its own, and GLM/DeepSeek are right that the *general*
escape is Stage B + a richer language. So Stage A is **reclassified**: not "the safe first rung," but
"a menu of certifying-fragment experiments," each gated behind the measurements in §10.4 and below the
cheaper bets. The honest one-liner the round-2 brief asked for: **Stage A is inert; the real escape is
inseparable from Stage B + a richer claim language.**

### 10.2 Proof-carrying / Stage B is a *soundness* escape, not a *discovery* escape (refines §3b, §5)

Reaffirmed 6/6, sharpened: Stage B converts the *epistemic* wall (`[0,64]` categorically forbids
trusting beyond the box) into a *computational* wall (the bridge proof may DEFER). Fugu Ultra & GLM
call this a **productive, honest relocation** — a computational wall yields to compute / heuristics /
RL, an epistemic one cannot, and it is the *intrinsic* Gödel–Turing wall, so you "stop lying to
yourself." Kimi & DeepSeek warn it can be **equally fatal in practice** ("a cleanroom inside a sewer";
"a smaller, stricter Flyspeck, not a truth-oracle"): synthesis is AI-complete, so the bridge will
DEFER on ~all interesting claims, and the **renderer becomes the new load-bearing TCB**. Two firm
consequences:

1. **The renderer must be UNTRUSTED.** The kernel-checked **formal object is normative**; the English
   prose is *non-authoritative commentary* generated from it (formal-first publication, already in §4
   — now mandatory, not a mitigation). A renderer bug otherwise yields a kernel-checked proof of a
   *mis-statement* (the documented `Δ∀` / `ΔH` / vacuous-antecedent gaming modes).
2. **Do not build the renderer first.** Gate Stage B behind the §10.4 oracle-reachability benchmark.
   Stage B is a **high-assurance platform for (largely human-driven) formal mathematics** — a real
   contribution — but **not** an autonomous-novelty engine, and must not be sold as one.

### 10.3 The conjecture tier is numerology unless it leaves the box — → "Observatory" (supersedes §3a "ship now", §8.1)

The round-2 catch that lands on *my hardened* Track 1: §3a made the evidence stamp **sound**, but
**sound ≠ out-of-sample.** An in-sample "encodable + conclusive `decide_unsat` over `[0,64]`, none
found" stamp is *still numerology* — it is the strong-law-of-small-numbers (Pólya, Mertens, Skewes),
and multiple-testing over many generated predicates destroys its significance. To be a contribution
rather than "epistemic spam diluting a Codex," the tier must raise its evidence standard to **one of**:

- **Out-of-sample / MDL (Fugu, Fugu Ultra):** generate the predicate on a *restricted* domain (e.g.
  `[0,32]`); require it to **compress** (predicate far shorter than the data it summarizes) **and**
  to predict a *disjoint, harder* holdout (`[33,256]`) **unmodified**. Pre-registered, frozen.
- **Structural impedance (GLM):** don't stamp "no counterexample"; stamp **where the proof engine
  structurally failed** — "goal reduces to G′; tactics T₁,T₂,T₃ fail at sub-goal G″ requiring
  induction on decreasing metric M; witness W." This converts the tier from numerological exhaust
  into a **high-value todo-list for human mathematicians.**
- **Structural-invariant certificate (Gemini):** a coboundary / commutator / symmetry identity
  checkable over the polynomial ring (Ramanujan-Machine "conservative matrix field" precedent) —
  "proven algebraic structure awaiting analytic identification," not a numerical coincidence.
- **Linkage to a recognized open problem (Kimi).**

And the **success metric is conversion-rate-to-proofs vs a baseline**, not raw conjecture count.
Rebranded the **Observatory** (Fugu), explicitly *not* Codex-stamped. The §3a soundness fixes all
still apply; they are necessary, not sufficient. "Ship now" (§8.1) is **withdrawn** pending an
out-of-sample standard.

### 10.4 Abstraction mining is promoted from alternative (§6) to the *leading* candidate

6/6 emphatic, and the strongest *divergent-from-round-1* signal: the panel over-weighted the
**acceptance** boundary (how to *trust* a theorem) and under-weighted the **proposal** boundary (how
to *invent* the mathematics). The two prior experiments moved the proposal **source** and the contract
**grammar** — but never the **ontology**. Math does not scale by longer proofs of flat statements; it
scales by **definitions / lemma-schemas that compress** the reasoning space (Lenat's AM/Eurisko,
Colton's HR, modern concept-formation). "Your vocabulary is too small to think thoughts not already in
textbooks." This is the one lever that changes the **type** of output and attacks the real bottleneck:
**representation, not inference or faithfulness.**

Decisively, it comes with the **cheapest falsifiable pre-test in the whole program**, run on *existing
data, no trust-boundary touch* (GLM's "build a compressor first"):

> Run anti-unification / macro-extraction over the **existing promulgated proof corpus** and measure a
> **Proof-Compression Δ** (Kolmogorov / DAG-size). **If 0 macros compress the trivial corpus, those
> theorems are structurally disjoint noise and the whole abstraction-mining thesis is dead** — a cheap
> kill. **If one macro compresses many, *that macro is the real candidate*** — promote it to a
> first-class definition (no richer claim language needed). Anti-gerrymandering gates (Fugu): short
> description length, proof-compression, held-out transfer, *reuse* (downstream concept productivity),
> stability, legibility.

§6 is hereby promoted: abstraction mining is the **primary research bet**, gated on this pre-test.

### 10.5 Measure before build — the governing principle and the new disposition (supersedes §8)

The meta-finding, unanimous: "sound escape, novelty unmeasured" is **self-deception** if we build
first — the two prior failures *and* this would-be-third all share the structure "widen X, hope
novelty follows." So the disposition is **no builds yet** (which also honors the operator's "before we
take any further steps"); instead, pre-register and run cheap, decisive measurements, cheapest first:

1. **M1 — Proof-Compression Δ (abstraction-mining viability).** §10.4. Cheapest; existing data; no
   trust touch. Decides whether the leading candidate is even alive. **Run this first.**
2. **M2 — Oracle-formalization reachability replay (Stage B viability).** Hand-compile ~20 genuinely
   *novel, non-textbook* target theorems into the formal language and test three gates: **(i)
   expressibility** (can the DSL even state them? if not, *language* is the bottleneck, not
   faithfulness), **(ii) generator reach** (can the proposer realistically emit them?), **(iii) bridge
   synthesis** (given the exact statement, can the solvers close the Stage-B proof?). If the system
   cannot recover known-novel "gold" when *spoon-fed* the target, escaping the box yields novelty ≈ 0
   → don't build the renderer.
3. **M3 — Faithfulness mutation-detection ≥ 80%** for any faithfulness change: inject subtle semantic
   faults (quantifier inversion `Δ∀`, dropped hypothesis `ΔH`, vacuous antecedent, `=` vs `≡`); a
   gate that misses them is spec-gaming, not faithfulness.
4. **M4 — Novelty-precision@K + conversion-rate vs baselines** for the Observatory tier; the blind
   human read (ADR 0034 §5) remains the sole novelty referee (an LLM judge violates invariant #4).

**Pre-registered kill (Kimi), adopted:** if, after M1/M2 green, a bounded Stage-B-plus-extended-grammar
run (target ~1000 CPU-hr) yields **< 1 blind-novel theorem**, scrap the proof-carrying-for-novelty
thesis and pivot to abstraction mining and/or an explicit human-in-the-loop formal-sketch tool.

**Revised build order (supersedes §8's):** M1 → M2 → (only the lever that survives) → M3-guarded build
→ blind read / M4 → Kimi kill-gate. Stage A (poly-identity) is **not** built; certifying fragments
(§10.1) only if M1/M2 point at them. The Observatory ships only with an out-of-sample standard (§10.3).
Nothing in §10 touches the proved path or `tests/test_invariants.py`; M1 and M2 are pure measurement.

*The round-2 verdict in one line: the synthesis was cleaner than the premise but still conservative —
"polishing the bars of the cage." The honest response is not to build the cleaner cage faster, but to
measure, cheapest-first, whether any of these levers reaches novelty at all — and to take seriously
that the untouched lever is representation, not trust. Calculemus — and this time, measure first.*

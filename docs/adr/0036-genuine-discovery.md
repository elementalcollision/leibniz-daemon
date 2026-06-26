# ADR 0036 — Genuine discovery under a hard trust boundary

**Status:** Proposed (design only — no code, awaiting operator approval). Synthesis of an in-harness
5-design panel + adversarial pass + an **independent 5-model external review** (Fugu, DeepSeek V4 Pro,
Kimi, GLM 5.2, Gemini 3.5 Thinking — `docs/external-review-novelty-frontier.md`).
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

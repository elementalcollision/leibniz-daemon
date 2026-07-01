<!--
Synthesis of the external panel on the discovery-frontier brief (docs/external-brief-discovery-frontier-
2026-06-30.md). Advisory (invariant 4: no LLM decides). Cross-checked against Leibniz's own measured
findings. Decision-informing for the program's next major direction.
-->

# External round synthesis — the discovery frontier (2026-06-30)

**Panel:** 7 solicited. **5 substantive** (Fugu, Deepseek v4 Pro, Kimi, GLM 5.2, Qwen 3.7 Max); **Fugu Ultra
returned empty**; **Gemini 3.5 largely off-topic** (RFP/procurement rubrics, court rulings, mass-spectrometry
analogies) — only its bet-table and two probe protocols are usable and they echo the others. Advisory only.

## Headline (strong convergence)
1. **Positive-witness table-beating is dead — confirmed, not disputed.** Every substantive reviewer agrees
   the structural finding holds *for constructing optimal objects / lower bounds on public tables*. Kimi
   calls it an "ecological law" (human attention ⊇ bounded mechanical decidability); GLM/Deepseek/Qwen
   agree for the lower-bound/positive-witness band specifically.
2. **The escape is a POLARITY FLIP + a CERTIFICATE architecture** — stop *constructing* optimal objects;
   instead *verify small certificates* produced by untrusted SOTA solvers for statements in the band humans
   don't dominate. Three convergent routes:
   - **Negative certificates / UPPER bounds** — GLM's **Delsarte LP dual polynomial** (untrusted SDP finds a
     dual; kernel checks it with exact rational arithmetic) is the sharpest single new idea; plus SAT-UNSAT /
     non-existence for Ramsey/packing optimality (Deepseek, Kimi, Fugu). Attacks a *continuous* / *search*
     band where SOTA solvers beat human intuition.
   - **Falsification** — Kimi's conjecture-refutation (flip "construct the best" → "find any counterexample";
     witness trivial, `decide` on one ground term). Carries a fatal risk (see §"critical risk").
   - **Certificate checker to replace `by decide`** — DRAT/LRAT→Lean (Deepseek, Qwen, GLM, Fugu). Escapes the
     decide wall by checking a linear-size certificate instead of enumerating.
3. **Full-text witness reconstruction is AMPLIFICATION, not discovery** — unanimous (Fugu, Deepseek, Kimi,
   GLM, Qwen). Real product value, cheapest $0 first win, but it re-verifies *known* results. Several rank it
   #1 *as the first thing to run* precisely because it's cheap and de-risks the ingestion pipeline — while
   explicitly flagging it is not "genuine discovery."
4. **Z3/Walnut lemma/identity generation is DEAD by the oracle wall** — unanimous. No mechanical novelty
   oracle for free-form identities → degenerates to an LLM judge → violates invariant 4. Kill unless novelty
   is redefined as "corpus-not-found" (which is *evidence*, not novelty — Fugu).
5. **A new cheap-witness domain: do not fund** (Kimi, Deepseek explicit; all low). No counterexample to the
   hypothesis was named.

## Per-direction verdict (with panel weight)
| direction | verdict | who |
|---|---|---|
| **Certificate arch — UPPER bounds / negative certificates** (Delsarte LP; SAT-UNSAT) | **PURSUE (top)** | GLM(1), Deepseek(1), Kimi(B), Fugu(1) |
| **Full-text witness reconstruction** (amplification / cheapest first win) | **PURSUE as product + de-risk probe** | Qwen(1), Deepseek(2), Kimi(C), GLM(4), Fugu(2), Gemini |
| **Conjecture falsification** (polarity flip) | **CONDITIONAL — gated on H→S** | Kimi(A); others cautious |
| **Correction/refutation of public records** (new category the panel added) | **worth considering, needs governance** | Fugu(3) |
| **Z3/Walnut identities** | **DEAD (oracle wall)** | all |
| **New cheap-witness domain** | **DEAD / don't fund** | all |

## Framing corrections to incorporate (the panel's critique of our brief)
- **"Structural law" → "structural hypothesis," scoped.** It holds for *positive-witness table-beating*, not
  universally. The panel named bands it does NOT cover: upper-bound certificates, non-existence, falsification,
  SAT-certified finite combinatorics. (Fugu, Kimi, GLM, Qwen.) Adopt Fugu's safe wording: *"in the surveyed
  public-table finite-witness (positive/lower-bound) domains, the intersection of cheap kernel checking,
  clean oracle, and reachable open headroom was empty."*
- **Novelty taxonomy** (Fugu): separate `TABLE_RECORD_NOVEL` (the only mechanically-decided novelty) from
  `CORPUS_NOT_FOUND` (evidence), `KNOWN_REPRODUCTION`, `HUMAN_NOVELTY_PENDING`. Our invariant 4 only covers
  `TABLE_RECORD_NOVEL`; retrieval-only "not found" must never be promulgated as novelty.
- **Oracle wording** (Fugu): a table oracle is *deterministic + version-pinned*, deciding *record-relative
  improvement as of snapshot hash H* — not "sound" in the kernel sense and not truth. (We already hash-pin;
  adopt the wording.)
- **Q.E.D. vs decided-by-backend are TCB tiers** (Fugu): only kernel = `Q.E.D.`; Z3/Walnut/oracle are scoped
  non-Q.E.D. statuses unless rechecked by the kernel. (Consistent with our existing tiering; state it.)

## The decide wall is PART artifact — our own data confirms Qwen
Qwen's strongest claim: our "decide wall" is a **"Naive Formalization Wall,"** not fundamental — the
predicates are poly-time; Lean's `by decide` chokes on naive inductive-list reduction. **Our Tier-2 GATE-2
finding independently confirms the artifact half:** the covering t≥3 "wall" was Lean's default `maxRecDepth`
(512), fixed by raising it — after which `decide` verified to C(v,t)≈1,140. BUT GATE-2 *also* showed a
genuine reduction-cost (heartbeat) wall beyond that. So the honest reading: **the wall is part naive-
formalization (fixable) and part real reduction cost (needs an `Array`/bit-vector checker, `native_decide`
with TCB expansion, or an external verified certificate checker).** This forces a decision the panel raises
repeatedly:
- **TCB tradeoff (Qwen, Fugu, must resolve before any scaling build):** `by decide` (pure kernel, doesn't
  scale) vs optimized pure-Lean `Array`/`decide` (kernel-tier, real work) vs `native_decide` (expands TCB to
  the compiler) vs an **external verified LRAT/DRAT checker** (the cleanest — untrusted solver, small
  kernel-checked certificate). The certificate route keeps the TCB tight *and* scales, which is why it is the
  convergent top pick.

## The critical risk to carry (Kimi, fatal; Fugu concurs) — H→S is now error-of-COMMISSION
For *positive constructions*, a mistranslated statement merely fails to verify (safe — incompleteness). For
**falsification and any retrieval-novelty direction**, a mistranslated statement means we promulgate a
**false claim about the literature** ("conjecture C refuted" when we refuted a strawman) — an error of
*commission*, which is worse and directly threatens the ledger's soundness identity. Implication: any
falsification / novelty-by-retrieval direction requires a **human lock on the formalized statement before
the search runs** (autonomy stops at candidate-formalization), or it is also dead. This extends ADR 0002
(faithfulness) from "is the formal statement faithful to the candidate" to "is it faithful to the *published
human claim*" — a genuinely new gate for those directions. The certificate/upper-bound route is *safer*
here: proving `C(v,k,t) ≤ B` via a checked dual certificate makes a self-contained mathematical claim, not a
claim *about a paper*.

## Recommended path (measure-before-build, ranked)
The convergent, soundness-respecting answer to Q1: **genuine discovery is conditionally reachable via a
negative-witness / certificate architecture — not via positive construction.** Sequenced $0/cheap probes,
each with a hard exit criterion, before any heavy build:

- **P1 — Delsarte LP dual-certificate reproduction (top pick).** Free-CPU; ortools/CSDP already available;
  the certificate is a *small rational polynomial* (sidesteps the terabyte-DRAT problem Kimi/GLM flag for
  Ramsey). Reproduce a **known** CWC/code upper bound: formulate the Delsarte LP for a cell with a table
  LB<UB gap, solve (float), round to exact rationals, and have the **kernel check** the rational dual
  satisfies the Delsarte constraints (`ring`/exact arith). **GREEN:** kernel verifies a rational dual whose
  bound matches (reproduction) or tightens (beat) a table UB for ≥1 cell. **RED:** float→rational rounding
  can't satisfy strict positivity. Cost ≈ $0. *This is the make-or-break for the whole negative-certificate
  pivot and it's the cheapest to run with what we have.*
- **P2 — witness-reconstruction de-risk probe (parallel; product, not discovery).** ~10–15 papers with
  explicit cyclic/difference constructions → LLM writes an orbit-expansion script → kernel-check the witness.
  **GREEN:** ≥3–5 reproduce the paper's stated bound. Needs full-text acquisition + LLM (operator/billable).
  Honest framing: amplification, not discovery.
- **P3 — LRAT→Lean certificate reproduction (gated, heavier).** Reproduce a *known* SAT-UNSAT bound
  (small Ramsey/packing non-existence) through an external verified LRAT checker → Lean. **GREEN:**
  certificate < ~1 GB and kernel/checker verifies < ~10 min. Establishes the general certificate infra if P1
  proves the pattern. (Deepseek/Qwen/GLM all rank the *reproduce-first* probe here.)
- **DEFER:** conjecture falsification (only behind a human-lock on formalization — H→S commission risk);
  Z3/Walnut identities (oracle wall); new-domain scouting (no counterexample named).

## Disposition
- **Incorporate** the framing corrections (structural *hypothesis*; novelty taxonomy; oracle wording; the
  part-artifact decide-wall reading) into the roadmap/scout doc.
- **Direction:** the negative-witness / certificate architecture is the panel's convergent escape and aligns
  with our already-gated certificate item (Gate B2 / ADR 0045 §10 / kernel-bridge #54). It targets a band the
  7-family scout did **not** test (upper bounds / non-existence).
- **Operator decision required:** (a) which probe to fund first — **P1 Delsarte (free, recommended)** vs P2
  reconstruction (product, billable) vs P3 LRAT (heavier); (b) the **TCB policy** (external verified checker
  — recommended — vs `native_decide` vs `Array` pure-Lean); (c) confirm falsification stays **deferred**
  behind a human-lock. No promulgating build starts before a GREEN probe.

Raw responses: `Discovery Frontier for Leibniz.md` (operator's Downloads). Brief:
`docs/external-brief-discovery-frontier-2026-06-30.md`.

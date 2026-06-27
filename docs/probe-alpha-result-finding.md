<!--
Probe α (zero-LLM enumeration audit) result + adversarial verification (run wyfd15i8b).
Corrects the interim "structurally falsifies the slogan" overreach. Provenance:
docs/results/probe_alpha_result.json. No trust-boundary change.
-->

# Probe α result — the producer-bias confound is real, but the *interesting* slogan survives

**Status:** measured + adversarially verified, 2026-06-26. **Verdict: PENDING-GREEN on the LLM-bias
question (settled in α's favor); effectively-RED on the textbook question (the survivors are catalogued /
published prior art).** The zero-LLM enumeration audit removed the LLM from the producer and asked whether
the *decided* region of an enumerable Walnut-decidable space contains sound, non-catalogued theorems. It
does **not** — the survivors are in OEIS and, for a whole sub-family, in the field's textbook.

## What ran (clean, and the decider is sound)
144 Walnut evals over 48 un-named uniform morphisms (power-freeness e∈{2,3,4}): **61 decided-TRUE, 83
decided-FALSE, 0 indeterminate.** Independent brute-force cross-check: **61/61 decided-TRUE prefix-clean
(0 contradictions); 83/83 decided-FALSE carry a real prefix counterexample.** External bonus: 12/12 of the
k=3 survivors' decided exponents are **consistent with Khodier's 2026 Waterloo thesis Table 5.1** published
critical exponents — an independent confirmation that Walnut is computing correctly.

## The correction — two slogans, only one was ever interesting
My interim report said this "structurally falsifies our slogan." That **overreached** by conflating two
claims; the adversarial pass (literature/OEIS lens + invariant-4 lens) separates them:

- **"if the LLM doesn't name it, it's unreachable" → FALSIFIED.** 36 sound, faithful (the morphism *is*
  the definition — ~0 English gap), aperiodic, decided-TRUE power-freeness theorems exist that the LLM
  conjecturer never proposed. The LLM-catalogue-bias confound is genuinely removed. Good to know — but this
  was never the binding claim.
- **"soundly-checkable ∧ finitely-encodable ⇒ textbook/known-to-humans" → NOT falsified; corroborated.**
  The literature lens is decisive: **8/8 sampled survivor fixed-points are catalogued OEIS sequences (0
  genuinely un-catalogued).** The entire k=3 half (12/36) is fully prior art — OEIS A189628's comment block
  enumerates the binary 3-uniform morphism→A-number family, and Khodier 2026 Table 5.1 *is* this exact
  experiment. **A064990 (Mephisto Waltz) is stated 4th-power-free in Allouche–Shallit's textbook, p.25.**
  The probe's `named_match=null` was a **false negative of its own detector** (it only knew Thue-Morse +
  period-doubling), not evidence of novelty.

**Invariant-4 discipline:** the pre-registered GREEN has four conjuncts — non-named, aperiodic,
literature/OEIS check, **human blind panel**. Only (i)+(ii) were structural; the literature check (iii) was
just run and came back **against** novelty; the human panel (iv) is the owner of the verdict. An agent may
not stamp "slogan falsified" — that is exactly the call invariant 4 reserves for humans. The honest status
is **conditional**, and the catalogue evidence points RED.

## Shallow — strongly, and by construction
Every survivor's minimum decided exponent is 3 or 4 (none squarefree or overlap-free). The design only
decided integer e∈{2,3,4}, so it **structurally cannot** surface a critical-exponent surprise (e.g. a
Dejean-threshold result) — it forecloses exactly the noteworthy class. 36/48 ≈ 75% survival makes
power-freeness *generic* over the tiny aperiodic space. The only non-generic subset (6 binary cube-free
morphisms) is the most classical object in the field (Thue 1906) and symmetry-collapses to ~3 facts. The
one honest sliver: the k=2 ternary fixed points (A096271/A101614/A101664/A101671) are catalogued *as
sequences* but their specific power-free *theorem* is sometimes unstated in OEIS (~2–3 distinct after
symmetry) — marginal, exercise-class.

## What it means (the fourth converging probe)
This is the **fourth** probe to converge — genre A/B (0 novel), Walnut run-3 (all textbook), SOS
(novelty RED), and now the zero-LLM enumeration audit. The new one is the strongest because it **removed
the LLM confound and still produced catalogued/textbook results.** So the binding constraint is *not* the
LLM proposer per se, and *not* finite-encodability — it is that **the soundly-decidable, cheaply-enumerable
region of a studied theory is, by its nature, the region humans have already catalogued.** Autonomous
discovery by "enumerate + decide the cheap questions" is effectively concluded as a measured negative.

## Disposition
- **Lever, if any:** search over **externally-meaningful** objects (Probe β — finite-witness record
  factory; novelty = an *objective public-table improvement*), as a **side-track** under verification
  amplification, never the main line. **Critical lesson α teaches β:** the literature/table-of-record
  oracle must be a **first-class automated stage** — the name-detector false-negatived 8/8; "improves the
  table" is only credible against a real automated lookup, never LLM-judged.
- **Strategic home:** verification amplification (the witnesses' unanimous #1).
- **Human panel:** forward at most the de-duplicated k=2 ternary theorem-level sliver (~2–3), and only
  after an automated OEIS filter is committed; do **not** spend panel budget on the 12 published k=3 or the
  6 textbook binary cube-free survivors.
- **Kernel bridge** (task #54) stays gated — unchanged.

Trust boundary intact throughout; no LLM decided anything; `tests/test_invariants.py` byte-identical.

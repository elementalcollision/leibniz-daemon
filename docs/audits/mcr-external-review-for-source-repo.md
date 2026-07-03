# Independent formal-verification review of the MCR whitepaper

*An external, machine-checked review of "MCR: A Universal Transition Equation for Multi-Level Information
Processing" (Kheltz, July 2026). Offered constructively: every finding below is backed by a re-runnable
artifact — a Z3 (SMT solver) query, a Lean 4 kernel-checked proof, or an exact numeric computation — so any
claim here can be verified or refuted independently. Where the paper is correct, we say so; we also state and
prove the closest **true** theorem to the paper's main claim, so there is something solid to build from.*

**Method.** Eight formalizable sub-claims were each assigned a verdict and an artifact, then each verdict was
independently re-checked by a second adversarial pass that tried to overturn it. Tooling: Z3 4.16.0 and
Lean 4.31 + Mathlib. A single self-contained script reproduces the SMT/numeric artifacts; the one Lean proof
is a short standalone file. Verdicts use five tags: **PROVEN-AS-STATED**, **REFUTED**, **VACUOUS-OR-TRIVIAL**,
**ILL-POSED**, **TRUE-BUT-WEAKER** (plus **NOT-PROVEN** where an inference simply fails to establish its
conclusion without that conclusion being *false*).

## Summary of findings

| Claim reviewed | Verdict |
|---|---|
| Theorem 1 (Level Invariance) carries capability content | **VACUOUS-OR-TRIVIAL** |
| Corollary 1 (Universality) is a valid inference | **REFUTED** |
| MCR is universally learnable | **REFUTED** — explicit counterexample proved |
| Theorem 3 (Q-learning embedding) is well-typed vs Definitions 1–2 | **REFUTED** |
| Theorem 2 bound `E ∈ [0, log₂N]` | **ILL-POSED** (with a false sub-step) |
| Theorem 4 (sample bound) and its `O(N ln N)` corollary | **TRUE-BUT-WEAKER** |
| §13 conclusion ("path to AGI via level discovery") follows | **NOT-PROVEN** |
| The true, weaker statement near Corollary 1 | **PROVEN** (and it is exponentially costly) |

**Overall.** The learning mechanism (Definitions 1–3) is a first-order (bigram) Markov frequency counter with
arg-max lookup — a correct and classical estimator (Markov, 1906). None of the formal apparatus establishes
the universality/AGI thesis of §13. The single true "universality-adjacent" statement (below) is real but
*conditional* and its cost is **exponential in context length** — a caveat the paper's own Theorem 4 already
contains but §13 does not connect. We recommend the paper either (a) restrict its claims to the true weaker
statement we prove, or (b) supply the missing definitions/premises named in each finding.

---

## Finding 1 — Theorem 1 is the "free theorem" for its type; it holds of a do-nothing stub. **VACUOUS-OR-TRIVIAL**

Theorem 1 says the learn/predict algorithms are identical across levels and only the tokenization τ_n differs.
Because `learn` and `predict` are generic in the state type and use only equality on states, this is precisely
the **parametricity free theorem** (Reynolds 1983; Wadler, "Theorems for free!", 1989): relabelling the tokens
and then running is identical to running and then relabelling (a naturality square). That square is *exactly*
the paper's "the same operator T acts on the image of τ_n."

The problem: this holds of *any* well-typed generic implementation, **including a stub that learns and predicts
nothing** — so Theorem 1 conveys no information about MCR's actual capability, which is what Corollary 1 and
§13 rely on.

*Artifact.* The naturality square commutes for the real counter **and** for a no-op stub (both `True`); Z3
proves it is **UNSAT** that any parametric `predict` could break it, and confirms a *non*-generic `predict`
(one that inspects a specific token) *does* break it (so the property is the parametricity boundary, not
vacuously true of everything); exhaustive check over a 2-symbol alphabet: all 65,536 generic predictors pass,
zero exceptions.

## Finding 2 — Corollary 1 equivocates on "learn." **REFUTED**

Corollary 1's argument is: (P1) every task is representable as transitions in some state space; (P2) MCR can
"learn transitions" in any state space; (C) MCR is a universal information processor. The word *learn* is used
in two senses. What Theorem 1 justifies is only that the counting code **runs** over any tokenized state space
(genericity). What C needs is that it **converges to low error** (learnability). These are different predicates.

*Artifact.* Encoding P1, the honest P2 (`Representable → Runnable`), and C (`Universal → ε-Learnable`): Z3 finds
`P1 ∧ P2 ∧ ¬C` **satisfiable** — a model where the premises hold and the conclusion fails, so the syllogism is
**invalid**. Only replacing P2 with the stronger, unjustified `Representable → ε-Learnable` makes it valid
(Z3: UNSAT). This is a textbook four-term equivocation.

## Finding 3 — An explicit task MCR provably cannot learn at any sample size. **REFUTED** *(counterexample proved)*

This is the sharpest finding. Alphabet Σ = {a, b, c}. Partition the stream into long blocks; each block
independently follows pattern `a,b,a,b,…` with probability q ∈ (0,1), else `a,c,a,c,…`. Run order-1 MCR over the
raw symbol (the natural state space the paper's own examples use). From state `a`, the correct next symbol is
determined by the hidden block-mode — information **not present** in the order-1 state `a`.

- The stationary counts give `T(a,·) ∝ (q, 1−q)`, so `arg max_b P(b|a)` is a **fixed** symbol (`b` if q > ½,
  else `c`) forever, regardless of how much data is seen.
- **From state `a`**, the model's prediction error therefore has a **lower bound `min(q, 1−q) > 0` for every
  q ∈ (0,1)** — an error floor at that ambiguous state that does **not** shrink with data. (Averaged over the
  whole stream, where `a` recurs on about half the steps, the unconditional per-symbol floor is about
  `½·min(q, 1−q)` — still bounded away from 0.)

*Artifact.* Exact stationary computation gives the floor `min(q,1−q)`; Z3 proves the negation ("floor ≤ 0 on
the realizable domain") is **UNSAT**. Importantly this does **not** contradict Theorem 4: Theorem 4 bounds the
*estimation* error around the true order-1 conditional, and says nothing about the gap between that conditional
and the *task-correct* answer when the process is not order-1 Markov over the chosen state space. This is the
classical, well-documented failure of bigram models, and it is a direct counterexample to Corollary 1 read as
the unconditional universal learnability §13 needs.

## Finding 4 — Theorem 3 (Q-learning) uses an operation Definitions 1–2 do not provide. **REFUTED**

Definition 2's update *increments a natural-number counter* (`T(a,b) += 1`) — a strictly-increasing,
ℕ-valued operation whose written value is determined by the current contents. Theorem 3 / Definition 14 instead
*assigns an arbitrary real* Q-value (which can decrease, be negative, or be fractional) into that structure — a
constant-in-the-pre-state, ℝ-valued *overwrite*. These are incompatible operation shapes on different codomains.

*Artifact (Lean 4, kernel-checked, 0 `sorry`).* On any linearly ordered value type, a single update map that is
both strictly-increasing (count shape) and constant (assign shape) forces the type to be a subsingleton;
specialized to the integers it forces `0 = 1` (closed by `decide`). Hence value-assign is **not** a
type-preserving specialization of count-update. Consequence: Theorem 3 is not derivable from Definitions 1–4 as
written; adding the needed overwrite primitive introduces a *second* per-level variation (the update rule
itself), which undercuts Theorem 1's premise that only τ_n varies.

## Finding 5 — Theorem 2's bound `E ∈ [0, log₂N]` is false as written. **ILL-POSED** (with a false sub-step)

Definition 11 sets `E = −log₂ p(w)`, unbounded above as `p(w) → 0`. The proof of Theorem 2 asserts
`E ∈ [0, log₂N]` and "normalized to [0,1]" without defining any normalization map, and the bound uses the wrong
logarithm (`E` is bounded by `log₂(corpus size)`, not by `log₂N` = vocabulary size).

*Artifact.* A hapax (frequency 1) in a 10⁶-token corpus with vocabulary N = 100 gives
`E = −log₂(10⁻⁶) ≈ 19.93` bits against `log₂(100) ≈ 6.64` — a **13.29-bit** violation (exact arithmetic + Z3).
No renormalization map for `E` or `P` appears anywhere in the document. The quoted step `E ∈ [0, log₂N]` is, in
isolation, a **false** proposition; the surrounding theorem is **ILL-POSED** because "normalized" is undefined.
*(A rescue exists as a **TRUE-BUT-WEAKER** result: with an explicit `E' = clip(E / log₂ N_max, 0, 1)` for a
stated `N_max`, `B ∈ [0,1]` does hold — but that is a different theorem than the one written.)*

## Finding 6 — Theorem 4's per-pair bound is correct; its corollary silently needs a union bound. **TRUE-BUT-WEAKER**

The per-pair bound is right: reduce to a Bernoulli indicator `Z_i = 1[a→b]` and apply two-sided Hoeffding —
the constant `ln(2/δ)` matches the absolute-value error (one-sided would be `ln(1/δ)`; Z3 confirms they are
distinct). But the Corollary's "reliable estimation for **each state**" is a guarantee *simultaneously* over all
N outcomes, which requires a **union bound** (`δ → δ/N`, i.e. `ln(2/δ) → ln(2N/δ)`) that is **absent** from the
derivation.

*Artifact.* Z3 confirms the two-sided constant and the identity `ln(2N/δ) = ln(2/δ) + ln N = Θ(ln N)`. Good
news for the author: because the extra `ln N` is absorbed, the corrected per-state requirement is still
`O(ln N)` and the advertised **`O(N ln N)` total sample complexity survives** — the derivation just needs the
union-bound step made explicit.

## Finding 7 — The chain from Theorem 1 to the §13 AGI conclusion does not go through. **NOT-PROVEN**

Classifying each inference: Theorem 1 → Corollary 1 is valid only under two *unstated* premises ("every task
reduces to transition-counting" and "MCR genuinely learns each such task" — the latter is exactly what
Finding 3 refutes). Corollary 1 → §13 is a **non-sequitur**: it needs the unstated premise "syntactic
reusability of a learning mechanism across domains ⇒ competent performance in them," which is independently
false (a reused counter scores no better than chance on a task requiring context, per Finding 3). The verdict is
**NOT-PROVEN** — the argument fails to establish the AGI conclusion; we are *not* claiming AGI-via-level-
discovery is itself false, only that this paper does not support it.

## Finding 8 — The true theorem in the neighborhood (and why it is exponentially costly). **PROVEN**

There is a correct statement underneath the universality claim, and we prove it. For any stationary **k-th
order** Markov process over Σ, define the augmented state `S = Σ^k` (length-k context windows). Then the process
is *exactly* first-order Markov over `S`, and Definitions 1–3 applied to `S` (not the raw alphabet) **converge**
to the true conditional distribution as sample size → ∞ (standard visit-count law of large numbers).

*Artifact.* Kernel-checked in Lean (0 `sorry`) at the structural level; simulation confirms the `n^{−1/2}`
convergence rate and Theorem-4 compliance. **The catch, quantified by the paper's own Theorem 4:** `|S| =
|Σ|^k`, so the `O(N ln N)` sample complexity becomes **exponential in k** (e.g. `4^k` in a worked case). This is
the true, materially weaker claim — "universality *conditional on sufficient state augmentation*, at cost
exponential in context depth" — and it is exactly the caveat the paper's §12 states ("first-order... cannot
capture long-range dependencies") but §13 does not connect to §11's sample-complexity result.

---

## Recommendation

The mechanism is a correct classical estimator, and the sample-complexity theorem (Theorem 4) is sound. We
suggest: (1) drop or explicitly caveat the universality/AGI framing of §13; (2) adopt the true weaker statement
of Finding 8 as the honest "universality" result, and connect it to Theorem 4 to surface the exponential cost;
(3) supply the missing pieces named in Findings 4–6 (a value-assign primitive for Theorem 3, a normalization map
for Theorem 2, an explicit union bound for Theorem 4's corollary). The paper's own formal apparatus already
contains the corrective (Theorem 4 + §12); connecting it would turn an overclaim into a correct, interesting,
and defensible result.

## Reproducibility

- SMT/numeric artifacts (Findings 1, 2, 3, 5, 6): a single self-contained Python script requiring only `z3` —
  runs all checks and prints GREEN.
- Lean proof (Finding 4): a ~40-line standalone Lean 4 + Mathlib file; kernel-checks with 0 errors and
  0 `sorry`.
- Every SAT/UNSAT verdict and numeric constant above is reproduced by those two files. They accompany this
  review.

*This review adjudicates only the formalizable mathematical/logical claims. Empirical questions (e.g. whether
the repository's validation report contains task-performance evidence) are outside its scope and are not
addressed here.*

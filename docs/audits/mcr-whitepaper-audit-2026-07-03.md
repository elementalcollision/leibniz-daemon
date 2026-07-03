<!--
Leibniz formal-verification audit of the MCR whitepaper (Kheltz, July 2026), in response to Chimera's audit
package (github.com/elementalcollision/chimera commit 196838e). Deliverable in the requested Part-4 format.
Verdicts backed by machine-checked artifacts (z3 4.16.0 SAT/UNSAT, Lean 4.31 kernel, exact numeric witnesses).
Reproducible core: docs/audits/mcr_audit_artifacts.py (runs GREEN) + docs/audits/mcr_p4_not_derivable.lean
(Lean kernel: 0 errors, 0 sorries). Method: each verdict was produced by a solver agent and then
adversarially verified by an independent skeptic (re-running artifacts, seeking a more charitable reading).
-->

# Leibniz audit — "MCR: A Universal Transition Equation" (Kheltz, 2026)

**Bottom line:** **nothing in P1–P8 survives as genuine support for the §13 AGI conclusion.** The mechanism is
a first-order (bigram) Markov frequency counter with arg-max lookup. Its "universality" theorem is either a
type-level tautology (P1) or an equivocation (P2/P7); it has a hard, sample-size-independent failure mode
(P3); two of its supporting theorems are broken as stated (P4, P5); one is fixable with a caveat the paper
omits (P6). The **one** true statement in the neighborhood (P8) is materially *weaker* — universality is
conditional on state augmentation, at a cost the paper's own Theorem 4 makes **exponential in context length**.

| # | Claim under audit | Verdict | Artifact |
|---|---|---|---|
| P1 | Thm 1 (Level Invariance) carries capability content | **VACUOUS-OR-TRIVIAL** | parametricity witness + z3 (exhaustive) |
| P2 | Cor 1 (Universality) syllogism is valid | **REFUTED** | z3 SAT countermodel |
| P3 | MCR universally learnable (flagship counterexample) | **REFUTED** *(countermodel PROVEN)* | probability proof + z3 UNSAT |
| P4 | Thm 3 (Q-learning embedding) is well-typed vs Defs 1–2 | **REFUTED** | Lean kernel (0 sorries) |
| P5 | Thm 2 (Bridge normalization) `E ∈ [0, log₂N]` | **ILL-POSED** | exact arithmetic + z3 |
| P6 | Thm 4 (Sample bound) + its `O(N ln N)` corollary | **TRUE-BUT-WEAKER** | z3 (Hoeffding constants) |
| P7 | Thm 1 → Cor 1 → §13 reaches the AGI conclusion | **NOT-PROVEN** (unsupported, not false) | z3 per-edge + witness |
| P8 | The true, weaker statement (steelman) | **PROVEN-AS-STATED** | Lean kernel + sim |

---

## P1 — VACUOUS-OR-TRIVIAL

**Artifact.** `learn`/`predict` are generic in the state type `S` with only `DecidableEq S`; their
Reynolds/Wadler free theorem, specialized to `R = graph(τ)` for a tokenization `τ`, is exactly the naturality
square `predict(relabel(t), τ a) = τ(predict(t, a))` and likewise for `learn` — which is *verbatim* MCR's "the
same operator T acts on the image of τ_n, invariant to level choice." Verified four ways
(`mcr_audit_artifacts.py::p1_parametricity_witness` + the workflow's z3 scripts): the square commutes for the
**real** counter **and** for a **no-op stub** that learns/predicts nothing (real=True, stub=True); z3 proves
**UNSAT** that any parametric `predict` could break it; z3 certifies a *non*-parametric `predict` (peeking at a
token) *does* break it (so the property is the parametricity boundary, not vacuously true of everything); and
an exhaustive check of all 65,536 generic `predict`s over a two-token alphabet passes with zero exceptions.

**Plain language.** Theorem 1 is a fact about MCR's *type signature*, not its behavior: because the code is
generic in the token type and can only compare tokens for equality, relabelling-then-running equals
running-then-relabelling — a property an empty stub shares. It therefore transmits **zero** capability content
to Corollary 1 or the §13 AGI claim, which need MCR to actually *learn*, not merely to be well-typed.

## P2 — REFUTED

**Artifact.** Formalize `P1 = Representable`, `P2_honest = (Representable → Runnable)` (all Thm 1 justifies:
the code *runs* over any tokenized `S`), `C = (Universal → εLearnable)`. z3
(`mcr_audit_artifacts.py::p2_syllogism_invalid`): `P1 ∧ P2_honest ∧ ¬C` is **SAT** (the entailment is invalid);
`P1 ∧ (Representable → εLearnable) ∧ ¬C` is **UNSAT** (only the *equivocated* P2 rescues it). Numeric witness:
on a task that is trivially Representable, MCR's asymptotic task error is 0.5010 — **not** ε-Learnable at
ε=0.05.

**Plain language.** Corollary 1 equivocates on the word "learn": the premise the paper *proves* only says the
counting code will *run* over any state space (genericity), while the conclusion needs it to *converge to low
error* (learnability) — two different predicates. z3 exhibits a world where the honest premises hold and the
conclusion fails, so the syllogism is deductively invalid. Named fallacy: equivocation (a four-term syllogism).

## P3 — REFUTED *(the flagship countermodel, PROVEN as stated)*

**Artifact.** Construction: `Σ={a,b,c}`; blocks of length L are Mode-X (`a,b,a,b,…`) w.p. `q∈(0,1)` else Mode-Y
(`a,c,a,c,…`). Order-1 MCR over the raw symbol sees only state `a` and cannot tell the mode. Exact stationary
analysis (`mcr_audit_artifacts.py::p3_error_floor`): `T(a,·) ∝ (q, 1−q)`, so `argmax_b P(b|a)` is a **fixed**
symbol (`b` if `q>½`, else `c`) for all sample sizes; the asymptotic per-symbol error on `a`-steps equals the
mass of the *other* mode, i.e. **`min(q, 1−q) > 0` for every `q∈(0,1)`** (tight for even L). z3: the negation of
"error floor > 0 on the realizable domain" is **UNSAT** (proven). Crucially, Theorem 4 does *not* contradict
this — it bounds *estimation* error around the true order-1 conditional, and says nothing about the gap between
that conditional and the *task-correct* answer when the process is not order-1 Markov over `S`.

**Plain language.** Here is an explicit task that is trivially "representable as transitions" yet on which MCR
provably cannot get low error at *any* sample size, for a structural reason (it conflates two contexts behind
the same state) rather than a data-scarcity reason. This is the textbook, decades-old failure mode of bigram
models, and it is a direct countermodel to Corollary 1 read as the unconditional universal learnability that
§13's AGI claim requires. The error floor `min(q,1−q)` is machine-verified, and Theorem 4's non-contradiction
is confirmed formally.

## P4 — REFUTED

**Artifact.** `docs/audits/mcr_p4_not_derivable.lean` (Lean 4.31 + Mathlib, **kernel: 0 errors, 0 sorries**,
re-verified in-session). `count-update` (Def 2) has per-cell shape *strictly increasing* (`∀x, x < u x`);
`value-assign` (Def 14) has per-cell shape *constant in the pre-state* (`∀x y, u x = u y`). Theorem
`not_derivable`: on any `LinearOrder` value type, a single `u` inhabiting both shapes forces the type to be a
subsingleton; `not_derivable_on_Int` specializes this to force `(0:ℤ)=1`, closed by `decide`. So no
type-preserving specialization turns count-update into value-assign.

**Plain language.** Definition 2 can only add 1 to a natural-number counter; the value it writes is determined
by the current contents. Definition 14 (Q-learning) must overwrite a cell with an arbitrary real — possibly
smaller, negative, or fractional — which is a fundamentally different operation shape on a different codomain
(ℝ, not ℕ). Theorem 3 therefore is *not* derivable from Definitions 1–4 as given; patching it in requires a new
update primitive the source never states, which reintroduces exactly the per-level variation Theorem 1 claims
does not exist (defeating "invariance").

## P5 — ILL-POSED *(with a REFUTED sub-finding and a TRUE-BUT-WEAKER rescue)*

**Artifact.** `E = −log₂ p(w)` is bounded by `log₂(corpus size)`, **not** `log₂ N` (vocabulary). Exact check
(`mcr_audit_artifacts.py::p5_entropy_exceeds_logN`, and z3 SAT): a hapax (freq 1) in a 10⁶-token, `N=100`-vocab
corpus gives `E = 19.9316 > log₂(100) = 6.6439` — a **13.29-bit** violation of the quoted proof step
`E ∈ [0, log₂N]`. No renormalization map for `E` or `P` appears anywhere in the source; the Theorem-2 proof
asserts "normalized to [0,1]" as an undefined hypothesis.

**Plain language.** The proof of Theorem 2 bounds a quantity it never actually defines: the raw specificity
term `E` is unbounded above, and the claimed ceiling uses the wrong logarithm. The quoted step
"`E ∈ [0, log₂N]`" is, in isolation, a **false** proposition (REFUTED sub-finding); the wrapper theorem is
ILL-POSED because "normalized" has no defining map. A natural rescue — `E' = clip(E / log₂ N_max, 0, 1)` for a
stated `N_max` — *does* yield `B ∈ [0,1]` (TRUE-BUT-WEAKER), but that is a different, unstated theorem.

## P6 — TRUE-BUT-WEAKER

**Artifact.** z3 (workflow + `mcr_audit_artifacts.py::p6_hoeffding_constant`): reducing to a Bernoulli
indicator `Z_i = 1[a→b]` and applying two-sided Hoeffding gives the **correct** per-pair constant `ln(2/δ)`
(matching the absolute-value bound; one-sided would be `ln(1/δ)` — proven distinct). The Corollary's "each
state" guarantee needs a **union bound** over the `N` outcomes (`δ → δ/N`, so `ln(2/δ) → ln(2N/δ)`), which is
**absent** from the source. But `ln(2N/δ) = ln(2/δ) + ln N = Θ(ln N)` (z3-confirmed identity), so the corrected
per-state requirement is still `O(ln N)` and the total **`O(N ln N)` survives**.

**Plain language.** The per-pair Hoeffding bound is correct as stated (modulo the one-vs-two-sided constant,
which is right). The jump to a *uniform* "reliable for each state" guarantee silently requires a union bound the
paper never applies — a real gap — but once inserted, the extra `ln N` is absorbed and the advertised
`O(N ln N)` total sample complexity is unchanged. (Separately, the literal "expectation bound *with probability*
1−δ" phrasing is malformed as written, but the intended tail bound is standard.)

## P7 — NOT-PROVEN *(the AGI conclusion is unsupported, not false)*

The chain does **not** deductively reach the AGI conclusion; each edge classified as (a) valid, (b) valid only
under a named unstated premise, or (c) non-sequitur. z3: E1 is invalid stated-only (SAT), valid only after
adding H1/H2 → class (b); E2 is invalid under any charitable deductive reading and is refuted by a concrete
witness (an identical reused MCR counter scores 0.00 generalization on parity under both tokenizations,
realizing `SYN_REUSE=True ∧ COMPETENT=False`) → class (c).

```
[Thm 1: one counting op is generic across tokenizations τ_n]         (per P1: VACUOUS — type-level only)
        │  E1  ── class (b): valid ONLY with unstated
        │        H1 "every task reduces to transition-counting"
        │        H2 "MCR genuinely LEARNS (ε-converges) each such task"   ← H2 is exactly what P3 refutes
        ▼
[Cor 1: MCR is a "universal information processor"]                   (per P2: equivocates "learn")
        │  E2  ── class (c): NON-SEQUITUR. Needs the unstated
        │        SUFFICIENCY premise "syntactic reusability of a learning
        │        mechanism across domains ⇒ competent performance in them"
        │        — independently FALSE (witness: reuse ∧ ¬competent).
        ▼
[§13: "the path to AGI may be one of level discovery"]                UNSUPPORTED
```

**Plain language.** Every link from Theorem 1 to the AGI conclusion either needs a premise the paper never
states or is a non-sequitur. The load-bearing missing premise — that a learning mechanism being *syntactically
reusable* across domains makes it *competent* in them — is exactly the claim P3 gives an explicit
counterexample to. The verdict is NOT-PROVEN (the chain fails to establish the conclusion) rather than REFUTED
(we have not shown AGI-via-level-discovery is *false* — only that this argument does not support it).

## P8 — PROVEN-AS-STATED *(the steelman: the true claim is conditional and exponentially costly)*

**Artifact.** Lean 4.31 (workflow: kernel OK, 0 sorries) + simulation (`mcr_p8.py`). **Statement.** For any
stationary `k`-th order Markov process over `Σ`, the augmented state `S = Σ^k` (length-`k` windows) makes the
process *exactly* first-order Markov over `S`; Defs 1–3 applied to `S` (not raw `Σ`) converge to the true
conditional as sample→∞ (visit-count LLN). Simulation confirms `N^{−0.5}` convergence (fitted exponent −0.530,
theory −0.5) and Theorem-4 compliance. **Corollary (the sting):** `|S| = |Σ|^k`, so the paper's own `O(N ln N)`
sample complexity becomes **exponential in `k`** (`4^k` in the worked case), matching §12's own admission that
first-order "cannot capture long-range dependencies."

**Plain language.** The grand "one equation is universal" claim is false as stated, but a real theorem survives
underneath it: widen the state to a length-`k` context window and MCR *does* learn any `k`-th-order process
correctly. The catch — quantified by the paper's *own* Theorem 4 — is that the state space, and hence the data
required, grows exponentially in the context length `k`. This is the correct, materially weaker claim: MCR's
universality is conditional on augmentation the paper's §13 does not perform, and its cost is exactly what the
paper's §12 warns about but §13 ignores.

---

## Overall summary

**Does any result in P1–P8 survive as genuine support for the paper's §13 AGI conclusion? No.** Theorem 1 is a
type-level free theorem with no capability content (P1); Corollary 1's universality is an equivocation on
"learn" (P2), and the full argument to AGI is either premised on unstated assumptions or a non-sequitur (P7).
The mechanism has a proven, sample-size-independent error floor on a trivially-representable task (P3) — the
decisive countermodel. Two supporting theorems are broken as stated (Q-learning embedding is ill-typed, P4;
the bridge-normalization bound is false and its theorem ill-posed, P5); one is fixable but omits a required
union bound (P6, `O(N ln N)` survives). The **only** true statement in the vicinity (P8) is materially weaker
and *self-undermining* for the AGI thesis: universality holds only with context-window augmentation, whose cost
the paper's own Theorem 4 makes exponential in context length — precisely the caveat §13 needed and skipped.
The honest, restated claim MCR actually supports is: *"a first-order frequency estimator learns any process
that has been reduced to first order by sufficient state augmentation, at sample cost exponential in the
augmentation depth"* — a century-old fact (Markov 1906), not a path to AGI.

*(Chimera's separately-noted empirical/bibliographic observations — no task-performance evidence in the
validation report; the 950-vs-2109 line-count discrepancy — are outside Leibniz's formal remit and are not
adjudicated here.)*

**Artifacts.** `docs/audits/mcr_audit_artifacts.py` (P1/P2/P3/P5/P6, runs GREEN under z3 4.16.0);
`docs/audits/mcr_p4_not_derivable.lean` (P4, Lean 4.31 kernel: 0 errors, 0 sorries). Every verdict above was
adversarially re-verified by an independent skeptic; the P7 verdict was downgraded REFUTED→NOT-PROVEN in that
pass (the AGI claim is unsupported, not shown false) — recorded honestly.

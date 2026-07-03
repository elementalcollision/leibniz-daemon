<!--
Archived external witness review of the F2b formalization brief (docs/briefs/terwilliger-f2b-external-brief-
2026-07-02.md). Eight reviewers. Synthesis (with our critical examination + cross-checks against our code)
first, then the verbatim panel. The durable findings were folded into the brief in this same review-response.
Audit/measurement only; no trust surface touched.
-->

# External witness review — F2b formalization brief (2026-07-03)

Eight reviewers (**Fugu**, **Fugu Ultra**, **Deepseek v4 Pro**, **Kimi**, **GLM 5.2**, **Gemini 3.1 Pro Deep
Thinking**, **Qwen 3.7 Max**, **MiniMax M3**) critiqued the F2b brief (the ask to formalize Schrijver's
block-diagonalization, Theorem 1, so the three audit-tier certificates become kernel-attested). Below: a
synthesis with our critical examination (cross-checked against our own code and ADR 0046), then the verbatim.

## Synthesis — what survived examination (and what we changed)

**The #1 finding — the "admit first" framing is a trust-boundary hazard (Fugu, Fugu Ultra, Kimi, Qwen,
MiniMax).** The brief's "admit this as one named lemma first — it *shrinks* our informal trusted base" is
misleading: in Lean an admitted axiom/`sorry` *enlarges* the TCB, and any theorem depending on it is
kernel-checked *relative to the axiom*, **not** Q.E.D. **Examination: the reviewers are right, and the fix is
already our own policy** — ADR 0046 (F2c = Observatory) says bridge results stay audit-tier until *discharged*.
So the substance was decided; the *brief* just contradicted our own ADR. **Fixed**: the brief now mandates the
admitted lemma as a **non-promoting scaffold** (audit-tier/CONDITIONAL), an `#print axioms` closure audit, and
"no Q.E.D. until the axiom footprint is empty."

**The target theorem was mis-stated (Fugu, Fugu Ultra, Deepseek, Kimi, GLM, Qwen — Gemini 3.1 dissenting):**
- **The 2ⁿ trap (GLM, sharp):** `Rmatrix n x` read literally is the 2ⁿ×2ⁿ ambient matrix (524k² at n=19) — Lean
  cannot type-check it. It must be stated over the Terwilliger algebra's *intrinsic* basis (dim `binom(n+3,3)`)
  / a quadratic-form predicate, never the 2ⁿ space. **Fixed** (flagged explicitly).
- **Drop `IsTripleDistribution` from the algebraic lemma (Fugu, Fugu Ultra, Kimi, GLM):** block-diagonalization
  is a *purely algebraic* fact about any self-adjoint Terwilliger element, not code-derived distributions;
  split into (a) algebraic block theorem, (b) code⇒primal-feasible. **Fixed.** (Gemini 3.1 alone defended the
  bundled form — outweighed by the majority + the sharper 2ⁿ argument.)
- **Bound `∀ k` to `k ≤ ⌊n/2⌋`; require self-adjointness (Fugu Ultra, GLM). Fixed.**
- **Forward-direction-first (Fugu Ultra, Kimi):** the *bound* needs only `PSD R → ∀k PSD Mblock`; the reverse
  iff is "mathematical luxury" and the harder algebraic half. **Examination: correct and high-value** — our F2a
  `tw_weak_duality` only needs code-derived `x` primal-feasible (R,R′ PSD + forward blocks). **Fixed**: brief
  offers a forward-only first milestone. This ~halves the riskiest work.

**β guarded binomials (Fugu, Fugu Ultra, Deepseek; Gemini 3.1 wrong here):** naive `Nat.choose (n-k-u)(i-u)`
truncates (`Nat.choose 0 0 = 1`) where the value should be 0. **Examination: our own `C(a,b)` already returns 0
outside `0≤b≤a` (verified), so OUR β is correct** — the brief now *mandates* the same guarded/zero-outside
binomial for the Lean port and forbids raw `Nat` subtraction. Gemini 3.1's claim that truncation is
"advantageous" is wrong for exactly the `choose 0 0` case. **Also (Qwen, sharp):** the Lean β must be proven
equal to the certificate-generator β, or the `sorry` is a TCB leak. **Fixed** (β-equals-cert-β mandate).

**Pin PSD over ℝ (Fugu, Deepseek, GLM, Gemini, Qwen):** brief said `PosSemidef` un-scoped. **Examination: F2a
already fixes it — ℝ with rational coeffs coerced, Gram/`dotProduct_mulVec_nonneg` form.** Gemini identified the
exact Mathlib congruence lemma (`Matrix.PosSemidef.conjTranspose_mul_mul_same`). **Fixed** (stated).

**Un-normalized rational basis (Gemini, Qwen, Deepseek):** proving Theorem 1 in the normalized (√binomial)
basis drags in `Real.sqrt`/algebraic numbers; instead use the **un-normalized** orthogonal basis (clear
denominators) so everything stays in ℚ — blocks congruent up to a *positive rational diagonal*, PSD-preserving.
**Fixed** (mandated + the congruence lemma named). **Multiplicities `q_k = C(n,k)−C(n,k-1)` (Fugu, GLM):** PSD-
iff is unaffected but the *objective/trace* needs them — noted as a required downstream sign-off.

**The bridge is more than Theorem 1 (Fugu, Deepseek, MiniMax):** "exactly Theorem 1" understated it (~9
components). **Fixed**: explicit in-scope / already-done / out-of-scope table.

**Self-containment (MiniMax, strongest):** the brief failed its own "self-contained" claim — internal jargon
(F1/F2a, "operator", "corrupt controls") a cold Mathlib recipient can't parse; gap-analysis too open-ended;
no deliverable form; no concrete final theorem. **Fixed**: project-context + glossary, gap-analysis as specific
questions, a concrete `code_bound_19_6` target, deliverable form per ask, a Mathlib-commit line.

**Route framing (GLM/Qwen vs Deepseek/Gemini/Kimi split):** GLM/Qwen say the abstract route may be shorter
(index hell is brutal); Deepseek/Gemini/Kimi say abstract is *blocked* (Mathlib lacks hyperoctahedral rep
theory / Hahn polynomials) so elementary is the only path. **Examination: the split is real; the honest fix is
to stop mandating elementary** — brief now says "we *suspect* elementary is the only viable path given Mathlib
gaps; please confirm and compare," not "we prefer it."

**Estimate (all):** months, not weeks. Range across reviewers: Gemini 11 expert-weeks; Kimi 6-10 (forward-only);
Qwen 4-8 discharge; Deepseek 5-6 months. **Honest consensus: ~1-2 wks for the admitted-wiring milestone; ~3-6
months for full discharge (less if forward-only).** Added to the brief with confidence bands.

**Pre-formalization probe (Deepseek, Kimi):** before formalizing, validate the block-diagonalization *statement*
(U-orthogonality + `UᵀMU` block-diagonal against the β oracle) in Python for n≤10, to avoid admitting a *wrong*
axiom. **Examination: our F1/D1 validate β *values* against eq.(7), but not the U/block-diag statement** — a
genuine gap. Added to the brief as a recommended $0 pre-check.

**Strategic honesty (Kimi):** F2b's payoff is 3 already-known bounds re-derived at kernel tier — a "sunk
artifact" with near-zero discovery value and months of cost. This matches our own standing (ADR 0046: it is
*verification amplification*, not discovery). The forward-only scoping is what most improves its ROI. The
send/no-send decision stays the operator's; the brief is now sound *to* send.

**Net:** the review does not change the F2b decision (audit-tier verification-amplification, ADR 0046) but
substantially sharpens the brief — trust framing corrected to match our own ADR, the target theorem restated
algebraically and forward-first, β/PSD/normalization pinned, and the whole thing made genuinely self-contained.
All folded in this review-response.

---

## Full verbatim review (operator source, preserved for provenance)

```markdown
# Fugu

\#\# Executive critique

The brief is useful, but it contains one major trust-boundary problem and several formalization hazards.

Main issue:

\> “Admit this as one named, citation-backed lemma first” is fine for scaffolding, but \*\*must not be allowed to convert audit-tier certificates into Q.E.D.\*\* If the admitted lemma is used in the final proof, Schrijver’s paper has become part of the TCB. That violates the project’s own invariant unless explicitly labeled conditional/non-promoting.

Second issue:

\> The target theorem is too compressed. “\`PosSemidef Rmatrix ↔ ∀ k, PosSemidef Mblock\`” hides several delicate choices: field/coercions, symmetry/Hermitian assumptions, unnormalized-vs-normalized blocks, multiplicities, index ranges, and the exact zero-outside binomial convention.

The brief should be tightened before sending to formalizers, especially around staging, theorem shape, and the \`β\` definition.

\---

\# 1\. Trust-boundary problem: admitted lemma cannot promote

This line is dangerous:

\> “Natural staging: admit this as one named, citation-backed lemma first … then discharge.”

As engineering staging, yes. As a route to promulgated bounds, no.

If Lean has:

\`\`\`lean  
axiom schrijver\_block\_diag : ...  
\`\`\`

and the code uses it to prove:

\`\`\`lean  
theorem A\_19\_6\_le\_1280 : A 19 6 ≤ 1280 := ...  
\`\`\`

then the kernel checks only a theorem \*\*relative to an axiom\*\*. The result is not kernel-grounded in the project’s sense. It is only as sound as the admitted statement.

Required clarification:

\`\`\`text  
Admitted/citation-backed lemma is allowed only in a non-promoting scaffold build.  
Any theorem depending on it must be labeled CONDITIONAL / AXIOM\_DEPENDENT / AUDIT-TIER.  
No Q.E.D. promotion until axiom footprint is empty or contains only explicitly allowed Mathlib axioms.  
\`\`\`

You should add an explicit axiom-audit requirement:

\`\`\`text  
\#check axioms A\_19\_6\_le\_1280  
\`\`\`

or the Lean equivalent in your pipeline. Reject any dependency on:

\`\`\`text  
sorryAx  
schrijver\_block\_diag as axiom  
admit  
unsafe assumptions  
\`\`\`

The staged plan should be:

1\. \*\*Stage F2b-0:\*\* use \`axiom schrijver\_block\_diag\` only to wire interfaces and test proof architecture. No Q.E.D.  
2\. \*\*Stage F2b-1:\*\* prove enough lemmas to discharge the axiom.  
3\. \*\*Stage F2b-2:\*\* rerun axiom audit. Only then promote bounds.

\---

\# 2\. Target theorem is too monolithic

Current target:

\`\`\`lean  
lemma schrijver\_block\_diag (n : ℕ) (x : Triple n → ℚ) (hx : IsTripleDistribution x) :  
    PosSemidef (Rmatrix n x) ↔ ∀ k, PosSemidef (Mblock n k x)  
\`\`\`

This is too much in one statement and also probably has the wrong assumptions.

\#\# Suggested decomposition

Do not tie block diagonalization to \`IsTripleDistribution\`. Schrijver’s block diagonalization is an algebraic theorem about any matrix in the Terwilliger algebra, not specifically about code-derived triple distributions.

Better:

\`\`\`lean  
def TripleIndex (n : ℕ) := ...  
def TerwCoeff (n : ℕ) := TripleIndex n → ℚ

def Rmatrix (n : ℕ) (x : TerwCoeff n) : Matrix (Finset (Fin n)) (Finset (Fin n)) ℝ := ...  
def Mblock (n : ℕ) (k : ℕ) (x : TerwCoeff n) : Matrix (BlockIndex n k) (BlockIndex n k) ℝ := ...

lemma schrijver\_block\_diag  
  (n : ℕ) (x : TerwCoeff n)  
  (hsym : TerwCoeffSymmetric n x) :  
  Matrix.PosSemidef (Rmatrix n x) ↔  
    ∀ k, k ≤ n / 2 → Matrix.PosSemidef (Mblock n k x)  
\`\`\`

Then separately:

\`\`\`lean  
lemma code\_triple\_distribution\_constraints :  
  Code n d C → IsTripleDistribution n (tripleDist C)

lemma code\_Rmatrix\_psd :  
  Code n d C → PosSemidef (Rmatrix n (tripleDist C))

lemma code\_Rprime\_matrix\_psd :  
  Code n d C → PosSemidef (RprimeMatrix n (tripleDist C))

lemma objective\_identity :  
  |C| \= ∑ i, Nat.choose n i \* x(i,0,0)  
\`\`\`

This is cleaner and prevents \`IsTripleDistribution\` from hiding assumptions needed for block diagonalization.

\---

\# 3\. The \`β\` formula needs Lean-safe binomial conventions

You state:

\`\`\`text  
binomials zero outside 0 ≤ b ≤ a  
\`\`\`

Good. But in Lean this is dangerous if implemented with plain \`Nat.choose\` after subtractions.

Example hazard:

\`\`\`lean  
Nat.choose (n \- k \- u) (i \- u)  
\`\`\`

If \`u \> i\`, then \`i \- u \= 0\` by truncated subtraction, so this may become:

\`\`\`lean  
Nat.choose (...) 0 \= 1  
\`\`\`

when mathematically it should be zero.

This is a serious formalization trap.

\#\# Required fix

Define an integer/guarded binomial:

\`\`\`lean  
def zchoose (a b : ℤ) : ℤ :=  
  if 0 ≤ b ∧ b ≤ a then Nat.choose a.toNat b.toNat else 0  
\`\`\`

or a guarded natural version:

\`\`\`lean  
def chooseZOutside (a b : ℤ) : ℤ := ...  
\`\`\`

Then define β using integer arguments:

\`\`\`lean  
β n i j t k \=  
  ∑ u in Finset.range (n+1),  
    (-1 : ℤ)^(u \- t) \*  
    zchoose u t \*  
    zchoose (n \- 2\*k) (u \- k) \*  
    zchoose (n \- k \- u) (i \- u) \*  
    zchoose (n \- k \- u) (j \- u)  
\`\`\`

with all variables coerced to \`ℤ\`.

If you keep \`Nat.choose\`, every term must be guarded explicitly:

\`\`\`lean  
if h :  
  t ≤ u ∧ k ≤ u ∧ u ≤ i ∧ u ≤ j ∧  
  u ≤ n \- k ∧ u \- k ≤ n \- 2\*k ∧  
  i \- u ≤ n \- k \- u ∧  
  j \- u ≤ n \- k \- u  
then ...  
else 0  
\`\`\`

Do not rely on truncated subtraction.

This should be called out in the brief.

\---

\# 4\. Field/coercion issue: PSD over \`ℚ\` or \`ℝ\`?

The target uses:

\`\`\`lean  
x : Triple n → ℚ  
PosSemidef (Rmatrix n x)  
\`\`\`

But PSD is naturally over \`ℝ\` or \`ℂ\`, and Mathlib’s \`Matrix.PosSemidef\` may impose \`RCLike\`/star-ordered assumptions depending on the exact API.

The formalization plan should specify:

\- Are matrices over \`ℚ\`, \`ℝ\`, or \`ℂ\`?  
\- Are rational certificate matrices coerced into \`ℝ\`?  
\- Does existing F2a use Gram witnesses over rationals or real PSD?

I would recommend:

\`\`\`lean  
x : Triple n → ℚ  
Rmatrix ... : Matrix ... ... ℝ  
Mblock ... : Matrix ... ... ℝ  
\`\`\`

with rational coefficients coerced to real.

The certificate side can remain exact over integers/rationals, proving a Gram/LDLT identity that implies real PSD.

Add this to the brief:

\> Please advise whether the bridge theorem should be stated over \`ℝ\` with rational coefficients coerced, or over \`ℚ\` with a separate lemma that rational Gram witnesses imply real PSD.

\---

\# 5\. Unnormalized vs normalized blocks must be explicit

You rely on Schrijver’s integer β coefficients after deleting the square-root normalization. That is plausible and useful, but the formalization needs a lemma:

\`\`\`lean  
lemma posSemidef\_congr\_diag\_pos :  
  D has positive diagonal →  
  PosSemidef M ↔ PosSemidef (D ⬝ M ⬝ D)  
\`\`\`

or the relevant direction.

The formal theorem must be clear whether \`Mblock\` is:

1\. the normalized block from eq. (8), or  
2\. the unnormalized integer β block after positive diagonal congruence.

If you prove Theorem 1 in the normalized basis but your certificate uses unnormalized integer blocks, you need the congruence bridge.

Add an explicit ask:

\> Please include the normalization-removal lemma as a named subgoal and state the exact diagonal scaling.

\---

\# 6\. Multiplicities and direct-sum equivalence must not be hidden

Schrijver’s algebra decomposes into blocks with multiplicities:

\`\`\`text  
q\_k \= C(n,k) \- C(n,k-1)  
\`\`\`

For PSD equivalence, multiplicities usually do not change the condition:

\`\`\`text  
block repeated q\_k times PSD iff block PSD  
\`\`\`

But the formal proof needs to account for them if it constructs the actual change of basis.

Add a named lemma:

\`\`\`lean  
lemma blockDiag\_repeated\_posSemidef\_iff :  
  PosSemidef (directSum over k of repeatedBlock q\_k (Mblock k)) ↔  
    ∀ k, PosSemidef (Mblock k)  
\`\`\`

or avoid direct repeated blocks if the proof route uses subspaces.

Also ask formalizers:

\> Do multiplicities appear in the PSD equivalence proof, or only in the algebra isomorphism? Where should they be represented in Lean?

\---

\# 7\. The code-bound bridge is more than Theorem 1

The brief says:

\> What remains for a full bridge is exactly: codes ⇒ primal-feasible, whose core is Theorem 1 above...

This is directionally right, but “exactly” is too strong.

You still need:

1\. definition of binary code and minimum distance;  
2\. triple distribution induced by a code;  
3\. nonnegativity and symmetry constraints;  
4\. distance-zero constraints;  
5\. R and R′ matrices are averaged outer products / PSD;  
6\. Theorem 1 maps R/R′ PSD to all SDP blocks PSD;  
7\. objective identity;  
8\. weak duality application;  
9\. integer rounding from rational bound to \`A(n,d) ≤ B\`.

Some are already done, but the brief should not imply Theorem 1 alone is the bridge.

Suggested wording:

\> Theorem 1 is the largest missing algebraic component. The full bridge also requires the code-to-primal-feasible lemmas listed below; some are already covered by F2a/F1, others remain to be wired.

\---

\# 8\. Ask for a real lemma dependency graph

The brief asks for a “lemma-level decomposition,” but I would make it more constrained.

Request a plan with this shape:

\`\`\`text  
Layer 0: finite sets / Boolean cube / cardinality lemmas  
Layer 1: Terwilliger basis matrices M^t\_{i,j}  
Layer 2: β formula and block definitions  
Layer 3: U/change-of-basis construction  
Layer 4: action of basis matrices on U-subspaces  
Layer 5: block diagonalization theorem  
Layer 6: normalized-to-integer block congruence  
Layer 7: code triple distribution → R/R′ PSD  
Layer 8: SDP primal feasibility → dual bound  
\`\`\`

For each lemma:

\`\`\`text  
statement sketch  
Mathlib dependencies  
expected difficulty  
risk  
can be admitted temporarily? yes/no  
\`\`\`

This will produce a more actionable external response.

\---

\# 9\. Gap analysis: likely Mathlib gaps

You should prime reviewers with the likely gaps so they can confirm/correct.

Likely existing in Mathlib:

\- finite types, finsets, finite sums;  
\- matrices and block matrices;  
\- real inner product spaces;  
\- basic PSD definitions;  
\- matrix congruence-type facts, possibly with missing exact statement;  
\- binomial identities, but not necessarily the needed Krawtchouk/Terwilliger sums;  
\- \`Finset\` cardinality lemmas;  
\- submodule/direct-sum infrastructure, though maybe heavy.

Likely missing or painful:

\- Terwilliger algebra of Hamming scheme;  
\- Johnson scheme / Krawtchouk-specific identities in this form;  
\- Schrijver’s explicit \`U\` basis construction;  
\- the exact β summation identity;  
\- block diagonalization theorem;  
\- convenient PSD iff for repeated block direct sums;  
\- automation for large combinatorial binomial sums.

The brief could explicitly ask:

\> Is the elementary Schrijver §II proof actually shorter in Lean than using Mathlib representation theory? Or does the elementary route require many bespoke binomial identities that dominate the effort?

\---

\# 10\. Estimate: ask for ranges and confidence

The brief asks for expert-weeks. Good. Ask for confidence bands:

\`\`\`text  
scaffold with admitted theorem: 1–3 days?  
formal statement \+ interfaces: 1 week?  
full elementary proof: 4–12 expert-weeks?  
risk of \>3 months: ?  
\`\`\`

My own rough guess:

\- admitted-lemma wiring: \*\*1–3 days\*\*, high confidence if existing F2a is clean;  
\- clean theorem statements/interfaces: \*\*1–2 weeks\*\*, medium confidence;  
\- full Schrijver Theorem 1 elementary formalization: \*\*6–16 expert-weeks\*\*, low confidence;  
\- full code-bound bridge to all three bounds: \*\*8–20 expert-weeks\*\*, low confidence.

The variance is high because the β/binomial identities could explode.

\---

\# 11\. Suggested revised target statement

A safer target might look like:

\`\`\`lean  
/-- Integer-coefficient Schrijver block. \-/  
def schrijverBlock  
  (n k : ℕ) (x : TripleIndex n → ℚ) :  
  Matrix (BlockIndex n k) (BlockIndex n k) ℝ := ...

/-- Matrix in the Terwilliger algebra associated to triple coefficients. \-/  
def terwMatrix  
  (n : ℕ) (x : TripleIndex n → ℚ) :  
  Matrix (SetLikeCube n) (SetLikeCube n) ℝ := ...

theorem schrijver\_block\_diag\_integer  
  (n : ℕ)  
  (x : TripleIndex n → ℚ)  
  (hsym : TripleCoeffSymmetric n x) :  
  Matrix.PosSemidef (terwMatrix n x) ↔  
    ∀ k : ℕ, k ≤ n / 2 →  
      Matrix.PosSemidef (schrijverBlock n k x)  
\`\`\`

Then have separate lemmas:

\`\`\`lean  
theorem code\_R\_psd ...  
theorem code\_Rprime\_psd ...  
theorem code\_sdp\_primal\_feasible ...  
theorem schrijver\_dual\_cert\_implies\_code\_bound ...  
\`\`\`

This avoids putting \`IsTripleDistribution\` into the algebra theorem.

\---

\# 12\. Add explicit “no source of truth drift” requirement

You mention the β oracle and kernel-side β. Good. Add:

\> The formalized β definition must be the same definition used by the certificate generator, ideally by emitting a hash or generated test comparing all β entries for the target cells.

Even better:

\- one canonical Python/Lean TSV generator is not a proof, but helps detect drift;  
\- Lean theorem should use the same \`beta\` function as the certificate render;  
\- all rendered certificates should reference \`beta\`, or if using literals, separately prove literals equal beta.

If certificate theorems use integer literals for speed, add a generated lemma:

\`\`\`lean  
theorem beta\_table\_correct\_n19 : ...  
\`\`\`

or accept that the literal stationarity proof checks the instantiated SDP, while the β theorem checks the bridge formula separately.

\---

\# 13\. One thing you are likely getting wrong

You may be underestimating the cost of formalizing Schrijver’s “elementary” proof.

“Elementary” on paper often means:

\- many implicit finite-dimensional subspace identifications;  
\- heavy index manipulation;  
\- binomial identities with zero-outside conventions;  
\- hidden changes of basis;  
\- informal “it is easy to see” orthogonality steps.

In Lean, that can be harder than a more abstract route if Mathlib already supports finite group representations or inner-product decompositions better than the bespoke combinatorics. I still suspect the elementary route is the right first attempt, but do not assume it is cheap because the paper proof is short.

Ask the external formalizer to explicitly compare:

\`\`\`text  
elementary β proof vs representation-theoretic proof  
\`\`\`

in terms of current Mathlib availability.

\---

\#\# Concrete edits I recommend

\#\#\# Replace

\> Natural staging: admit this as one named, citation-backed lemma first ... then discharge.

\#\#\# With

\> For scaffolding only, temporarily introduce this as an axiom to test interfaces. Any theorem depending on it is conditional/audit-tier and cannot be Q.E.D.; production requires an empty axiom footprint after the lemma is discharged.

\---

\#\#\# Add after the β formula

\> In Lean, this must not be implemented using unguarded \`Nat\` subtraction inside \`Nat.choose\`; use an integer/guarded binomial with zero-outside semantics.

\---

\#\#\# Replace

\`\`\`lean  
lemma schrijver\_block\_diag (n : ℕ) (x : Triple n → ℚ) (hx : IsTripleDistribution x) :  
    PosSemidef (Rmatrix n x) ↔ ∀ k, PosSemidef (Mblock n k x)  
\`\`\`

\#\#\# With a more algebraic version

\`\`\`lean  
lemma schrijver\_block\_diag  
    (n : ℕ) (x : TripleIndex n → ℚ)  
    (hsym : TripleCoeffSymmetric n x) :  
    PosSemidef (Rmatrix n x) ↔  
      ∀ k, k ≤ n / 2 → PosSemidef (Mblock n k x)  
\`\`\`

and put \`IsTripleDistribution\` in later code-derived lemmas.

\---

\#\#\# Add to asks

\> Please identify the exact diagonal congruence that removes Schrijver’s square-root normalization and state the PSD-preservation lemma needed in Lean.

\---

\#\#\# Add to asks

\> Please state whether the formal proof should be over \`ℚ\`, \`ℝ\`, or rational matrices coerced to \`ℝ\`, given Mathlib’s \`Matrix.PosSemidef\` API.

\---

\#\# Bottom line

The brief is worth sending after one major correction: make clear that an admitted Schrijver block-diagonalization lemma is \*\*non-promoting scaffolding only\*\*, not a trusted shortcut. Also revise the theorem statement to separate the algebraic block-diagonalization from code-derived triple-distribution constraints, and explicitly require guarded zero-outside binomial semantics. Without those changes, the external work may produce a compiling bridge that is either axiom-dependent or subtly formalizes the wrong β convention.

# Fugu Ultra

\#\# Executive verdict

Do \*\*not\*\* send or rely on this brief unchanged. The mathematical direction is good, and the corrected \\(\\beta\\) formula with \\(C(u,t)\\) is a major improvement, but the current brief still has three serious problems:

1\. \*\*It blurs the trust boundary\*\* by proposing an admitted “citation-backed” lemma in a way that could contaminate Q.E.D. results.  
2\. \*\*The target theorem is the wrong interface\*\*: too code-specific, underspecified, and missing symmetry/index/PSD details.  
3\. \*\*It underestimates Lean formalization hazards\*\*, especially \`Nat\` subtraction in \\(\\beta\\), PSD over \\(\\mathbb Q\\) vs \\(\\mathbb R\\), and the cost of Schrijver’s “elementary” combinatorics.

If already sent, I would send an erratum. If not sent, revise first.

\---

\#\# 1\. Biggest trust issue: “admit first” must be quarantined

This sentence is dangerous:

\> “admit this as one named, citation-backed lemma first (it shrinks our informal trusted base to a single statement), then discharge.”

In Lean, an admitted theorem or \`axiom\` is not informal; it is a formal trusted assumption. A downstream theorem depending on it is kernel-checked \*\*relative to that axiom\*\*, not Q.E.D. under Leibniz’s stated invariant.

A citation does not shrink the trusted base. It expands it.

Required rewrite:

\> “For plumbing only, we may introduce a namespaced axiom-stub \`schrijver\_block\_diag\_axiom\`. Any theorem depending on it is audit-tier / conditional only and must not be promoted. CI must report axiom closure, and no final theorem may be Q.E.D. until the stub is replaced by a sorry-free proof.”

Required safeguards:

\- every concrete bound theorem must run \`\#print axioms\` / axiom-closure equivalent;  
\- CI fails promotion if the axiom closure includes \`schrijver\_block\_diag\_axiom\`, \`sorryAx\`, or unapproved axioms;  
\- admitted-lemma wiring is a development milestone, not a proof milestone.

This is the most important fix.

\---

\#\# 2\. Target theorem is not the right formal interface

Current sketch:

\`\`\`lean  
lemma schrijver\_block\_diag (n : ℕ) (x : Triple n → ℚ) (hx : IsTripleDistribution x) :  
    PosSemidef (Rmatrix n x) ↔ ∀ k, PosSemidef (Mblock n k x)  
\`\`\`

This is too vague and probably the wrong abstraction.

\#\#\# Problem A: \`IsTripleDistribution\` is too restrictive

Schrijver’s block diagonalization is an algebraic theorem about arbitrary elements of the Terwilliger algebra, not only code-derived triple distributions.

Better split:

1\. \*\*Algebraic block theorem\*\* for arbitrary self-adjoint Terwilliger coefficients.  
2\. \*\*Code-to-primal-feasible theorem\*\* showing code-derived triples satisfy Schrijver’s SDP constraints.

Suggested shape:

\`\`\`lean  
theorem schrijver\_block\_psd\_iff  
    (n : ℕ)  
    (a : TerwCoeff n ℚ)  
    (ha : SelfAdjointTerwCoeff n a) :  
    PSD (terwMatrix n a) ↔  
      ∀ k : Fin (n / 2 \+ 1), PSD (schrijverBlock n k a)  
\`\`\`

Then separately:

\`\`\`lean  
theorem code\_triples\_primal\_feasible  
    (C : Finset (Word n))  
    (hmin : MinDistAtLeast C d) :  
    SchrijverPrimalFeasible n d (tripleDistribution C)  
\`\`\`

Do not drag \`IsTripleDistribution\` into the pure block-diagonalization theorem.

\#\#\# Problem B: \`∀ k\` must be bounded

\`k\` ranges over:

\\\[  
0 \\le k \\le \\lfloor n/2\\rfloor.  
\\\]

Use:

\`\`\`lean  
∀ k : Fin (n / 2 \+ 1), ...  
\`\`\`

or an explicit bounded hypothesis.

Unbounded \`∀ k\` is either false, meaningless, or depends on arbitrary behavior of \`Mblock\` outside its valid range.

\#\#\# Problem C: PSD needs symmetry/self-adjointness

A general coefficient family \\(x^t\_{i,j}\\) need not produce a symmetric matrix. PSD is only meaningful for symmetric/self-adjoint matrices.

The theorem needs either:

\`\`\`lean  
SelfAdjointTerwCoeff n a  
\`\`\`

or a coefficient type that enforces the symmetry by construction.

For code-derived triples, symmetry may follow from permutation invariance of the three distances, but the algebraic theorem should state the minimal symmetry assumption directly.

\#\#\# Problem D: for the bound, you may not need the full iff

For proving code upper bounds, the needed direction is likely:

\`\`\`lean  
PSD (Rmatrix n a) →  
  ∀ k, PSD (Mblock n k a)  
\`\`\`

because code-derived matrices \\(R\\) and \\(R'\\) are shown PSD by averaged outer products, and then block PSD constraints follow.

The reverse direction is mathematically true and useful, but if the formalization is hard, prove the needed direction first. Do not force the project to pay for a stronger theorem before the first bridge.

\---

\#\# 3\. Pin the PSD notion

The brief says \`PosSemidef\` but does not specify which one.

You need to decide and state one of:

1\. Mathlib PSD over \`ℝ\`, with rational matrices cast from \`ℚ\`;  
2\. project-local rational quadratic-form PSD:  
   \`\`\`lean  
   PSDq M := ∀ v : ι → ℚ, 0 ≤ v ⬝ M.mulVec v  
   \`\`\`  
3\. Gram/LDLT certificate PSD, matching your emitted certificates.

My recommendation:

\- State Schrijver’s block theorem semantically over \`ℝ\`, or over a clean project-local \`PSDq\`.  
\- Separately prove the bridge from your exact LDLT/Gram witness to that PSD notion.  
\- Make \`tw\_weak\_duality\`’s required PSD interface explicit in the brief.

Otherwise an external formalizer may prove a correct theorem over the wrong PSD predicate.

\---

\#\# 4\. \\(\\beta\\) formula: correct, but Lean implementation is still hazardous

Good: the brief now uses:

\\\[  
C(u,t)  
\\\]

not \\(C(t,u)\\). That is the right correction.

But the Lean-level danger remains severe.

The formula contains terms like:

\\\[  
C(n-k-u, i-u).  
\\\]

In Lean, raw \`Nat\` subtraction saturates at zero. That can silently turn a mathematically invalid binomial into \`Nat.choose 0 0 \= 1\`.

Example failure mode:

\- mathematically, \\(n-k-u \< 0\\), so \\(C(n-k-u, i-u)\\) should be zero;  
\- in Lean \`Nat\`, \`n \- k \- u \= 0\`;  
\- if also \`i \- u \= 0\`, Lean computes \`Nat.choose 0 0 \= 1\`.

That corrupts \\(\\beta\\).

Mandate a safe binomial:

\`\`\`lean  
def zchoose (a b : ℤ) : ℤ :=  
  if 0 ≤ b ∧ b ≤ a then Nat.choose a.toNat b.toNat else 0  
\`\`\`

or an equivalent guarded \`Nat\` version.

Also specify the summation range:

\\\[  
u=\\max(k,t),\\dots,\\min(i,j)  
\\\]

or sum over all \`u ≤ n\` with fully guarded binomials.

The sign should also be guarded. Do not write \`(-1)^(u-t)\` over \`Nat\` unless the range guarantees \`t ≤ u\`.

Suggested text to add:

\> “All binomial terms in \\(\\beta\\) must use a zero-outside-range guarded binomial; raw \`Nat\` subtraction is forbidden in the specification.”

The TSV oracle is useful as a regression fixture, but it must not become a proof source.

\---

\#\# 5\. The “elementary proof path” preference is too strong

The brief says:

\> “We explicitly prefer \[Schrijver’s elementary route\] over abstract C\*-algebra/representation-theoretic machinery…”

This may be bad advice.

Schrijver’s §II proof is elementary on paper, but in Lean it means:

\- nested finite sums;  
\- subset-indexed bases;  
\- alternating binomial identities;  
\- dependent bounds;  
\- many index shifts;  
\- Vandermonde-style manipulations.

That is exactly the kind of proof that can become very expensive in a proof assistant.

A representation-theoretic or module-theoretic route may actually be shorter if Mathlib already has enough linear algebra infrastructure.

Recommended rewrite:

\> “Schrijver’s §II proof is a plausible elementary route, but we do not want to over-prescribe. Please compare the elementary finite-combinatorial route with any algebraic/representation-theoretic route that is shorter in current Mathlib, and recommend the path with the fewest new hard lemmas.”

Ask for a route comparison, not just an implementation of the route you currently expect.

\---

\#\# 6\. The brief conflates three layers

Right now it presents Theorem 1 as “what remains” for the bridge. That is only partly true.

You need all of:

1\. \*\*Block diagonalization\*\* of the Terwilliger algebra.  
2\. \*\*Code-derived triple distribution\*\* satisfies Schrijver’s SDP primal constraints.  
3\. \*\*Dual certificate weak duality\*\* connects the exact certificate to a code-size upper bound.  
4\. \*\*Concrete final theorem\*\* about \\(A(n,d)\\) or all finite codes.

The brief says F2a already covers weak duality, good. But the external formalizer still needs exact signatures for what must connect.

Add final theorem targets, e.g.:

\`\`\`lean  
theorem A\_19\_6\_le\_1280 :  
  A 19 6 ≤ 1280  
\`\`\`

or, more explicitly:

\`\`\`lean  
theorem code\_bound\_19\_6 :  
  ∀ C : Finset (Word 19),  
    MinDistAtLeast C 6 → C.card ≤ 1280  
\`\`\`

Without this, a formalizer can produce a correct block theorem that still does not plug into the certificate pipeline.

\---

\#\# 7\. Clarify R and R′ usage

Schrijver’s SDP uses two PSD block families:

\\\[  
R  
\\\]

and

\\\[  
R'.  
\\\]

The block theorem should be a reusable algebraic lemma. Then instantiate it twice:

1\. coefficients \\(a^t\_{i,j}=x^t\_{i,j}\\);  
2\. coefficients \\(a^t\_{i,j}=x^0\_{i+j-2t,0}-x^t\_{i,j}\\).

Make this explicit.

Otherwise someone may try to bake the two-family SDP structure into \`Mblock\`, which would be the wrong abstraction.

\---

\#\# 8\. Prefer a stronger decomposition theorem as the main proof target

The clean proof object is not merely:

\`\`\`lean  
PSD full ↔ PSD blocks  
\`\`\`

but something like:

\\\[  
U^T M U \=  
\\bigoplus\_k q\_k \\cdot M\_k  
\\\]

where:

\\\[  
q\_k=\\binom nk-\\binom n{k-1}.  
\\\]

Then PSD equivalence follows from:

\- PSD invariance under congruence by invertible \\(U\\);  
\- PSD of block diagonal iff each block is PSD;  
\- repeated block multiplicities do not change the condition.

This theorem also exposes where the multiplicities go. The current brief never mentions \\(q\_k\\), but a formal proof probably cannot ignore it.

Suggested ask:

\> “Would you prove an explicit congruence/direct-sum decomposition first, and derive PSD iff as a corollary? If not, why is a direct PSD proof easier?”

\---

\#\# 9\. Need a compiling Lean skeleton

The brief asks for estimates, but without exact signatures those estimates will be low quality.

Include or attach:

\- exact Lean version and Mathlib commit;  
\- definitions/stubs for:  
  \- \`Triple\`;  
  \- \`TerwCoeff\`;  
  \- \`Rmatrix\` / \`terwMatrix\`;  
  \- \`Mblock\` / \`schrijverBlock\`;  
  \- \`PosSemidef\` / \`PSDq\`;  
  \- \`gram\_pairing\_nonneg\`;  
  \- \`tw\_weak\_duality\`;  
  \- final bound theorem stub;  
\- exact import list;  
\- what axioms are currently permitted;  
\- performance constraints.

If the external formalizer has to infer these, the first week will be interface archaeology.

\---

\#\# 10\. Gap analysis: likely reality

I cannot verify the exact current Mathlib 4.31 APIs from the brief alone, but calibrated expectation:

Likely available:

\- finite types, \`Fin\`, \`Finset\`, \`Fintype\`;  
\- \`Nat.choose\`;  
\- finite sums / big operators;  
\- matrices and matrix multiplication;  
\- some block-matrix tools;  
\- some PSD / positive-semidefinite infrastructure;  
\- linear equivalences and congruence-style lemmas.

Likely missing or project-local:

\- Terwilliger algebra of the Hamming scheme;  
\- the \\(M^t\_{i,j}\\) basis;  
\- Schrijver’s \\(U\\) basis;  
\- the β coefficient derivation;  
\- alternating binomial identities in this exact form;  
\- code triple distributions;  
\- Schrijver SDP primal feasibility;  
\- the two \\(R/R'\\) averaged-outer-product PSD proofs.

Riskiest lemmas:

1\. deriving the \\(\\beta\\) block entries from the chosen basis;  
2\. proving the direct-sum/congruence decomposition;  
3\. proving code-derived \\(R/R'\\) PSD and equation (21) with the right normalization.

PSD congruence itself is probably not the hard part; index-heavy combinatorics is.

\---

\#\# 11\. Estimate critique

The brief asks for expert-weeks, but it should warn that estimates are high-variance until the Lean skeleton exists.

My rough estimate:

\- admitted-stub plumbing against existing F2a: \*\*2–5 days\*\*;  
\- definitions, safe β, blocks, and small regression fixtures: \*\*1–2 expert-weeks\*\*;  
\- full Schrijver block proof: \*\*8–20 expert-weeks\*\*, high variance;  
\- code-to-primal-feasible bridge: \*\*4–10 expert-weeks\*\*;  
\- end-to-end concrete theorem with no project axioms: \*\*12–30 expert-weeks\*\* total.

The largest uncertainty is not the math statement; it is Lean proof engineering around finite sums and dependent indices.

\---

\#\# 12\. Concrete edits I would make before sending

\#\#\# Replace the target statement

Current:

\`\`\`lean  
lemma schrijver\_block\_diag (n : ℕ) (x : Triple n → ℚ) (hx : IsTripleDistribution x) :  
    PosSemidef (Rmatrix n x) ↔ ∀ k, PosSemidef (Mblock n k x)  
\`\`\`

Suggested:

\`\`\`lean  
theorem schrijver\_block\_psd\_iff  
    (n : ℕ)  
    (a : TerwCoeff n ℚ)  
    (ha : SelfAdjointTerwCoeff n a) :  
    PSD (terwMatrix n a) ↔  
      ∀ k : Fin (n / 2 \+ 1), PSD (schrijverBlock n k a)  
\`\`\`

And optionally a first weaker target:

\`\`\`lean  
theorem schrijver\_blocks\_psd\_of\_full\_psd  
    (n : ℕ)  
    (a : TerwCoeff n ℚ)  
    (ha : SelfAdjointTerwCoeff n a) :  
    PSD (terwMatrix n a) →  
      ∀ k : Fin (n / 2 \+ 1), PSD (schrijverBlock n k a)  
\`\`\`

\#\#\# Add trust-status language

Add:

\> “An admitted version is for plumbing only. Any theorem depending on it is conditional/audit-tier and must not be promulgated. Final Q.E.D. requires empty project-axiom closure.”

\#\#\# Add safe-binomial warning

Add:

\> “The formal \\(\\beta\\) definition must use guarded zero-outside-range binomial coefficients; raw \`Nat\` subtraction is not acceptable.”

\#\#\# Clarify R/R′

Add:

\> “The block theorem is applied twice, once to \\(x^t\_{i,j}\\) and once to \\(x^0\_{i+j-2t,0}-x^t\_{i,j}\\).”

\#\#\# Add final theorem target

Add one concrete end-to-end statement, e.g.:

\`\`\`lean  
theorem code\_bound\_19\_6 :  
  ∀ C : Finset (Word 19),  
    MinDistAtLeast C 6 → C.card ≤ 1280  
\`\`\`

\#\#\# Attach skeleton

Add links or code excerpts for the actual F2a theorem signatures and expected imports.

\---

\#\# Final recommendation

Revise the brief before relying on it: quarantine any admitted Schrijver lemma as non-Q.E.D., restate the block theorem over arbitrary self-adjoint Terwilliger coefficients with bounded \\(k\\), pin the exact PSD predicate and safe \\(\\beta\\) arithmetic, ask for route comparison rather than forcing the elementary proof, and attach a compiling Lean skeleton plus final theorem signature.

# Deepseek v4 Pro

This is a well‑constructed brief, but the scope of the formalization task it describes is significantly larger than the “admit this one lemma, then discharge” framing suggests. I’ll critique it directly, focusing on feasibility, hidden costs, and where the plan could break down.

\---

\#\#\# 1\. Overall assessment

The decision to formalize Schrijver’s elementary §II proof is strategically correct: it avoids heavy representation theory and keeps dependencies small. However, the elementary proof is \*\*not\*\* a single lemma—it is a multi‑page construction culminating in an explicit orthogonal change‑of‑basis \`U\` (Propositions 2–5) followed by a combinatorial verification that \`U\` block‑diagonalizes the Terwilliger algebra. Schrijver’s §II is the core of the paper; formalizing it in full will require building a substantial library of combinatorial identities and handling sums over subsets with variable \`n\`. I do not see any way to shrink this to a single “admitted lemma” that can be wired in a few days; the “admit then discharge” approach would leave a very large sorried statement whose later discharge is the entire project.

The realistic staging is: \*\*admit the whole block‑diagonalization theorem as a single \`sorry\`\*\* to unblock downstream work (kernel wiring, certificate checking) and then gradually replace the \`sorry\` with a full proof over several months. That is a valid plan, but the brief should be explicit that the admitted lemma is huge.

\---

\#\#\# 2\. Gap analysis — what Mathlib currently has

\*\*What exists:\*\*  
\- \*\*Matrices and PSD:\*\* \`Matrix\` over \`ℝ\` (or \`ℚ\`) is mature. \`Matrix.PosSemidef\` is defined, usually via the quadratic form \`vᵀ M v ≥ 0\` for all \`v\`. Congruence invariance (\`M\` PSD iff \`P \* M \* Pᵀ\` PSD for invertible \`P\`) is likely not a one‑liner but is provable with existing lemmas about \`mulVec\` and dot products. The block‑diagonal case will need \`Matrix.fromBlocks\` and the lemma you already identified. That part is manageable.  
\- \*\*Binomial coefficients:\*\* \`Nat.choose\` with standard identities (Pascal, symmetry) is present. Sums over \`Finset\` are well‑supported.  
\- \*\*Kernel‑side arithmetic:\*\* your F1 checker already computes \`β\` inside Lean, so the correctness of the formula is already established in a computational way. That reduces the burden for the symbolic proof.

\*\*What is missing (and will need to be built from scratch):\*\*  
\- \*\*The change‑of‑basis matrix \`U\`.\*\* This is an orthogonal matrix of size \`2ⁿ × 2ⁿ\` whose entries are square roots of rational numbers? Wait—Schrijver’s \`U\` is orthogonal with respect to a weighted inner product, and its entries involve square roots of binomial coefficients (eq. (8) normalisation). However, the normalisation factors are deleted to make the block integer‑coeff, but the proof of block‑diagonalization still uses those raw matrices with square roots. The formalization will have to work with the orthogonal matrix in ℝ, not ℚ, using algebraic numbers. That introduces \`Real.sqrt\` and \`Algebraic\` numbers, complicating the algebra. The “elementary” proof is still algebraic but carries these irrationalities, which must be handled with field extensions or by working in \`ℝ\` and using algebraic identities. This is a major source of pain.  
\- \*\*Proposition 2–5 of Schrijver:\*\* These are explicit combinatorial expressions for the basis vectors of the irreducible modules. They involve sums over subsets and binomial identities. Mathlib has no ready‑made lemmas for these specific sums; everything must be proved from scratch.  
\- \*\*Block‑diagonalization argument:\*\* showing that after change of basis the matrix becomes block‑diagonal with blocks given by the \`β\` coefficients. This involves expanding double sums of \`x\` variables against the basis elements, which is a large but finite algebraic verification. It can be done by using the explicit formulas for \`U\` and its inverse and then expanding sums. The key difficulty is the sheer number of index manipulations; a single off‑by‑one mistake will grind progress to a halt.

\*\*Bottom line:\*\* Mathlib provides the matrix algebra and basic combinatorics; the \*\*entire content of Schrijver’s §II must be formalized from first principles\*\*. There is no existing library for association schemes or Terwilliger algebras. That gap is the project.

\---

\#\#\# 3\. Lemma decomposition and riskiest parts

A realistic lemma plan would look like:

1\. Define the Terwilliger algebra’s generating matrices \`M^t\_{i,j}\` as explicit \`(2ⁿ × 2ⁿ)\` matrices indexed by subsets, with entry \`1\` exactly when the subset sizes and intersection match. (Already partially in F2a? Possibly, but the block‑diagonalization needs the full ambient matrix.)  
2\. Define the change‑of‑basis \`U\` (as a matrix over ℝ with entries involving \`Real.sqrt\` of binomials) and prove \`Uᵀ \* U \= I\` (weighted inner product). This requires identities involving sums of binomials over subsets—risky because of the square roots.  
3\. Prove that for each generator \`M\`, the transformed matrix \`U \* M \* Uᵀ\` is block‑diagonal with blocks given by \`β\`. This is the core computation, with many nested sums.  
4\. Then for a general \`x\`-linear combination, the PSD equivalence reduces to block‑PSD because block‑diagonal matrices with zero off‑diagonals are PSD iff each block is. This step is relatively easy with \`fromBlocks\`.

\*\*Riskiest lemmas:\*\*  
\- The orthogonality of \`U\` — combinatorial sums with square roots that must cancel exactly.  
\- The explicit form of the blocks after transformation — this is where the β formula emerges and must match the combinatorial definition.

Without a highly automated sum‑normalisation tactic (which Mathlib lacks for this kind of combinatorial sum), these proofs will be long and fragile.

\---

\#\#\# 4\. Estimate (expert‑weeks)

I will be blunt: formalizing all of Schrijver’s §II from scratch in Mathlib is at least a \*\*4–6 month full‑time project\*\* for a skilled formalizer comfortable with combinatorial matrix algebra. Even with the “admit the theorem as one big lemma” strategy, the discharge effort will be that large.

\- \*\*First milestone (admitted lemma wired in):\*\* 1 week. This is just stating the \`schrijver\_block\_diag\` theorem with a \`sorry\` and connecting it to the existing F2a code.  
\- \*\*Second milestone (full proof):\*\* the remaining time. The work can be split into:  
  \- Proof of orthogonality of \`U\`: 3–4 weeks.  
  \- Block‑diagonalization of generators: 4–6 weeks.  
  \- General PSD congruence and block lemma: 2 weeks.  
\- Total estimate: \*\*5–6 months\*\* for an expert, possibly longer if the square‑roots force algebraic number reasoning. This is not a small side project; it is a major formalization effort comparable to the size of the original paper.

If you have access to a dedicated formalizer or can fund an internship, it is feasible but must be planned accordingly.

\---

\#\#\# 5\. Critique of the brief’s assumptions

\- “Admit this as one named, citation‑backed lemma first (it shrinks our informal trusted base to a single statement)” — this is correct, but the informal trusted base remains substantial: the entire statement of the theorem, which includes the definition of \`U\` and the block form. That statement is not trivial; an error in its formulation would be as damaging as an error in the proof, but the statement is checked by your computational oracle (\`beta\_oracle.tsv\`) for small \`n\`? You mentioned your kernel F1 checker recomputes eq. (7) inside Lean, but that is the \`β\` coefficients, not the full equivalence statement. You could \*\*validate the block‑diagonalization statement computationally\*\* for concrete \`n\` up to, say, 12 by computing the large matrix and its blocks and checking PSD equivalence using rational arithmetic (since for fixed n, the matrices are finite and the equivalence is a linear algebra statement over ℚ after clearing denominators). That would give a computational sanity check that the admitted lemma is indeed true, mitigating the risk of an incorrect axiom. I strongly recommend doing that for small n to gain confidence before formalizing.  
\- The brief says “the elementary proof path … minimizes Mathlib dependencies” — this is true, but it maximizes manual combinatorial work. An abstract representation‑theoretic proof using the action of the symmetric group might be shorter \*if\* Mathlib had semisimple algebra and the representation theory of S\_n, but it doesn’t. So elementary is the only realistic path.  
\- “What remains for a full bridge is exactly: codes ⇒ primal‑feasible” — that bridge is deep: it requires embedding the code into the Terwilliger algebra, showing that the distribution \`x\` derived from a code satisfies the constraints, and that the objective function equals the code size. That proof is independent of the block‑diagonalization but still substantial. The brief mentions it but does not ask for an estimate; be aware it could add another 1–2 months.

\---

\#\#\# 6\. Constructive suggestions

\- \*\*Pilot proof for a fixed n:\*\* Before attempting the generic \`n : ℕ\` proof, formalize a proof for a specific small \`n\` (say \`n \= 6\`) by brute force using \`dec\_trivial\`? Not possible for size 2^6=64? Actually, 64x64 matrices are small; you could verify the statement for \`n \= 6\` by explicit computation in Lean using \`dec\_trivial\` if you convert the matrix entries to \`ℚ\` and use a decision procedure for linear arithmetic. That would give a concrete, fully verified instance and help iron out the definitions without tackling the generic proof. It would also serve as a test case for the downstream pipeline.  
\- \*\*Leverage your computational oracle for the formal proof:\*\* Since your F1 checker already computes the \`β\` coefficients correctly inside Lean, you could use that computational witness in the proof. For example, the block‑diagonalization proof might be structured as: show that the transformed matrix has a specific form, and then use the already‑verified \`β\` computation to assert that the form matches \`Mblock\`. This doesn’t avoid the core sum manipulations, but it ensures that the final block entries are correct by computation, reducing the chance of a transcription error.  
\- \*\*Seek collaboration:\*\* This is a textbook‑sized formalization; consider reaching out to the Mathlib community with a funded project or a dedicated PhD student.

\---

\#\#\# 7\. Honest bottom line

The formalization plan is valid, but the scope is severely underestimated in the brief. Theorem 1 is not a single isolated lemma—it is the heart of the paper. Realistic effort: 5–6 expert‑months. The admission strategy is fine, but downstream discharge will be a major project, not a quick follow‑up. Before committing, run a computational validation of the theorem for small \`n\` to ensure the statement is correct and to refine the definitions. That will also give you a concrete, fully verified instance that can serve as a regression test for the generic proof.

\*\*Recommendation:\*\* Admit the theorem now (1 week) to unblock kernel integration; then plan a multi‑month formalization project with dedicated resources; do not expect to discharge the \`sorry\` soon. That is the honest assessment.

# Kimi:Latest

\*\*This is an adversarial review. Formalizing Theorem 1 is the right technical move for your locked audit-tier certificates, but your “admit first” framing inverts the trust model: you are proposing to expand the trusted base to a single, monolithic, citation-backed axiom that is \*larger\* and more error-prone than the multi-checker pipeline it replaces. The elementary route is viable but the combinatorial identity wall is higher than you estimate.\*\*

\---

\#\# 1\. Attack the premise: is this the right formalization target?

\*\*The honest ROI.\*\* You have three certificates (A(19,6), A(23,6), A(25,10)) stuck in audit tier. Formalizing Theorem 1 converts them to kernel tier. That is a real but \*bounded\* win: three bounds, already known, already verified by your exact legs, now with a Mathlib proof certificate. The cost is 6–10 weeks of formalization work on a dense combinatorial identity. 

\*\*The alternative cost.\*\* Those same engineer-weeks spent on horizontal infrastructure (e.g., a generic SDP-to-Lean certificate importer, or a second finite-witness domain) produce compounding value. Spent on Schrijver’s Theorem 1, they produce a \*sunk\* artifact: a one-off proof about the Terwilliger algebra of H(n,2) that no other domain reuses. 

\*\*What changes my mind:\*\* If you can prove the \*\*forward direction only\*\* (code-derived \`R(x)\` is Gram → blocks are PSD), the scope shrinks dramatically and the ROI improves. You do \*\*not\*\* need the full iff for the bound proof. The reverse direction (blocks PSD → \`R(x)\` PSD) is only needed if you want to prove \*strong duality\* or to verify primal certificates, neither of which your current pipeline uses. I suspect you included the iff because Schrijver states it, but your F2a weak-duality bridge only needs: “for any code \`C\`, the inner distribution \`x\_C\` is primal feasible.” That requires \`R(x\_C)\` PSD and \`R'(x\_C)\` PSD (Prop 1), plus the forward block implication. 

\*\*Recommendation:\*\* Scope the target to \*\*Theorem 1-forward \+ Prop 1\*\*. Drop the reverse direction from the milestone. This is not a minor optimization; it removes the need to prove that an \*arbitrary\* collection of PSD blocks assembles into a PSD full-matrix, which is the harder algebraic half.

\---

\#\# 2\. Gap analysis: Mathlib today

| Component | Status in Mathlib 4 (≈ July 2026\) | Gap |  
|---|---|---|  
| \`Matrix\`, \`Matrix.blockDiagonal\`, \`Matrix.fromBlocks\` | \*\*Exists\*\* | None |  
| \`Matrix.PosSemidef\`, congruence invariance | \*\*Exists\*\* (\`PosSemidef\_congr\`) | None for 2×2 blocks; n-block generalization of \`blockDiagonal\_posSemidef\` likely requires an induction lemma you must prove |  
| \`Nat.choose\`, \`Finset.sum\`, binomial identities | \*\*Exists\*\* | None for basic sums; the \*specific\* triple sums of signed binomial products in U’s orthogonality are \*\*not present\*\* |  
| Orthogonal/unitary matrices over ℝ/ℚ | \*\*Exists\*\* (\`Matrix.Orthogonal\`) | None |  
| Krawtchouk/Hahn orthogonal polynomials | \*\*Absent\*\* | Must build from scratch or avoid |  
| Hyperoctahedral group \`C\_2 ≀ S\_n\`, its representation theory, Gelfand pairs | \*\*Absent\*\* | The abstract route is blocked |  
| Computational reflection for 2^n×2^n symbolic matrices | \*\*Impractical\*\* | n=19 gives 524k index space; you cannot compute dense entries |

\*\*Verdict:\*\* Only the elementary route is open. The representation-theoretic shortcut (prove the algebra is semisimple by character theory, read off the blocks) requires building the character table of the hyperoctahedral group from scratch—far harder than the elementary proof.

\---

\#\# 3\. Lemma decomposition and risk ranking

I assume the \*\*forward-only\*\* scope. The lemma tree:

\`\`\`  
schrijver\_bound (n d : ℕ) (C : Code n d) : |C| ≤ bound n d  
├── weak\_duality (F2a, already built)  
│   └── requires: primal\_feasible n d x\_C  
│       └── requires: prop1\_R\_psd n x\_C  
│       │   └── R\_matrix n x\_C \= Gram matrix of χ\_C-related vectors  
│       │       └── \[combinatorial definition, medium\]  
│       └── requires: prop1\_R'\_psd n x\_C  
│       │   └── \[same structure, medium\]  
│       └── theorem1\_forward n x\_C  
│           ├── U\_orthogonal n  
│           │   └── U\_transpose\_mul\_U n  
│           │       └── ∑\_X U\_X,α U\_X,β \= δ\_αβ  
│           │           └── \*\*\*RISKIEST\*\*\* combinatorial identity  
│           ├── block\_diag\_conjugation n (t i j)  
│           │   └── ∀ k, (Uᵀ M^t\_{i,j} U) restricted to k-block \= β^t\_{i,j,k} I\_{q\_k} ⊗ J?   
│           │       └── Actually: the block is β^t\_{i,j,k} times something  
│           │       └── \*\*\*RISKIEST\*\*\* block vanishing / structural identity  
│           ├── beta\_formula\_correct n t i j k  
│           │   └── entry of block equals Σ\_u (-1)^{u-t} ...  
│           │       └── \*\*\*MEDIUM\*\*\* computational identity (testable against oracle)  
│           └── posSemidef\_of\_block\_diag n x  
│               └── (Uᵀ R U block diag with M\_k blocks) ∧ R PSD → each M\_k PSD  
│                   └── Low risk: follows from PosSemidef\_congr \+ blockDiag\_psd  
\`\`\`

\#\#\# The three riskiest lemmas

1\. \*\*\`U\_transpose\_mul\_U\` (orthogonality):\*\* A triple sum over subsets with signed binomial weights. The identity is “obvious” on paper because it counts pairs of subsets with given intersections, but in Lean it is a nightmare of \`Finset.sum\` over \`powerset\` with dependent type indices. Expect 2–4 weeks of \`Finset\` plumbing and binomial identity lemmas.  
2\. \*\*\`block\_diag\_conjugation\` (vanishing):\*\* Proving that \`Uᵀ M^t\_{i,j} U\` has no cross-block terms. This requires showing that basis vectors from different \`k\` are eigenvectors of every \`M^t\_{i,j}\` with different eigenvalues, or that the inner product structure respects the decomposition. The elementary proof constructs U so that this holds by design, but proving it is a nested induction on n or a Möbius-inversion argument.  
3\. \*\*\`prop1\_R\_psd\` (code Gram matrix):\*\* Schrijver’s Prop 1 states that for a code C, \`R(x\_C)\` is a Gram matrix. The vectors are explicit (characteristic functions of code elements restricted to subsets). Defining the matrix \`B\` (size 2^n × |C|) and proving \`R \= B B^T\` is medium-complexity but requires careful indexing. \*\*This is independent of Theorem 1 and can be built first.\*\*

\---

\#\# 4\. Staging, estimate, and gating

\*\*Stage 0: Scope reduction (3 days, gates everything)\*\*  
\- Redefine the target to \*\*forward direction only\*\*.  
\- Verify by pen-and-paper that the bound proof \`code → |C| ≤ dual\_bound\` uses only forward.  
\- If you discover you need reverse (e.g., for a primal certificate path you omitted), reassess.

\*\*Stage 1: End-to-end wiring with \`sorry\` (1 week)\*\*  
\- Define \`Theorem1Forward (n : ℕ) : ∀ x, IsCodeDerived x → PosSemidef (Rmatrix n x) → ∀ k, PosSemidef (Mblock n k x)\` admitted.  
\- Prove \`schrijver\_bound\` modulo this sorry and the F2a bridge.  
\- Compile the three certificates against this theorem. \*\*GREEN:\*\* All three compile end-to-end with exactly one \`sorry\`. \*\*RED:\*\* The wiring reveals a mismatch in \`IsTripleDistribution\` or the bound statement.

\*\*Stage 2: Prop 1 (2–3 weeks)\*\*  
\- Prove \`prop1\_R\_psd\` and \`prop1\_R'\_psd\`: for a code \`C\`, the matrices are Gram.  
\- This is a self-contained win and validates your \`Rmatrix\` definition.

\*\*Stage 3: The change of basis U (4–8 weeks, high variance)\*\*  
\- Sub-stage 3a (1 week): Define the index type for the block decomposition and prove \`Σ\_k q\_k \* p\_k \= 2^n\`.  
\- Sub-stage 3b (2–4 weeks): Define \`U\` and prove \`U\_orthogonal\`. This is where the project lives or dies.  
\- Sub-stage 3c (1–2 weeks): Prove \`block\_diag\_conjugation\` and \`beta\_formula\_correct\`.  
\- Sub-stage 3d (1 week): Assemble \`theorem1\_forward\`.

\*\*Probe for Stage 3b (the combinatorial wall):\*\*  
Before building the Lean proof, write a \*\*Python script\*\* that:  
1\. Defines \`U\_{X, (k,T,i)}\` following Schrijver’s §II for n=6,8,10.  
2\. Verifies \`U^T U \= I\` by exact rational arithmetic.  
3\. Verifies \`U^T M^t\_{i,j} U\` is block diagonal with entries matching the β oracle.

\*\*GREEN:\*\* Python confirms for n=10 in \<1 minute. \*\*RED:\*\* Python reveals a sign error or indexing mismatch in your reading of Schrijver. Fix in Python before touching Lean.

\---

\#\# 5\. The thing you are getting wrong

\*\*\`IsTripleDistribution x\` bundles too much, and you are not validating it against the code-derived distribution.\*\*

The brief says the lemma target is:  
\`\`\`lean  
lemma schrijver\_block\_diag (n : ℕ) (x : Triple n → ℚ) (hx : IsTripleDistribution x) :  
    PosSemidef (Rmatrix n x) ↔ ∀ k, PosSemidef (Mblock n k x)  
\`\`\`

But \`IsTripleDistribution\` must encode at minimum:  
\- Nonnegativity of \`x\` on valid triples  
\- \`x^0\_{0,0} \= 1\`  
\- The symmetry/orbit constraints (20)(iii)  
\- The distance-zeroing constraints (20)(iv)

If your predicate is too weak, you prove a theorem about matrices that do not correspond to codes. If it is too strong, you cannot prove that code-derived \`x\_C\` satisfies it. In particular, the symmetry constraints \`(20)(iii)\` (equality under permutation of the triple) are easy to state wrong. A single missed transposition in the permutation orbit means your \`x\` type has more free variables than the true code inner distribution, which weakens the SDP relaxation and invalidates the bound.

\*\*Guard:\*\* Before Stage 1, write a Lean tactic that \*computes\* \`x\_C\` for a small explicit code (e.g., the binary Golay code of length 23\) and proves it satisfies \`IsTripleDistribution\`. If this fails, your predicate is malformed.

\---

\#\# 6\. Prioritized recommendation

\*\*Reduce the target to Theorem 1-forward only; run the Python U-orthogonal probe for n=10 against the β oracle this week; if it greens, proceed to Stage 1 (wiring with sorry) immediately; if it reds, halt the formalization and keep the certificates audit-tier until a human formally verifies the block-diagonalization identity independently.\*\*

The full iff is mathematical luxury; the forward direction is what stands between your three certificates and the kernel. Do not gold-plate the theorem.

# GLM 5.2

This brief is a strong step toward bridging the trust gap, but it contains a fatal architectural flaw regarding how Lean handles matrix sizes, and a strategic misjudgment about the "elementary" proof path. If you send this brief as-is, you will likely get a reply from Mathlib experts telling you to rewrite the target statement, or you will spend months in index hell.

Here is the adversarial critique and concrete feedback.

\#\#\# 1\. The $2^n$ Matrix Trap (The Fatal Flaw in the Target Lemma)

Your proposed target lemma is:  
\`\`\`lean  
lemma schrijver\_block\_diag (n : ℕ) (x : Triple n → ℚ) (hx : IsTripleDistribution x) :  
    PosSemidef (Rmatrix n x) ↔ ∀ k, PosSemidef (Mblock n k x)  
\`\`\`

\*\*This statement is unformalizable for the $n$ you care about.\*\* \`Rmatrix n x\` is the $2^n \\times 2^n$ matrix in the ambient space $\\mathbb{R}^{2^n}$. For $n=19$, this is a $524,288 \\times 524,288$ matrix. Lean cannot even \*type-check\* a literal matrix of this size, let alone reason about it. The entire point of Schrijver's block diagonalization is that you \*never construct\* the ambient matrix; you work entirely in the $\\binom{n+3}{3}$-dimensional Terwilliger algebra.

\*\*The Fix:\*\* You must formulate the theorem algebraically, not representationally. The statement must be about the quadratic form or the Gram matrix of the \*algebra basis elements\* $M^t\_{i,j}$, not the $2^n$ space.

It should look more like:  
\`\`\`lean  
lemma schrijver\_block\_diag (n : ℕ) (x : Triple n → ℚ) :  
    (∀ v : Fin (binom n+3 3), 0 ≤ dotProduct (evalAlgebraMatrix n x v) v) ↔   
    ∀ k, PosSemidef (Mblock n k x)  
\`\`\`  
Or, even better, formulate it as a congruence of bilinear forms on the Terwilliger algebra. If you send the brief with the $2^n$ \`Rmatrix\`, the formalizers will immediately flag it as a non-starter.

\#\#\# 2\. The "Elementary Path" Trap

You state: \*"We explicitly prefer it \[the elementary path\] over abstract C\*-algebra/representation-theoretic machinery... unless the gap analysis shows the abstract route is genuinely shorter."\*

\*\*In Lean 4, the abstract route is almost always shorter for linear algebra.\*\*   
Schrijver's Props 2–5 involve explicit basis vectors, partitioned index sets, and messy combinatorial summations. Formalizing explicit matrix multiplication and index manipulations (the "elementary" path) in Lean is notoriously agonizing—it is "index hell." Mathlib has powerful automation (\`simps\`, \`linear\_combination\`, \`tensor\_product\` infrastructure) for \*abstract\* linear maps, but very weak automation for explicit matrix index arithmetic.

\*\*The Fix:\*\* Remove the prejudice against the abstract route. Tell the formalizers: \*"We want the fastest path to a sound isomorphism. If Mathlib's \`LinearEquiv\` / \`TensorProduct\` infrastructure makes the abstract route 10x faster than explicit basis manipulations, we prefer the abstract route."\* The abstract route \*is\* the standard modern mathematical proof; fighting the formalizer to use 2005's explicit basis vectors is a strategic mistake.

\#\#\# 3\. Premature Constraints on the Target Statement

Your proposed lemma includes \`(hx : IsTripleDistribution x)\` as a hypothesis. 

\*\*This is mathematically incorrect and unnecessarily weakens the lemma.\*\* Schrijver's Theorem 1 is a purely algebraic fact about the Terwilliger algebra: \*every\* element of the algebra block-diagonalizes this way, regardless of whether its coefficients $x^t\_{i,j}$ form a valid distance distribution. The \`IsTripleDistribution\` constraints (non-negativity, triangle inequalities) are only required later to prove that the matrices for codes are PSD (Prop 1 / R and R'). 

\*\*The Fix:\*\* Remove \`hx\` from the block diagonalization lemma. Keep the algebraic facts pure; apply the code-theoretic constraints later. This makes the lemma vastly more reusable and easier to prove.

\#\#\# 4\. Missing Multiplicities ($q\_k$)

Your target lemma says \`∀ k, PosSemidef (Mblock n k x)\`. 

This omits the multiplicities $q\_k \= \\binom{n}{k} \- \\binom{n}{k-1}$. Block $k$ appears with multiplicity $q\_k$ in the decomposition. While PSD-ness of one copy implies PSD-ness of all copies (so the $\\iff$ is technically true as stated), the \*trace\* (and therefore the objective function of your SDP) depends critically on the multiplicity. When you connect this lemma back to your weak duality and the SDP bound, you will need the multiplicities. 

\*\*The Fix:\*\* The statement should either reflect the direct sum $\\bigoplus\_k (M\_k \\otimes I\_{q\_k})$, or the formalizer must explicitly sign off that the multiplicity is handled downstream in the trace/objective lemma.

\#\#\# 5\. Critique of the Asks

\*   \*\*Ask 1 (Plan/Decomposition):\*\* Good, but you need to explicitly ask them to evaluate the \*algebraic vs. explicit\* trade-off for the first 3 lemmas.  
\*   \*\*Ask 2 (Gap Analysis):\*\* You missed a crucial Mathlib gap: \*\*Congruence of PSD via non-singular matrices\*\*. Schrijver's proof relies on $U^\\dagger M U \\ge 0 \\iff M \\ge 0$. Mathlib has \`PosSemidef.cong\`, but ensuring it works for the specific rectangular/singular change-of-basis used in the Terwilliger algebra (which collapses the $2^n$ space) is a known pain point. Ask them to scope this specifically.  
\*   \*\*Ask 3 (Estimate):\*\* Asking for "expert-weeks" is good, but you must define the milestone rigorously. "Admitted-lemma wiring compiling end-to-end" is vague. Define it as: "A \`sorry\`-free \`schrijver\_block\_diag\` lemma with the correct algebraic signature (no $2^n$ matrix), plus the \`sorry\`-free corollary that links it to the \`tw\_weak\_duality\` F2a file."

\#\#\# Recommended Rewrites before Sending

1\.  \*\*Rewrite the Target Lemma\*\* to remove the $2^n$ matrix and the \`IsTripleDistribution\` constraint. State it over the Terwilliger algebra's intrinsic basis.  
2\.  \*\*Soften the "Elementary Path" mandate\*\* to "whichever path Mathlib supports best; we suspect abstract linear maps are easier than explicit matrix indices."  
3\.  \*\*Explicitly flag the $2^n$ wall\*\* in the brief so the formalizers understand \*why\* the statement must be algebraic. (They will respect you more for it).

# Gemini 3.1 Pro Deep Thinking

Formalization Brief Critique: Schrijver’s Block-Diagonalization of the Terwilliger Algebra in Lean 4Executive Summary and The Paradigm Shift in Combinatorial VerificationThe integration of advanced mathematical structures into interactive theorem provers represents a transformative frontier in formal verification, particularly concerning algebraic combinatorics and coding theory bounds. The provided formalization brief outlines a highly ambitious, mathematically intricate, and structurally profound project: formalizing Alexander Schrijver’s block-diagonalization of the Terwilliger algebra within the Lean 4 proof assistant and the Mathlib ecosystem. The ultimate objective of the Leibniz theorem-daemon project is to establish machine-checked upper bounds for binary codes, specifically targeting the Hamming scheme $H(n,2)$. By mathematically bridging the gap between kernel-attested computational certificates generated by the F1 checker and the formal proofs situated in the F2 stage, the project aims to elevate currently existing audit-tier computational bounds into absolute, foundational mathematical proofs.This specific formalization endeavor unlocks the kernel-checked status for the bounds $A(19,6) \\le 1280$, $A(23,6) \\le 13766$, and $A(25,10) \\le 503$. The transition from empirical, solver-based confidence to kernel-verified certainty is not merely a computational exercise; it is a fundamental shift in mathematical epistemology. For decades, bounds in coding theory have relied on floating-point solvers and complex semidefinite programming (SDP) implementations whose internal execution traces were too vast for human auditing. The Leibniz project architecture decouples the generation of the witness from its verification, relying on the principle that while large language models or heuristic SDP solvers may propose the structure of the proof, only the Lean kernel—operating on an undeniably minimal foundational logic—decides its ultimate validity.The formalization brief appropriately designates the central mathematical target as "Theorem 1" derived from Schrijver's 2005 seminal paper. This theorem asserts that a matrix existing within the Terwilliger algebra of the Hamming cube is Positive Semidefinite (PSD) if and only if each of its block-diagonal components, designated as $M\_k$, is independently Positive Semidefinite. This comprehensive critique evaluates the provided brief by delivering a mathematically rigorous lemma-level decomposition, an exhaustive Mathlib gap analysis spanning current type-theoretic constraints, and a phased strategic estimation. The analysis ultimately confirms that the project's strategic preference for an "elementary route"—utilizing explicit orthonormal basis changes and finite combinatorics over abstract representation-theoretic machinery—is optimally aligned with the current architectural maturity of the Mathlib library.The Mathematical Landscape: From Delsarte LP to Schrijver SDPTo fully evaluate the proposed Lean 4 implementation and appreciate the gravity of the formalization brief, it is essential to trace the mathematical lineage of the target theorem and its role in modern coding theory. The primary metric of interest in this domain is $A(n,d)$, defined as the maximum possible cardinality of a binary code of word length $n$ with a minimum Hamming distance of at least $d$ between any two distinct codewords. Historically, the pursuit of bounding $A(n,d)$ was heavily constrained by the linear programming (LP) framework pioneered by Philippe Delsarte in the 1970s.The Delsarte bound leverages the regular association scheme of the Hamming cube. In this classical LP approach, the distance distribution of a code—a vector detailing the number of pairs of codewords at each possible distance—is constrained by the requirement that its MacWilliams transform (its projection onto the eigenspaces of the association scheme) must yield non-negative coefficients. While revolutionary, the Delsarte bound inherently limits its analysis to pairs of codewords. It discards deeper structural constraints regarding how triplets, quadruplets, or larger subsets of codewords geometrically interact within the high-dimensional Hamming space.Schrijver’s 2005 intervention profoundly advanced this discipline by expanding the analytical resolution from pairs to triples of codewords. By analyzing the triple distribution—quantifying the occurrences of codeword triplets $(X,Y,Z)$ possessing specific mutual intersection distances—Schrijver formulated the bounding problem not as a linear program, but as a semidefinite program (SDP). Semidefinite programming optimizes a linear objective function over the intersection of the cone of positive semidefinite matrices with an affine space, offering a strictly more expressive geometric framework than the polyhedral cones utilized in linear programming.However, representing the relationships between all subsets of the Hamming cube $H(n,2)$ natively requires operating on matrices of dimension $2^n \\times 2^n$. Checking the positive semidefiniteness of such matrices is computationally intractable for any cryptographically or practically relevant value of $n$. Schrijver circumvented this exponential wall by recognizing that the matrices generated by the triple distributions belong to the Terwilliger algebra $A\_n$ of the Hamming scheme. The Terwilliger algebra is a highly symmetric, finite-dimensional sub-algebra. By proving that this specific algebra can be analytically block-diagonalized, Schrijver demonstrated that the PSD condition of the massive $2^n \\times 2^n$ matrix is mathematically equivalent to the PSD condition of a highly restricted set of smaller block matrices, the largest of which grows only polynomially with $n$. This dimensionality reduction is the exact theoretical mechanism that enables the numerical computation of the bounds $A(19,6) \\le 1280$ and $A(25,10) \\le 503$, and it is the mechanism that the Leibniz project now seeks to formally verify in Lean 4.Algebraic Structure of the Terwilliger AlgebraThe formalization of the block-diagonalization theorem requires a robust encoding of the Terwilliger algebra's precise algebraic structure into Mathlib’s type system. The Terwilliger algebra $A\_n$, introduced by Paul Terwilliger in the context of distance-regular graphs and association schemes, is formed by the complex matrices whose rows and columns are indexed by the subsets of $\\{1, \\dots, n\\}$.For the Hamming cube $H(n,2)$, the basis matrices $M^t\_{i,j}$ of the Terwilliger algebra are defined such that the entry at row $X$ and column $Y$ is strictly determined by three cardinalities: the size of the set $X$ (denoted $i$), the size of the set $Y$ (denoted $j$), and the size of their intersection $X \\cap Y$ (denoted $t$). Because these matrices are invariant under the permutation of the underlying ground set, they capture the deep symmetry of the Hamming scheme. Schrijver established that the dimension of this algebra, denoted $\\dim A\_n$, is exactly $\\binom{n+3}{3}$. This polynomial dimensionality is the first indicator that the algebra can be computationally tamed.To map this to a formal proof environment, one must construct the variable set representing the triple distribution. The variables are denoted $x^t\_{i,j}$. These variables are directly derived from $\\lambda^t\_{i,j}$, which Schrijver defines as the number of triples $(X,Y,Z)$ in the code such that the symmetric differences satisfy $|X \\Delta Y| \= i$, $|X \\Delta Z| \= j$, and the intersection of these differences satisfies $|(X \\Delta Y) \\cap (X \\Delta Z)| \= t$. The primal matrix $R$, constructed in the target lemma's formulation, is built by summing these basic matrices weighted by the triple distribution variables:  
$$R \= \\sum\_{i,j,t} x^t\_{i,j} M^t\_{i,j}$$  
A structurally similar matrix $R'$ is constructed to account for the subsets that are not in the code. The central mathematical claim is that because $R$ and $R'$ are constructed as sums of outer products of non-negative incidence vectors derived from the code, they are intrinsically positive semidefinite. The formalization of this specific algebraic structure—translating the definition of $M^t\_{i,j}$ into Lean's Matrix type and establishing the closure of the algebra under multiplication—forms the critical preparatory phase for the block-diagonalization proof.Dissecting the Block-Diagonalization Theorem (Theorem 1)The formalization brief identifies Theorem 1 from Schrijver (2005) as the ultimate target, specifically isolating equations (7) and (8). Theorem 1 asserts that the algebra $A\_n$ is isomorphic to a direct sum of matrix blocks. Under this isomorphism, any matrix within the Terwilliger algebra is mapped to a block-diagonal matrix where the PSD property is preserved across the mapping.The mathematical structure of this decomposition is defined as follows:$$\\bigoplus\_{k=0}^{\\lfloor n/2 \\rfloor} \\mathbb{C}^{N\_k \\times N\_k}$$  
where the index set for the $k$-th block is given by $N\_k := \\{k, k+1, \\dots, n-k\\}$. Consequently, the $k$-th block possesses a dimensionality of $(n-2k+1) \\times (n-2k+1)$. The mapping of the original matrix entries $x^t\_{i,j}$ into these blocks is governed by a specific coefficient formula, designated as $\\beta^t\_{i,j,k}$.The exact formula for $\\beta^t\_{i,j,k}$, evaluated for indices $i, j, k, t \\in \\{0, \\dots, n\\}$, is defined in Schrijver's Section I-A (Equation 7\) as:$$\\beta^t\_{i,j,k} := \\sum\_{u=0}^{n} (-1)^{u-t} \\binom{u}{t} \\binom{n-2k}{u-k} \\binom{n-k-u}{i-u} \\binom{n-k-u}{j-u}$$This single equation is the most critical computational vertex in the entire formalization.\[1, 2\] It describes exactly how the variables of the SDP are linearly combined to populate the entries of the reduced block matrices. The matrix block $M\_k$ is then populated by elements that are scaled sums of these beta coefficients. Specifically, the entry at index $(i,j)$ in the $k$-th block is given by:$$\\sum\_{t} \\binom{n-2k}{i-k}^{-1/2} \\binom{n-2k}{j-k}^{-1/2} \\beta^t\_{i,j,k} x^t\_{i,j}$$  
Validating this exact transformation natively within the Lean kernel ensures that the numerical SDP solver outputs—which are generated using floating-point approximations of these exact values—can be rounded, certified as rigorous rational proofs, and integrated into the logical foundation without trusting the external solver's arithmetic.The Target Lemma Definition and Type-Theoretic NuancesThe brief proposes admitting a centralized lemma to serve as the structural anchor for the formalization architecture. This is presented as:Leanlemma schrijver\_block\_diag (n : ℕ) (x : Triple n → ℚ) (hx : IsTripleDistribution x) :  
    PosSemidef (Rmatrix n x) ↔ ∀ k, PosSemidef (Mblock n k x)  
This lemma signature is an exceptionally accurate capture of the equivalence relation, mapping the macroscopic positive semidefiniteness of the primal matrix Rmatrix to the localized PSD state of the blocks Mblock. The formulation reveals several deep type-theoretic and semantic nuances that validate its robustness for the Mathlib ecosystem.Type-Theoretic FeatureImplication for FormalizationJustification within Lean 4 / MathlibUse of the Rational Field ($\\mathbb{Q}$)Circumvents undecidability of real equality and floating-point approximations.Mathlib's PosSemidef requires a and a. $\\mathbb{Q}$ satisfies both perfectly with a trivial star-involution.Predicate IsTripleDistributionEncapsulates the combinatorial validity of the input variables, isolating graph theory from linear algebra.Prevents the lemma from needing to assert universal matrix truth, restricting it only to those matrices structurally generated by valid code distances.Universal Quantification over Blocks∀ k, PosSemidef (Mblock n k x) elegantly replaces the need for a monolithic block-diagonal matrix type in the final top-level statement.Avoids the type-theoretic overhead of dependent block dimensions at the boundary of the theorem, keeping the interface clean for the F2a weak duality proofs.The Top-Level Admit StrategyAllows parallelized development. The F1 kernel check can be fully wired against the admitted lemma immediately.Highly preferred in large-scale formalizations. It isolates the dense linear algebra proofs from the combinatorial execution.By deploying the rational numbers ($\\mathbb{Q}$), the formalization sidesteps the complex analytical machinery required for the real numbers ($\\mathbb{R}$) or complex numbers ($\\mathbb{C}$). While the theoretical literature discusses the algebra over $\\mathbb{C}$, the symmetric nature of the distance matrices means all eigenvalues are real, and the basis transformation operates entirely within the real domain. Furthermore, by scaling the transformation carefully, all operations can be kept strictly within the rational field, aligning perfectly with Lean's computational strengths.The F1-to-F2 Bridge and the Power of Weak DualityThe formalization brief dictates that this theorem does not exist in a vacuum; it acts as the final logical bridge connecting the F1 kernel computations to the F2a weak duality formalizations. The F2a stage has already successfully formalized weak duality with zero sorry statements, defining gram\_pairing\_nonneg and tw\_weak\_duality inside scripts/terwilliger\_f2a.py.Weak duality in semidefinite programming asserts that if the primal problem (derived from the code) yields a PSD matrix, and the dual problem (the SDP solver's output witness) yields a PSD matrix, their inner product must be non-negative. This non-negativity mathematically enforces the upper bound on the objective function, which in this case is the cardinality of the code $A(n,d)$.In the Lean 4 environment, positive semidefiniteness is governed by the definition in Mathlib.Analysis.Matrix.Order, which states that a finite matrix $M$ is positive semidefinite if and only if it is Hermitian and the quadratic form is non-negative for all vectors:  
M.PosSemidef ↔ M.IsHermitian ∧ ∀ (x : n → R), 0 ≤ star x ⬝ᵥ M.mulVec x.The F2a stage represents the dual PSD-ness via an LDLT (or Gram) witness form. An LDLT factorization ($M \= L D L^T$ where $D$ is a diagonal matrix with non-negative entries) acts as a direct algebraic witness to the non-negativity of the quadratic form. Because the F2a script already successfully links this witness to the general duality bound, the only missing component is proving that the primal matrices $R$ and $R'$, originating from a valid code, are inherently PSD, and that checking their block-diagonal reductions is logically sufficient. schrijver\_block\_diag provides exactly this logical sufficiency.Strategic Route Selection: Elementary Method vs. Abstract MachineryA pivotal directive explicitly stated in the formalization brief is the absolute preference for Schrijver's "elementary route" (Section II of the 2005 paper) over abstract representation-theoretic frameworks. The brief specifically warns against deploying $C^\*$-algebras, representation-theoretic frameworks, symmetric group wreath actions ($S\_n \\wr S\_2$), or Specht modules unless a rigorous gap analysis proves them necessary. This directive demonstrates an extraordinarily nuanced understanding of the current operational state of the Lean 4 Mathlib library.Abstract approaches to decomposing the Terwilliger algebra rely heavily on algebraic representation theory. They view the matrices as centralizer algebras of the action of the automorphism group of the Hamming scheme on the space of complex functions. While Mathlib possesses a rapidly evolving and impressive representation theory architecture for finite groups—including Schur's lemma, Maschke's theorem, irreducible representations, and character orthogonality —its formalized coverage of general association schemes and their subconstituent algebras remains highly nascent. Recent conference proceedings indicate that while efforts have begun mapping finite groups to thin association schemes in Lean, the library is currently bereft of the deep algebraic infrastructure required to systematically and automatically decompose the Terwilliger algebra via generalized representation theory modules. The lack of comprehensive, ready-to-use theorems for distance-regular graphs and Q-polynomial properties in Mathlib  means the abstract route would demand months of foundational library building before even approaching the specific coding theory bounds.Conversely, Schrijver's elementary route is grounded entirely in explicit matrix constructions, hard-coded orthonormal basis changes, and finite combinatorial summations. This elementary path maps flawlessly onto Mathlib's most robust, battle-tested domains. Mathlib’s Matrix API is exceptionally mature, complete with dot products, transposes, block manipulations, and congruence theorems. Furthermore, the Finset API and big\_operators provide massive infrastructural support for summations over finite ranges. Therefore, selecting the elementary route is not merely an aesthetic preference; it is a critical strategic prerequisite for ensuring the viability and timely completion of the project.Lemma-by-Lemma Formalization Strategy (Schrijver Section II)To successfully execute the elementary proof within Lean 4, Theorem 1 must be systematically decomposed into a sequence of verifiable lemmas corresponding to Schrijver's Propositions 1 through 5\. Below is the detailed mathematical translation and Lean 4 implementation strategy for each core component, directly addressing the brief's requirement for a lemma-level breakdown.Phase 1: Formulating the Beta Coefficients and Equation (7)The coefficient $\\beta^t\_{i,j,k}$ is the heart of the transformation. It must be formalized with acute attention to the behavior of natural number subtraction in Lean's type system. In Lean, natural number subtraction (Nat.sub) truncates at zero (e.g., $3 \- 5 \= 0$). While this often causes friction in algebraic manipulations, it acts as a highly advantageous annihilator here.The brief explicitly validates the convention that binomial coefficients $C(a, b)$ are zero outside of the range $0 \\le b \\le a$. Mathlib's implementation of the binomial coefficient, Nat.choose, flawlessly mirrors this mathematical reality. Recent extensive work in Mathlib on combinatorial identities, such as the formalization of Wolstenholme's theorem, demonstrates that Nat.choose is supported by a rich set of automated simplification lemmas and ring tactics capable of handling deep integer arithmetic seamlessly.The sum over $u$ in Equation (7) ranges from $0$ to $n$. The alternating sign $(-1)^{u-t}$ requires casting the evaluation out of Nat and into ℤ or ℚ. The optimal Lean formulation will map the index u over Finset.range (n \+ 1). Inside the sum, the expression will multiply ((-1 : ℚ) ^ (u \- t)) by the rational-cast product of the four Nat.choose operations. Because Nat.choose naturally truncates to zero when the bounds $k \\le u \\le n-k$ are violated, there is absolutely no need to encode complex, dependently typed index bounds on the sum itself. The truncation naturally annihilates invalid terms, drastically reducing the proof obligations required to satisfy the simplifier tactic (simp).Phase 2: Proposition 1 (Averaged Outer Products)Proposition 1 establishes the mathematical reality that the matrices $R$ and $R'$ are constructed as linear combinations of the basis matrices $M^t\_{i,j}$, weighted exactly by the triple distribution variables $\\lambda^t\_{i,j}$.  
In Lean, this lemma serves as the structural bridge linking the combinatorial geometry of the code to the linear algebra of the matrices. Because weak duality is already achieved, the existence of a Gram matrix witness guarantees positive semidefiniteness via the condition 0 ≤ star x ⬝ᵥ M.mulVec x. The formalization must simply prove that $R$ equates to the sum of vector outer products of incidence vectors across the code's distance sets. Once $R$ is expressed as a Gram matrix, Matrix.PosSemidef applies by definition. This resolves the brief's requirement to prove "$R/R'$ PSD via averaged outer products".Phase 3: Proposition 2 (Matrix Rank and Dependencies)Proposition 2 calculates the rank of specific sub-matrices, notably proving that $M^{k-1}\_{k-1, k}$ has rank $\\binom{n}{k-1}$. The proof relies on a recursive algebraic relation:  
$$M^{k-1}\_{k-1,k}M^{k-1}\_{k,k-1} \= M^{k-2}\_{k-1,k-2}M^{k-2}\_{k-2,k-1} \+ (n \- 2k \+ 2)M^{k-1}\_{k-1,k-1}$$  
In Lean, verifying this proposition relies entirely on matrix multiplication (Matrix.mul\_apply) and induction over $k$. Because Mathlib lacks comprehensive automated theorems for matrix ranks dependent on arbitrary recursive block structures , this proposition must be proved manually by explicitly demonstrating the linear independence of the basis subsets generated by the intersections.Phase 4: Proposition 4 (Constructing the Orthonormal Basis)Proposition 4 is the pivot point of the block-diagonalization. It defines the vectors $u\_{k,b,i} := \\binom{n-2k}{i-k}^{-1/2} M^k\_{i,k}b$, asserting that they form an orthonormal basis for the space $\\mathbb{R}^P$. To formalize this, one must construct the transformation matrix $U$ from these vectors.The requirement of a square root term $\\dots^{-1/2}$ poses a significant type-theoretic challenge. The project explicitly seeks to operate strictly within the rational field $\\mathbb{Q}$ to preserve the exactness of the F1 kernel checker. Irrational roots are impermissible in this setup. The mathematical mitigation strategy—and a crucial insight for the formalizers—is to define an un-normalized, orthogonal (but not orthonormal) basis in Lean. By scaling the basis vectors by the binomial coefficient itself, the formalization clears the denominators. The resulting transformed blocks will be congruent to Schrijver's blocks up to a strictly positive rational diagonal scaling matrix. Because multiplying a matrix by a positive diagonal matrix perfectly preserves the PSD property, the overarching equivalence of Theorem 1 remains mathematically identical, completely bypassing the need for $\\mathbb{R}$ or irrational extensions.Phase 5: Proposition 5 (The Block-Diagonal Transformation)Proposition 5 represents the mathematical climax of the elementary route. It proves that applying the congruence transformation $U^T M^t\_{i,j} U$ yields the transformed matrix $\\tilde{M}^t\_{i,j}$. Crucially, this transformed matrix acts like a multidimensional Kronecker delta: it is exactly zero everywhere except when $l \= k$, $i \= i\_0$, $j \= j\_0$, and the basis vectors align ($b \= c$). When these strict conditions are met, the entry collapses into exactly the target $\\beta^t\_{i,j,k}$ equation.  
The Lean strategy for Proposition 5 will rely heavily on matrix entry computation theorems. The global sum collapses into the specific $\\beta$ terms using the orthogonality guarantees mathematically derived in Proposition 4.Mathlib Gap Analysis and Resolving Type-Theoretic FrictionsA comprehensive gap analysis reveals that Mathlib is exceptionally well-equipped for the fundamental algebraic manipulations required, though bespoke API scaffolding will be heavily needed for the dependent block matrices and index wrangling.Mathematical ConceptMathlib Status & LocationImplementation ComplexityArchitectural NotesPositive SemidefinitenessAvailable in Mathlib.Analysis.Matrix.Order via Matrix.PosSemidef.LowFully defined over generic ordered star rings. Flawlessly supports $\\mathbb{Q}$ without requiring complex field extensions.PSD Congruence InvarianceAvailable via Matrix.PosSemidef.conjTranspose\_mul\_mul\_same.Zero (Already Solved)Directly satisfies the explicit bridge requirement requested in the brief.Block Diagonal MatricesAvailable via Matrix.blockDiagonal and Matrix.blockDiagonal'.MediumblockDiagonal' must be used to support the dependently typed dimensions of the shrinking $M\_k$ blocks.Combinatorial Sums & BinomialsNat.choose, Finset.sum, big\_operators.LowSubtraction truncation naturally zeroes out invalid index ranges, perfectly aligning with equation (7).Weak Duality via Gram WitnessFully verified in project F2a via gram\_pairing\_nonneg.Zero (Integration Point)The existing LDLT/Gram witness satisfies the quadratic form condition of PosSemidef.Jordan Normal FormsOnly Jordan-Chevalley-Dunford exists; strict Jordan chains are absent.N/AMathematically irrelevant for Schrijver's elementary route, heavily vindicating the decision to avoid abstract machinery.Resolving PSD Congruence InvarianceThe formalization brief explicitly lists "PSD congruence invariance" as one of the critical remaining bridge requirements. The analysis reveals that this is, fortunately, already a fully solved problem within the Mathlib4 ecosystem. The library file Mathlib/LinearAlgebra/Matrix/PosDef.html contains the exact theorem required :Leantheorem Matrix.PosSemidef.conjTranspose\_mul\_mul\_same {A : Matrix n n R}   
  (hA : A.PosSemidef) (B : Matrix n m R) : (B.conjTranspose \* A \* B).PosSemidef  
Since the basis change matrix $U$ utilized in Schrijver's proof is orthogonal over the real domain (and constructed systematically to be real-symmetric in its mappings), the conjugate transpose $U^H$ is identical to the standard transpose $U^T$. Thus, this exact theorem can be applied verbatim to deduce that if the primal matrix is PSD, the block-diagonalized matrix resulting from the $U$ congruence transformation is identically PSD. This reduces a potentially massive proof obligation down to a single tactical application.Managing Dependent Block DimensionsThe most profound type-theoretic friction in this project involves index wrangling across dependent matrix blocks. The Terwilliger algebra $A\_n$ decomposes into blocks $M\_k$ where $k$ ranges from $0$ to $\\lfloor n/2 \\rfloor$. The structural challenge is that the size of block $M\_k$ is dynamically determined by $k$, specifically sized at $(n-2k+1) \\times (n-2k+1)$.Because the index sets map from homogeneously typed vectors (a flat index space of $2^n$) into dependently typed vectors spanning varying block sizes, the standard Mathlib function Matrix.blockDiagonal will result in fatal type unification errors, as it strictly assumes homogeneously sized blocks Matrix (m × o) (n × o) α. The formalizers must rigorously employ Matrix.blockDiagonal' (note the prime notation), which natively supports collections of matrices with varying dimensionality across the index parameter. Constructing the precise bijection between the flat index Fin (2^n) and the dependently typed sum of block indices will constitute the highest engineering risk in the codebase. The formalization must prioritize the creation of an isolated, robust index-mapping API. If index casting lemmas are mixed indiscriminately into the main matrix multiplication proofs, the simp tactic will rapidly fail to unify terms, resulting in intractable goal states.Fulfilling the Five F1-to-F2 Bridge RequirementsThe formalization brief explicitly requests the resolution of five remaining requirements to finalize the F1-to-F2 bridge. Based on the deep mathematical analysis, here is the strategic resolution for each:Proving Theorem 1 (Schrijver Block Diagonalization): Accomplished via the sequential, manual proving of Propositions 4 and 5, culminating in the application of Matrix.blockDiagonal' and the scaling out of irrational square roots to maintain exact $\\mathbb{Q}$ operations.Proving $R/R'$ PSD via averaged outer products: The Gram matrix framework natively satisfies 0 ≤ star x ⬝ᵥ M.mulVec x. By structurally defining $R$ as the sum of vector outer products across the code distance sets in Lean, the PSD nature is an automatic mathematical consequence requiring no deep matrix calculus.Proposition 1: This requires proving the coefficient identity mathematically linking $\\lambda^t\_{i,j}$ to the matrices $R$ and $R'$. This is fundamentally a pure combinatorial counting lemma. It relies on the geometric properties of intersections within the Hamming scheme. Because it does not require deep linear algebra, it can be proven independently using standard Finset inclusion-exclusion principles, isolating it from the matrix representation theories.PSD Congruence Invariance: Solved natively by Mathlib via Matrix.PosSemidef.conjTranspose\_mul\_mul\_same , requiring only straightforward instantiation.Proving Equation (21) — $|C| \= \\sum C(n,i) x^0\_{i,0}$: This formula concisely expresses the cardinality of the binary code $|C|$ entirely in terms of the primary triple distribution variables. It is an immediate, algebraic consequence of evaluating the definitions of the distributions over the trivial intersection (zero distance). It requires standard combinatorial simplifications utilizing Nat.choose identities.Effort Estimation and Phased Implementation StrategyThe formalization brief explicitly requests an estimate of the required effort, measured in expert-weeks, staged to show how the project reaches end-to-end compilation against the F2a statements. Because the F1 kernel already recomputes Equation (7) independently and valid instances of $\\beta$ are generated computationally via the terwilliger\_beta\_oracle.tsv , the Lean formalization can extensively leverage external file I/O or metaprogramming to test intermediate definitions natively. This capability significantly accelerates debugging by instantly highlighting mathematical mismatches between the Python/C++ F1 checker and the Lean 4 matrix definitions.The effort is estimated based on the performance of an expert Lean 4 mathematician highly familiar with Mathlib.LinearAlgebra, Mathlib.Data.Matrix, and dependent type theory.Development PhaseCore Task BreakdownFoundational DependenciesEstimated EffortPhase 1: API FoundationDefine the dependently typed block index sets N\_k. Implement the rational, un-normalized $\\beta$ coefficients. Define the global algebra matrices and the block matrices in ℚ.None1.5 Expert-WeeksPhase 2: Target Admit & Bridge VerificationState schrijver\_block\_diag as sorry. Formally connect this admitted lemma to the F2a weak duality proofs. Validate end-to-end compilation with existing F1 oracle data.Phase 11.0 Expert-WeeksPhase 3: Combinatorial CountingFormalize Proposition 1 and Equation (21). Prove the outer product equivalence mapping the counting identities to Gram matrices.Phase 22.0 Expert-WeeksPhase 4: Matrix Orthogonality & Basis DefinitionFormalize Proposition 4\. Define the un-normalized basis vectors. Prove mutual orthogonality manually via Matrix.dotProduct over the custom index API.Phase 12.5 Expert-WeeksPhase 5: Block Congruence ValidationFormalize Proposition 5\. Execute the basis transformation mathematically. Prove equivalence between the transformed global matrix and the dependently-sized block diagonal structure mapping to the $\\beta$ equation.Phase 43.0 Expert-WeeksPhase 6: Final Integration & DischargeDischarge the sorry on schrijver\_block\_diag utilizing Matrix.PosSemidef.conjTranspose\_mul\_mul\_same  and integrating the structural results of Phase 5.Phase 2, 3, 51.0 Expert-WeeksTotal Estimated Effort11.0 Expert-WeeksThe Leibniz theorem-daemon project’s formalization brief for Schrijver's block-diagonalization of the Terwilliger algebra represents a highly feasible, rigorously defined, and immensely impactful endeavor in the realm of automated mathematics. The decisive strategic directive to bypass abstract representation-theoretic formalizations in favor of an elementary, basis-transformation approach is the single most critical factor that makes this project viable under the current architectural constraints of Lean 4’s Mathlib.The comprehensive gap analysis explicitly demonstrates that Mathlib already provides the most structurally complex algebraic requirements—specifically the PSD congruence invariance theorems and dependently-sized block matrix constructions. The primary technical friction will originate strictly from the dependent typing of combinatorial sub-range indices and the vital necessity to avoid irrational square roots in basis normalization. By intelligently shifting to an orthogonal, non-normalized basis to strictly preserve exact rational arithmetic ($\\mathbb{Q}$), the formalization can flawlessly interface with the preexisting F1 kernel checker. This meticulously staged, 11-expert-week approach directly unlocks the verification of the coding upper bounds for $A(19,6)$, $A(23,6)$, and $A(25,10)$, successfully finalizing their transition from audit-tier heuristic computations into fully realized, foundational mathematical proofs.

# Qwen 3.7 Max

\*\*1. Attack the Premise: The "Elementary" Trap and Direct PSD\*\*  
Your preference for Schrijver’s §II "elementary" proof over representation theory is a classic formalization anti-pattern. You are optimizing for "minimizing Mathlib dependencies" by choosing explicit combinatorial constructions, but in Lean, this trades abstract algebraic machinery for grueling, low-level "matrix index hell." Schrijver’s explicit orthogonal matrix $U$ is built from Hahn polynomials, and proving $U^T M U \= \\bigoplus M\_k$ requires grinding through their recurrence relations and orthogonality identities. In Lean 4, explicit index manipulation on large matrices is notoriously brittle, and \`simp\`/\`omega\` will routinely time out on the resulting arithmetic goals. You are not choosing an "easier" path; you are choosing a path that requires formalizing special functions from scratch.

Furthermore, your target statement \`PosSemidef (Rmatrix n x) ↔ ∀ k, PosSemidef (Mblock n k x)\` is mathematically correct but \*\*proof-hostile\*\*. Mathlib’s \`Matrix.PosSemidef\` is defined via quadratic forms ($v^T M v \\ge 0$). Proving the equivalence directly by manipulating $2^n$-dimensional vectors is a dead end. 

\*\*2. The Mathlib Gap Reality Check (The Hidden Iceberg)\*\*  
You asked for a gap analysis. Here is the brutal truth about what exists and what doesn't in current Mathlib 4:  
\*   \*\*Exists:\*\* \`Matrix.PosSemidef\`, block matrices (\`Matrix.fromBlocks\`), \`Matrix.kronecker\`, basic binomial sums, and Krawtchouk polynomials (from prior Delsarte LP formalizations).  
\*   \*\*Missing (The Iceberg):\*\*   
    1\.  \*\*Hahn Polynomials:\*\* \*I know\* (up to my knowledge cutoff) that Mathlib \*\*does not\*\* have Hahn polynomials, their orthogonality relations, or their difference equations. \*Uncertainty:\* Mathlib updates daily; it is possible a recent PR added them. \*Resolution:\* Run a search in the latest Mathlib repository for \`OrthogonalPolynomials.Hahn\`. If missing, the "elementary" path requires a multi-week special-functions formalization effort.  
    2\.  \*\*Kronecker Block Congruences:\*\* While \`Matrix.kronecker\` exists, using it to state and prove block-diagonal congruences cleanly requires significant custom API glue that Mathlib currently lacks.  
    3\.  \*\*Algebra Isomorphisms:\*\* There is no general "commutant of a group action" or "Wedderburn decomposition" framework you can just plug into.

\*\*3. Refined Target Statement (The Congruence Path)\*\*  
Do not ask the formalizers to prove the PSD equivalence directly. Factor it through \*\*matrix congruence\*\*, which is the standard Mathlib idiom. The formalization must proceed in two steps:  
1\.  \*\*The Congruence Lemma:\*\* Prove there exists an orthogonal matrix $U$ such that $U^T (\\text{Rmatrix } n \\ x) U \= \\bigoplus\_k (\\text{Mblock } n \\ k \\ x \\otimes I\_{m\_k})$.  
2\.  \*\*The PSD Equivalence:\*\* Derive your target statement trivially using \`Matrix.PosSemidef.congr\` (which exists) and the fact that Kronecker products and direct sums preserve PSD-ness.   
\*Fix your brief to explicitly mandate this two-step decomposition.\*

\*\*4. Estimate & Staging (The Honest Timeline)\*\*  
\*   \*\*Milestone 1 (The \`sorry\` wrapper):\*\* 1–3 days. Define the types, state the congruence, state the PSD equivalence, use \`sorry\` for the core proof, and wire it into your daemon. This achieves your "shrink the TCB" goal.  
\*   \*\*Milestone 2 (The Discharge):\*\* \*\*4–8 expert-weeks.\*\* This is the actual project. Formalizing the Hahn polynomial identities and grinding the $U^T M U$ matrix multiplication will take months, not weeks.   
\*   \*\*Alternative if time-constrained:\*\* If you cannot afford 2 months of formalizer time, pivot to a weaker, daemon-specific trust model: write a verified external checker (e.g., in Coq, or a verified Rust tool using interval arithmetic) that checks the numerical $U^T M U$ identity for \*specific\* $n$, and trust the external checker, rather than formalizing the general $n$ theorem in Lean.

\*\*5. One thing you're getting wrong (The TCB Illusion)\*\*  
You state: \*"admit this as one named, citation-backed lemma first (it shrinks our informal trusted base to a single statement)."\* This is false. If you admit \`schrijver\_block\_diag\`, your TCB includes that \`sorry\`. But to \*use\* it in your pipeline, you also need to map your Python-generated $\\beta$ coefficients to the Lean definitions. If the mapping from Python to Lean is unverified, or if the Lean definition of \`Mblock\` doesn't exactly match your Python \`β\` oracle, the single \`sorry\` on the theorem \*\*does not protect you\*\* from a bug in the $\\beta$ generation. The TCB is the theorem \*plus\* the definition equivalence. You must mandate that the Lean definition of \`β\` is proven equivalent to the exact rational output of your Python oracle, or the \`sorry\` is a leak.

Prioritized recommendation: Update the brief to mandate the matrix congruence decomposition, explicitly flag the Hahn polynomial formalization as the primary risk, and verify the Python-to-Lean $\\beta$ definition equivalence to prevent a TCB leak.

# MiniMax M3

\# Review of the F2b external brief

Overall: this is a well-prepared, technically literate brief from a team that clearly knows its domain. It does several things right — pinning the β formula with explicit convention warnings, separating the staging ask from the eventual payoff, and pre-acknowledging that §II is the chosen path. The main deficiencies are in \*self-containment for an external reader\* and in \*failing to pre-empt the gap analysis\* (which is itself one of the three asks). I would not send this as-is to a cold recipient.

\#\# What works

\- \*\*Convention pinning on β.\*\* The "NOT \`C(t,u)\`, zero outside \`0 ≤ b ≤ a\`, sign via parity of \`u−t\`" passage is exactly the right move. Index-order traps are how these formalizations silently die. Keep it.  
\- \*\*The iff direction in the statement.\*\* \`PosSemidef (Rmatrix n x) ↔ ∀ k, PosSemidef (Mblock n k x)\` cleanly captures what §II actually proves (both directions), and you've flagged that the formalization target is this two-sided statement, not a one-sided corollary. Good.  
\- \*\*The "admit-then-discharge" staging.\*\* This is a sound Lean workflow for keeping a multi-month project committable. The brief is right that the first milestone is a compiling wiring.  
\- \*\*The three-certificate payoff.\*\* Naming A(19,6) ≤ 1280, A(23,6) ≤ 13766, A(25,10) ≤ 503 — these are all real Schrijver bounds — anchors the deliverable in something the recipient can verify externally.  
\- \*\*Governance framing.\*\* "LLMs propose, only the Lean kernel decides" is the right one-sentence positioning.

\#\# Issues, in rough priority order

\#\#\# 1\. The brief is not actually self-contained

The header comment claims "Self-contained: paste into an email / Mathlib Zulip thread / an Aristotle project description as-is." It is not. An external recipient will not know what any of these mean:

\- "F1", "F2a", "F2b" (your internal phase numbering)  
\- "the operator" (an internal role)  
\- "Phase 0" (a project state)  
\- "the Leibniz theorem-daemon project" (no URL, no one-liner)  
\- "real-code PSD differential tests with corrupt controls" (what differential test? what corruption model? what is "real-code"?)

A recipient on Mathlib Zulip is a category-theoretic graph theorist or combinatorics formalizer, not someone who knows your project. The "corrupt controls" sentence in particular reads as jargon to insiders and as nonsense to outsiders — rephrase or drop.

\*\*Fix:\*\* add a 3–5 line "Project context" paragraph up top, and a glossary for the in-flight internal references (F1 \= …, F2a \= …, F2b \= …). Even one sentence each is enough.

\#\#\# 2\. The gap analysis ask is under-supported

You ask "which pieces exist in Mathlib today" but you don't pre-emptively state your own guess. A recipient faced with this brief has to research:

\- Whether \`Matrix.IsPSDCongr\` and friends cover PSD congruence invariance  
\- Whether \`Krawtchouk.krawtchouk\` (added by the quantum-info group in 2023–2024) is rich enough for the Krawtchouk-sum manipulations  
\- Whether \`Matrix.fromBlocks\` and block-PSD decomposition lemmas exist  
\- Whether the orthogonal matrix \`U\` from §II has any reusable form (Hadamard-like, signed Krawtchouk)

You don't need to answer these — but you should list them as the explicit sub-questions of the gap ask, so the recipient knows what to investigate and so the ask is scoped. Right now "gap analysis" is open-ended enough that you'll get a one-paragraph shrug back.

\*\*Fix:\*\* turn "gap analysis" into a bulleted list of 4–6 specific Mathlib questions. The recipient can then either answer them or honestly say "I don't know, I'd have to look."

\#\#\# 3\. The "admit first" framing is slightly misleading

\> "shifts our informal trusted base to a single statement"

This is true in spirit but the phrasing invites pushback from anyone who notices that admitting a lemma in Lean \*enlarges\* the trusted base (you now trust the statement \*and\* the proof of admissibility) until the axiom is discharged. The honest framing is:

\> "converts a multi-page human-verification obligation into a single citation-backed statement obligation, plus the kernel-checked proof that discharges it"

\*\*Fix:\*\* rephrase. The current line is technically defensible but will be challenged, and you don't want the brief to open on a quibble.

\#\#\# 4\. Scope of the full bridge is parenthetical

The parenthetical at the end of the "Ground truth" section lists four other pieces needed (codes ⇒ primal-feasible, R/R′ PSD via averaged outer products, Proposition 1, eq. (21) \`|C| \= Σ C(n,i) x⁰\_{i,0}\`, PSD congruence invariance). This is doing huge work and is buried in a parenthetical. A reader will not know whether the F2b ask \*includes\* any of these or whether Theorem 1 is genuinely the only blocker.

\*\*Fix:\*\* make this a short "Scope of the full bridge" subsection with one line per piece, each marked "in scope for F2b" or "out of scope, already formalized" or "out of scope, future phase."

\#\#\# 5\. Minor technical / presentational nits

\- "PSD" / "psd" / "PosSemidef" — pick one rendering for prose. Lean name is \`PosSemidef\`; the rest of the doc should be "PSD".  
\- The β formula renders \`Σ\_u\` with a literal underscore; in a brief destined for a Zulip thread (which mangles backslashes), consider writing "Σ over u".  
\- "finite combinatorics" in the §II characterization is true but vague — the orthogonal matrix \`U\` is \*signed Krawtchouk\*, which Mathlib may already partially know.  
\- \`Triple n → ℚ\` and \`IsTripleDistribution\` are not defined in the brief. Even one line ("\`Triple n\` is the index type for \`(i,j)\` with \`0 ≤ i,j ≤ n\`; \`IsTripleDistribution\` encodes the 5-feasibility constraints") would help. The signatures are part of the formalization target and the recipient needs to know what you're committing to.  
\- The "12,155 entries at n=19 in seconds" — fine as a sanity number, but cite the source script's exit code or checksum rather than just asserting it.

\#\#\# 6\. Estimation realism

You ask for "expert-weeks, staged" with no anchor. A serious Lean formalization of a Schrijver-scale result is months, not weeks, even for a strong team. If the recipient quotes 4 expert-weeks, will you accept that? If they quote 30, will you walk away? You should tell them.

\*\*Fix:\*\* add one line: "Our internal estimate for end-to-end is X expert-weeks; we want the brief's estimate to be calibrated against that and flag 2× / 5× scenarios."

\#\#\# 7\. Definition of done

None of the three asks has a deliverable form. "Plan" — markdown doc? PR description? Lean file? "Gap analysis" — same question. "Estimate" — same. Without this you'll get back a 200-word reply and discover it was the wrong format.

\*\*Fix:\*\* in the "Three asks, concretely" section, append a deliverable form to each, e.g., "deliverable: a self-contained markdown document, ≤ 4 pages, with the lemma DAG and the Mathlib gap table."

\#\# What the recipient will probably ask you

Be ready for these — the brief should ideally pre-empt them:

1\. \*\*"What is \`Triple n\`?"\*\* — see nit 5\.  
2\. \*\*"Is the working Mathlib commit hash documented? Anything in \#docs or in active PRs I should know about?"\*\* — add a one-liner about which Mathlib revision you target.  
3\. \*\*"Why not just use \`Krawtchouk\` from Mathlib for the matrix \`U\`?"\*\* — have an answer ready (it might be that the existing definition is \`Krawtchouk n q k i\` and Schrijver's \`U\` is a signed variant with \`q=2\` and row/column conventions that don't match).  
4\. \*\*"Which direction of the iff is the hard one?"\*\* — both are non-trivial; the "blocks PSD ⇒ whole matrix PSD" direction goes through the orthogonal-ish basis change and the other goes through the explicit β reconstruction. The brief should say this.  
5\. \*\*"Has anyone in the Lean community already touched Terwilliger / association schemes / Bose-Mesner?"\*\* — almost certainly no, but say so.

\#\# Bottom line

The technical content is sound and the conventions are pinned. The brief fails the "self-contained" test it sets for itself, underspecifies two of its three asks, and buries its scope in a parenthetical. With the fixes above (≈1 hour of editing) it becomes a strong external ask. As-is, it reads like internal project notes that escaped.  
```

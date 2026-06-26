<!--
M2 expressibility-audit finding (ADR 0036 §10.5 gate i). Second round-2 "measure-before-build"
pre-test. Self-contained record. Method: 31-agent assemble→classify→adjudicate workflow over a
benchmark of genuinely non-textbook theorems, classified against the exact sound-faithfulness DSL
grammar (read from leibniz/backends/smt_z3.py). Provenance: docs/results/m2_expressibility_audit_report.json.
No billable generator/prover compute — gate (i) only (expressibility). Trust boundary untouched.
-->

# M2 (gate i) — Expressibility audit: can the DSL even *state* novel mathematics?

**Status:** measured, 2026-06-26. **Verdict: 0 of 24 genuinely non-textbook theorems are
expressible** in the sound-faithfulness DSL — and the binding constraint is **not the vocabulary,
it is the bounded-box soundness paradigm itself.** Feeds ADR 0036 §12.

## Why this experiment

ADR 0036 §10.5 M2 has three reachability gates: (i) **expressibility** — can the formal language
even state genuinely novel theorems? (ii) generator-reach, (iii) bridge-synthesis. Round-2
reviewers (Fugu, Fugu Ultra) were explicit: *"if you can't express them, Stage B isn't your
bottleneck; language design is."* Gate (i) is the cheap one — no LLM generator, no prover, no
billable compute — so the operator chose to run it first. If the language can't state novel math,
the whole proof-carrying program is downstream of a language/paradigm problem.

## Method

The **authoritative sound envelope** was read directly from `leibniz/backends/smt_z3.py` (`_conv` /
`compile_pred`): a claim is *mechanically* faithfulness-checkable only if it fits a small grammar —
quantifier-free boolean combinations of integer polynomials with **constant** exponents,
**constant**-divisor mod/div, `min`/`max`, and one special periodic `base^n % m` form, all checked
on a **bounded box `[0,64]`**. Anything outside routes to the LLM judge (untrusted, not the sound
path). Full spec: the §"missing-feature vocabulary" below.

A 31-agent workflow then: **assembled** 24 target theorems (4 each across number theory, additive/
combinatorial, sequences/recurrences, analysis/irrationality, inequalities/algebra, discrete/
extremal), independently **classified** each against the grammar, and **adjudicated** (dedup,
adversarial sanity-check, histogram, verdict).

## Result

**Expressible in the DSL: 0 of 24.** Every target is OUT. The targets are unambiguously
research-grade — Wolstenholme, Zsygmondy, Gauss's primitive-root sum, Lerch's Fermat-quotient,
Ramanujan partition congruences, Erdős–Ginzburg–Ziv, Cauchy–Davenport, Schur, Motzkin numbers
mod 8, Apéry supercongruence, Catalan ν₂, Stern's diatomic, Apéry's ζ(3) irrationality, the
continued fraction of e, Gelfond–Schneider, Roth, the Motzkin & Choi–Lam PSD-not-SOS polynomials,
Newton's & Schur's inequalities, Ramsey R(4,4)=18, Turán/Mantel, Brooks, Erdős–Ko–Rado.

**Missing-feature histogram** (over all 24 OUT targets; a target can need several):

| feature | count | repairable by a bounded DSL extension? |
|---|---|---|
| #2 UNBOUNDED-∀ / infinitude | **19** | **No** — paradigm-level |
| #7 number-theoretic functions (gcd/φ/μ/π/binomial/primality) | 14 | vocabulary (lookup tables) — but stranded behind #2/#1 |
| #3 EXISTENTIAL / ∀∃ alternation | 12 | No — paradigm-level |
| #4 summation / product (Σ, Π, continued fractions) | 11 | vocabulary — but stranded behind #2 |
| #1 REALS / irrationality / transcendence | 9 | No — needs a real-domain backend |
| #8 sequences / recurrences (p(n), Apéry, Stern…) | 7 | only via a sequence decision procedure (new backend) |
| #9 sets / combinatorial structures (graphs, colourings) | 7 | vocabulary, but a large lift |
| #6 variable-modulus | 6 | vocabulary — but the modulus is the quantified var → re-introduces #2 |
| #5 variable-exponent | 6 | partial (one periodic case exists) |
| #10 higher-order / complexity / O-notation | 6 | No |

## What M2 establishes

1. **The DSL cannot state research-grade mathematics — 0/24.** Decisive and well-distributed
   (4/4 OUT in every area).
2. **The blocker is NOT the vocabulary — it is soundness over an infinite domain.** This is the
   non-obvious finding. The naïve M2 hypothesis ("maybe we just need more operators") is **false**:
   adding Σ, gcd/φ lookup tables, or variable-modulus would make a predicate *well-formed* for a
   *fixed instance*, but cannot make a **universal-over-infinitely-many** claim *sound* on a
   `[0,64]` box. #2 UNBOUNDED-∀ sits on 19/24 and **no bounded extension can repair it**; #1 reals
   (9/24) and #3 ∀∃-alternation (12/24) are likewise paradigm-level. The bounded-box
   decision-procedure **paradigm**, not its operator set, is what excludes novel math.
3. **The "modest certifying-fragment DSL extension" path (round-2 §10.1) is largely dead for the
   bounded checker.** Escaping requires a *different sound backend*, each reaching only a narrow
   class: an **automatic-sequence / Walnut decision procedure** (sound ∀n for the base-b sequence
   facts — Motzkin mod 8, Stern, Catalan ν₂), an **SOS / Positivstellensatz** backend (the real
   polynomial inequalities — Motzkin, Choi–Lam, Schur, Newton), or the **kernel bridge (Stage B)**
   (general, but undecidable-in-general). None is a DSL tweak; each is a distinct sound engine.
4. **One genuine vocabulary-only gap exists** (the exception that proves the rule): Ramsey
   R(4,4)=18 is *finite* and in principle decidable by search, yet OUT purely because the DSL has
   no graph/colouring/set vocabulary (#9). It is 1/24, and a sound bounded graph backend is itself
   a large build.

## M1 + M2 converge on one root cause

- **M1** (proof-compression): mining the existing corpus recovers only the **textbook genre**
  (finite-ring closure in ℤ/mℤ); novelty is input-diversity-gated.
- **M2** (expressibility): the sound language can only **express** that same textbook genre, and the
  reason is the bounded-box soundness paradigm.

Both independent measurements point at the *same* wall ADR 0036 §10 named: the **pointwise
bounded-box check used as the sole sound faithfulness arbiter.** The escape is therefore not a
better proposer (ADR 0034, measured 0-novel), nor a richer grammar inside the box (ADR 0035,
measured 0-novel), nor abstraction mining over the current corpus (M1, recovers the genre) — it is
a **different sound checking paradigm**: the kernel bridge (Stage B), or narrow sound decision-
procedure backends for specific classes. That is exactly where ADR 0036 §10.2 located it, now
confirmed from the expressibility side.

## Honesty notes

- **The novelty-recheck labels are a known artifact.** The per-target `novelty_recheck` flagged
  22/24 "textbook"; the adjudicator flagged this as internally contradictory — the targets
  (Wolstenholme, Zsygmondy, Apéry ζ(3), Roth, Gelfond–Schneider, Ramsey R(4,4)…) are manifestly
  *not* first-year. The classifiers conflated "famous / appears in textbooks" with "first-year
  elementary." **The 0-expressible conclusion is fully robust to this**: all 24 are OUT regardless
  of the novelty label, so the gate result does not depend on it.
- **No false-positives/negatives to overturn:** zero targets are labelled IN; the closest-to-IN
  cases were spot-checked (Ramanujan p(5n+4) — `5n+4 % 5` is legal but `p(·)` is unnameable, OUT;
  the SOS reals — integer-box check is unsound at the equality locus, OUT).
- **Adversarial layer:** the adjudicator performed the adversarial sanity pass (false-pos/neg
  check, the novelty-label catch). The DSL spec was read directly from `smt_z3.py`, so the
  classification target is authoritative.
- **Gates (ii)/(iii) are moot for the current DSL:** generator-reach and bridge-synthesis presume
  an expressible target; with 0 expressible, the next question is not "can the generator reach
  them / can the prover bridge them" but "does a *specific new sound backend* (Walnut / SOS /
  kernel bridge) admit a real novel class" — a more targeted probe than the original M2(ii/iii).
- Trust boundary untouched: read-only inspection + LLM classification; no `kernel_verified` /
  `promulgated` writes; `tests/test_invariants.py` unchanged.

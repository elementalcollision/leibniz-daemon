<!--
Scoping for the two remaining rungs of the Terwilliger audit→Q.E.D. ladder (F1 whole-cert-in-kernel, F2
bridge theorem) + the honest discovery outlook. Written for FRESH SESSIONS to pick up cold — each rung section
is self-contained (inputs, design, exit tests, risks, size). Sizing numbers are MEASURED on the actual
A(19,6) certificate, not estimated. No code in this pass; docs only.
-->

# Terwilliger three-point — formalization scope: audit → Q.E.D. (2026-07-01)

## Where the ladder stands (context for a cold start)

The SDP three-point producer is complete at the audit tier (`DUAL_CERTIFICATE_CHECKED`), PRs #216–#226:
**A(19,6) ≤ 1280** (Schrijver's Table I record) is reproduced as an exact-rational dual certificate
(`scripts/terwilliger_exact_lp.py::certify_lp`, ~17 s) whose 20 PSD blocks the **real Lean 4.31 kernel
verifies** (per-block `ldltOK` theorems, 16 s; corrupted block rejected). What the kernel does *not* yet check:
the **stationarity system + nonnegativity + bound arithmetic** (today: exact-rational Python, `dual_check`),
and the **reduction itself** (that a feasible dual bounds A(n,d) — the formulation transcription, Fugu's
Trap 3). Those are rungs **F1** and **F2** below. Key code: `scripts/terwilliger_{beta,dual,sdp,cert,exact_lp}.py`;
key docs: `docs/results/terwilliger-*.md`, the review synthesis `docs/results/terwilliger-review-synthesis-2026-07-01.md`.

**Measured certificate profile (A(19,6), the sizing ground truth for F1):**
- 55 free orbit variables ⇒ **55 stationarity identities**;
- 4621 multipliers total but only **55 nonzero** (the exact LP returns a *basic* vertex — sparse by
  construction; zeros need no kernel arithmetic, only a "treated as 0" convention);
- max nonzero multiplier **47 bits** (median 32); **common denominator 34 bits** ⇒ after clearing, every
  identity is small-integer arithmetic;
- **8076 nonzero β entries** at n=19 (the tensor the kernel must not take on trust);
- 20 PSD blocks, largest 20×20, scale ≤ 2113 bits (already kernel-verified).

---

## Rung F1 — whole-certificate-in-kernel (stationarity-in-Lean; D3 in full)

**Goal.** The kernel checks the *entire* certificate, not just the PSD blocks: (1) recompute β from eq. (7),
(2) verify each of the 55 per-orbit stationarity identities, (3) verify multiplier nonnegativity, (4) verify
`Σγ − ν ≤ target`. Output stays audit-tier (F1 does not change *what* is trusted, only *how much* of the check
the kernel performs); it is the prerequisite that makes F2 meaningful.

**Design (one fresh session, all pieces have working precedents in-repo):**
1. **β in Lean.** `betaOK`: kernel recomputes `β^t_{i,j,k} = Σ_u (−1)^{u−t} C(u,t) C(n−2k,u−k) C(n−k−u,i−u)
   C(n−k−u,j−u)` with Pascal-rule binomials — the #209 Delsarte cert already does kernel-side binomial
   recomputation (`cc`) to n=24, so this is a known-feasible pattern. To keep `decide` cheap, the producer
   supplies the 8076-entry β table and the kernel **verifies the table against eq. (7)** (recompute-and-compare;
   never trusts it) — one theorem per k-block slice, following the B2 per-block lesson.
2. **Stationarity in Lean.** After clearing the 34-bit common denominator D: for each of the 55 orbit keys,
   an integer identity `obj_coeff·D + Σ_blocks β·(Z−Z')·D + Σ_multiplier contribs = 0`. All data integer;
   55 small theorems (`statOK_i`).
3. **Nonneg + bound.** `d ≥ 0`-style list checks on the 55 nonzero multiplier numerators (D > 0 fixed), and
   one integer inequality `Σγ·D − ν·D ≤ target·D`.
4. **Assembly.** One source file, one theorem per obligation (the B2 lesson: never one giant conjunction),
   `maxHeartbeats 0`. Producer = `terwilliger_exact_lp`; renderer new (`terwilliger_kernel_full.py`).

**Exit tests (GREEN =):** A(19,6): all obligations kernel-True; **four corrupted controls kernel-False**
(a wrong β entry in the table; a perturbed multiplier breaking stationarity; a negative multiplier; a bound
claim of 1279). Small cells (A(4,2)/A(6,4)) as fast regressions. All docker-gated, CI-skipping.

**Risks & mitigations.** (a) `decide` cost of the β verification (8076 entries × binomial sums): default
strategy = one theorem per (k,t) slice; escalate to supplied-and-verified Pascal-row tables only if a slice
exceeds ~60 s under `LeanCliBackend(timeout_s=900)`. (b) Source size (~1–2 MB with the β table): B2 showed
164 KiB is fine; chunk into multiple `check_source` calls if the elaborator balks. **Size: M — one focused
session.** No trusted-surface edits (standalone checker; `LeanVerifier.discharge` untouched).

**Cold-start pointers (F1) — the specs are the existing implementations; transcribe, don't re-derive:**
- The *exact* stationarity coefficient structure (orbit binding, block indexing, multiplier contributions) is
  `collected()` in `scripts/terwilliger_dual.py` — the Lean checker mirrors that function line-for-line; its
  correctness is already machine-validated (Lagrangian-identity + weak-duality tests with corrupt-controls).
- β ground truth: `td.beta` (eq. 7 verbatim, Phase-0-validated) + `docs/results/terwilliger_beta_oracle.tsv`.
- Certificate data source: `terwilliger_exact_lp.certify_lp(19, 6, target=1280, return_duals=True)` (~17 s;
  cache the duals — they are deterministic given the solver seed-free Clarabel run, but re-solves may vary
  slightly, so persist the certified duals to JSON as part of the build).
- Render + kernel-call pattern to copy: `terwilliger_cert.render_cert_lean` (per-theorem + `maxHeartbeats 0`)
  and `terwilliger_exact_lp.kernel_verify_lp`. **check_source trap:** any elaboration failure reads as False —
  when debugging a False, call `bk._run_lean(src).output` for the raw diagnostics (the B2 lesson, twice now).
- Corrupted-control pattern to copy: `tests/test_terwilliger_exact_lp.py::test_kernel_attests_a19_6_...`
  (mutate one datum, expect the whole file False). Tests are docker-gated (`_needs_docker`) + cvxpy-gated
  (`_needs`), CI-skipping; results doc goes in `docs/results/terwilliger-f1-<date>.md`; process = branch
  (`terwilliger-f1`) → PR to main → CI (invariants lane) → operator merges.

---

## Rung F2 — the bridge theorem (audit → Q.E.D.)

**Goal.** A Lean theorem `tw_bridge : dual_feasible n d duals → A(n,d) ≤ bound duals` — so that a kernel-checked
certificate *plus* this theorem yields a kernel-checked statement **about codes**, eliminating the formulation
transcription from the TCB (the panel's central warning). Three stages, sharply separated because their cost
and trust profiles differ by an order of magnitude:

**F2a — weak duality over the abstract primal (M; one session, Lean+Mathlib).**
Formalize exactly Phase 1's Lagrangian argument: define the primal constraint set abstractly (variables
`x : orbit → ℚ`, the two β-block families PSD, (20)(i)/(ii)), and prove `∀ x feasible, obj x ≤ Σγ − ν` for any
dual satisfying stationarity + PSD + nonneg. This is finite-dimensional linear algebra (Mathlib has
`Matrix.PosSemidef`, inner products, finite sums). It does **not** mention codes. Machine-checked analogue of
`weak_duality_holds` (which already validates the argument numerically with corrupt-controls).
*Cold-start pointers:* the informal proof to formalize is the module docstring + `lagrangian()`/`collected()`
of `scripts/terwilliger_dual.py` (L = c·x + Σ⟨Z,M(x)⟩ + linear terms; each term ≥ 0 at feasible points;
stationarity collapses L to the constant Σγ−ν). Sketch statement:
`theorem tw_weak_duality (P : TwPrimal n d) (D : TwDual n d) (hD : D.feasible) : ∀ x, P.feasible x → P.obj x ≤ D.bound`.
The key Mathlib lemma is `Matrix.PosSemidef.trace_mul_nonneg`-style (⟨Z,M⟩ ≥ 0 for PSD Z, M).

**F2b — codes ⇒ primal-feasible (XL; the real formalization project — external round candidate).**
Prove: every binary code C with min distance ≥ d yields a feasible x (its scaled triple-distribution). Needs
Schrijver §I–II formalized: R/R′ PSD (averaged sums of outer products, eq. 9), Proposition 1 (eq. 12/14), the
**block-diagonalization Theorem 1** (eq. 7/8 — Schrijver's Propositions 2–5; the hard core), PSD congruence
invariance (deleting the normalization), and (20)(i)–(iv) + eq. (21) `|C| = Σ C(n,i)x⁰_{i,0}`. Estimated
**weeks-to-months of expert Lean work**; natural staging: admit Theorem 1 as ONE named lemma first (shrinks
the informal TCB to a single citation-backed statement), then discharge it. Sketch of the admitted lemma (so
F1's kernel data plugs in directly): `lemma schrijver_block_diag (n : ℕ) (x : Triple n → ℚ)
(hx : IsTripleDistribution x) : PosSemidef (Rmatrix n x) ↔ ∀ k, PosSemidef (Mblock n k x)` with `Mblock`
defined via the eq. (7) β coefficients. **This is the piece to send to an external formalization round**
(Aristotle / the review panel / Mathlib community) — draft brief below.

**F2c — trust wiring (GATED; do not attempt before F2a+F2b land + an ADR).**
Stamping Q.E.D. through this path means a new discharge route into `Demonstratio.kernel_verified` — edits
inside the guarded core (`verifiers.py`, trust tiers). Per the charter: PreToolUse hook + operator sign-off +
a witness round (precedent: the C proof-edge deferral, task #68's 8/8 witness protocol). The alternative that
needs **no** trust edit: keep outputs at the Observatory/reading-room tier (ADR 0038 precedent) with the
bridge theorem published alongside — worth an explicit operator decision when F2b completes.

**Draft external brief (F2b), for when the operator sends it:** state Theorem 1 (eq. 7/8) precisely with our
validated β convention (`C(u,t)`, Phase 0); attach `terwilliger_beta_oracle.tsv` as ground truth; ask for
(i) a Lean 4 + Mathlib formalization plan with lemma decomposition, (ii) which Mathlib pieces exist
(representation theory of S_n wreath actions / Specht-style arguments vs. elementary induction per Schrijver's
own proof), (iii) an estimate and staging. Emphasize: the *elementary* §II proof (explicit U, Propositions 2–5)
is preferred over abstract C*-algebra machinery — it minimizes Mathlib dependencies.

---

## Discovery outlook (honest; decides how much F2 is worth)

Reproduction ≠ discovery: Schrijver already computed Table I for all n ≤ 28, so **no cell in that range can be
tightened by the base 2005 formulation** — our A(19,6) result validates the *machinery*, not new mathematics.
For the producer to *discover* (tighten a current-best-known bound), the options, in rough cost order:
1. **Beyond-Table-I reach probe (1 session, operator-local, cheap):** sweep n = 20..30-ish cells against
   Brouwer's current table (`https://www.win.tue.nl/~aeb/codes/binary-1.html`, the same reference Schrijver
   cites; snapshot the relevant cells into a checked-in JSON before comparing); measure where our solve+LP
   pipeline still lands and whether any current best-known upper bound still comes from a *weaker* method.
   Realistic expectation: low hit-rate (later literature has stronger SDPs), but it is the cheap empirical
   answer and also measures the pipeline's n-scaling.
2. **Sharpenings:** eq. (25) constraints (`C(n,i)x⁰_{i,0} ≤ A*(n,d,i)` from constant-weight bounds) — small
   formulation delta, known to help mostly at the margins.
3. **Constant-weight (Johnson scheme):** a *separate* algebra build (panel D1) — new β, new blocks; medium
   project with its own Table II targets.
4. **Split-Terwilliger / quadruples (post-2005 hierarchies):** the modern frontier; large formulation builds.

**Recommended sequencing for fresh sessions:** ① discovery reach probe (cheap; informs whether F2b's
investment has a discovery payoff or is infrastructure), ② F1 (self-contained, makes every future cert fully
kernel-checked), ③ F2a (bounded Lean work), ④ operator decision on F2b external round + F2c tier question.

## Invariants (apply to every rung)
F1/F2a/F2b touch **no trusted surface** (standalone checkers + standalone theorems);
`tests/test_invariants.py` stays byte-identical. F2c is the *only* trust-touching step and is gated as above.

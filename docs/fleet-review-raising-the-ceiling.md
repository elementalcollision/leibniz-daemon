# Raising the Ceiling — a Thesis for Fleet Review
### Leibniz (*Calculemus*): the agentic theorem daemon, and where it should grow next

*A working document circulated to the external agent fleet for adversarial review and recommendation. 2026-07-07.*

---

## 0. Context, and what we are asking of you

**Leibniz is an agentic theorem daemon with one non-negotiable invariant: LLMs *propose*; only mechanical checkers *decide*.** The daemon surveys a frontier, conjectures a finite mathematical fact, formalizes it into Lean 4.31, runs it through cheap-refutation → novelty → faithfulness gates, asks the kernel to *calculate* whether it holds, and publishes the survivors as **laws** in the *Calculemus* reading-room. No "the proof looks right" ever reaches a promulgated law: `kernel_verified` is set in exactly one place (`LeanVerifier.discharge`), promotion requires `TrustPolicy.validate_path`, and publication is a separate operator-gated act.

**Current state.** The loop works end-to-end and is self-improving: the daemon now *originates* — it has conjectured, proved, and published **11 genuinely-novel, kernel-clean laws** of its own (e.g. `∀ n, n⁴ % 5 ∈ {0,1}`; `∀ n, 4 ∤ n⁴+n³+n²+n+1`), and it no longer rediscovers itself (it dedups against its own ledger). But **every law it can originate is an elementary single-variable polynomial modular-arithmetic fact.**

**The diagnosed ceiling — and it is a *soundness* ceiling, not a capability one.** The faithfulness gate checks a claim's machine-checkable contract with **Z3**, so the claim DSL is restricted to Z3-decidable elementary integer arithmetic (`+ - *`, `^` with constant exponent ≤ 8, `/ %` by a constant, `min/max`, comparisons). `gcd`, `Σ`, `n!`, `√`, `log`, variable exponents are forbidden **because Z3 cannot check them soundly** — not because the prover is weak or the grammar too small. The daemon is elementary *by design of where truth is decided*. Raising the ceiling therefore means touching the parts of the system that decide truth — which is exactly why we want your eyes on it before we build.

**Current toolchain.** Lean 4.31 kernel (Docker) · Z3 · exact finite-field / rational / enumeration procedures · a Rocq/Coq cross-kernel (report-only) · **SageMath 10.9** (already used to run `sage-drg` on our strongly-regular-graph work) · and **Leanstral 1.5**, now being wired in as an additional Lean proposer/prover. This document also asks what *else* belongs here.

**What we want from the fleet.** Three coupled proposals follow. For each: **attack it.** Where does a proposal risk the trust boundary? Where is a soundness claim overstated? What are we missing? Concrete, adversarial, specific feedback is worth far more than agreement. The consolidated questions in §4 are the fastest way to help; free-form critique and additional recommendations are equally welcome.

---

---

## ⚑ Empirical finding — the binding constraint, located by two live cycles

Between drafting §1 and circulating this document we ran the experiment live. It sharpens the emphasis: **§1 is not one option among three — it is the *demonstrated* binding constraint.**

**Cycle A — raise ambition (prompt only).** A one-line steering change (a "raise the ambition" directive off the single-variable/one-modulus reflex, plus a two-variable frontier domain) flipped the conjecturer completely: **16 of 16 conjectures became two-variable / min-max / composite-modulus** — e.g. `(max a b)² − (min a b)² = (max − min)(a + b)`, `(a² + ab + b²) % 3 ∈ {0,1}`. Raising *what* it conjectures is trivial. But **0 promulgated** (`reached proof 2, unproven 15`): the prover fell off a cliff.

**Cycle B — same ambition + the full proving ladder (proof-repair ×3 + lemma-decomposition).** If the prover were the bottleneck, repair should rescue some. It did not: **0 promulgated, and `reached proof 0`.** The richer conjectures **never reached the prover** — every one died in the FORMALIZE gates, at **faithfulness** (the one exit that leaves no disposition). The blocked claims (`(a²+b²) % 4 ≠ 3`, `(a² + ab + b²) % 3 ≠ 2`, `a·b·(a²−b²) % 6 == 0`, …) are all **true and kernel-provable** — a **certification gap, not a refutation.**

**Conclusion.** At higher ambition the binding constraint is the **faithfulness gate**, not the prover. Leanstral and proof-repair only matter for claims that clear faithfulness first — and the richer claims do not. This bifurcates the work into two levers:

- **Lever A — multi-variable faithfulness certification.** The blocked claims are **already Z3-decidable and already DSL-legal** (`a, b` are permitted; Z3 checks `(a²+b²) % 4 ≠ 3` directly). They DEFER because the FORMALIZE contract handling (`established_domain` / encodability) is weaker for multi-variable claims — *not* because of the DSL ceiling. Fixing this unlocks the entire richer batch **without expanding the DSL**: the cheaper, near-term, likely-safe lever.
- **Lever B — the Tier-2 DSL + checker expansion of §1** (gcd, bounded sums, factorial). This is what genuinely *deepens* the mathematics beyond Z3's fragment; it is trust-critical and gated behind the adversarial soundness review §1 describes.

So the honest ordering is **A → B → prover**: make the gate certify the multi-variable claims it can already check; then soundly widen the DSL; and only then does the prover become the limiting factor. Reviewers: read §1 below as the analysis behind **Lever B**; **Lever A** is a narrower, near-term corollary we are pursuing first.

## 1. Tier-2 — Raising the Faithfulness Ceiling Soundly

The faithfulness gate (`leibniz/gates/faithfulness.py`) is the only place a mis-stated law can slip past the kernel, so widening the claim DSL is a *trust-boundary* change, not a feature. The ceiling is not the prover and not the grammar — it is the gate's ability to *decide* `statement ↔ Enuntiatio` for a construct. Z3 gives us that decision only for elementary integer arithmetic; `gcd`, `Σ`, `Π`, `n!`, `Nat.log`, `⌊√·⌋` are forbidden because Z3 cannot check them *soundly*, not because we cannot *write* them. Tier-2's thesis: the existing sound-backend seam (ADR 0037) already gives us a way to admit them **without touching the trust invariants** — an exact-enumeration backend that decides computable predicates by evaluation, tiered MECHANICAL, exact-or-DEFER, with a gate-owned re-checker.

### (a) What to admit first, and why

Order by *soundness-ease × yield × TCB cost*, not by expressiveness:

1. **`gcd(n, c)` / `gcd(a, b)` over a fixed modulus** — first. `gcd(n, c)` is *periodic in n with period c*, so a full-period enumeration is a **total decision procedure**, not a bounded check (see c). High number-theoretic yield, ~5 lines of Euclid TCB.
2. **Bounded `Σ_{i<k}`, `Π_{i<k}`** — second. Computable once `k` is statically bounded; opens `Σi`, `Σi²`, binomial identities. Not periodic in general, so PASS only survives when the *outer* variable is mod-periodic (below).
3. **`⌊√n⌋` (isqrt), `Nat.log`** — third. Exact integer routines, monotone, cheap; claims like `isqrt(n)² ≤ n < (isqrt(n)+1)²`. Bounded-prefix only (no periodicity).
4. **`min/max` over lists** — low yield (structural, not arithmetic), last.
5. **`n!` for bounded n — deliberately deferred.** ADR 0030 Tier C already measured factorial *inert* at the production bound and found the conjecture mix produces zero such claims. Admit the construct only if demand appears; do not add it because it is expressible.

### (b) The sound checker — bounded exact enumeration

For a computable predicate we replace the Z3 gaming-witness search (`find_gaming_witness`, `bound=64`) with direct evaluation of the *actual* function. The gate already searches `claim_domain ∧ ¬claim_property`; the enumeration backend evaluates that same target over a finite set using a closed interpreter (no `eval`) over a fixed, total operator set. **Any x satisfying it is a genuine gaming witness → FAIL — exact, at any bound.** This asymmetry is the whole point: refutations are always sound; only *acceptance* is ever bounded. A PASS emits a `Certificate(kind="exact-enumeration", ...)` bound to a hash of the exact `(domain, predicate, range)` evaluated; the gate's registered `CertificateRechecker` re-derives and re-runs it independently. A self-reported pass with no matching re-checker is not a pass — the ADR 0037 discipline holds unchanged.

### (c) Posture and its limits — bounded vs. exact

A finite-prefix PASS is bounded *exactly like today's Z3 bound=64*: it can miss a witness beyond the prefix (real — Pólya-type first counterexamples are astronomical). We therefore adopt the **strongest defensible posture: the enumeration backend PASSes only when the check is EXACT — a fully-enumerable finite domain, or a full residue period — and otherwise FAILs (witness found) or DEFERs. It never issues a merely-bounded PASS.** This means the backend *cannot* weaken the boundary: it only adds exact decisions and sound refutations. Periodicity is the escape hatch: for a single free `n` whose only `n`-dependence enters through `n mod m` (fixed m) — precisely the mod-arithmetic laws Leibniz already originates — the predicate has period m (or lcm of the moduli), and enumerating `{0..m-1}` decides *all* n. That is a genuine soundness *upgrade* over bounded Z3 for the existing law class, and it should be the gate's preferred path.

### (d) This is trust-critical — adversarial review gates the merge

Enumeration grows the TCB (the interpreter + the periodicity-deriver), which `tests/test_invariants.py` does not guard — the same honest exposure ADR 0035 §3 flagged. Per the ADR 0021/0030/0037 precedent it must clear a ≥3-lens adversarial soundness review (the ADR 0051 slot) before merge, red-teaming at minimum: **vacuity/non-discriminating controls** (empty domain or trivially-true property → false PASS; require ADR 0020/0022 non-vacuity + positive controls the checker MUST fail and MUST DEFER); **periodicity spoofing** (backend claims period m smaller than the true period → the *gate*, not the backend, must independently derive m from expression structure); **evaluator poisoning** (attacker-controlled summand diverges or exploits an interpreter bug → static bounds on k and n, hard resource cap, partial/timed-out enumeration is DEFER, never PASS); and **certificate kind-collision/laundering** (ADR 0041) — bind the certificate to the exact statement hash so it cannot be replayed for a weaker one.

---

## 2. Geometric Mathematics for Visual, Verifiable Outputs

Today a Leibniz law is a line of text: a Lean theorem plus a Q.E.D. That is complete but opaque — a human cannot *see* what was certified. A large family of finite mathematics has the property that a kernel- or exact-checkable fact is also a **finite geometric object** with a canonical picture. Expanding into discrete, combinatorial, and computational geometry lets each law carry a rendered figure that is **additive to the code**: a human can check the shape by eye, while the machine still decides the truth. The picture is a faithful *rendering of the certified object*, never a step in the proof. **A picture never decides** — this preserves the trust boundary exactly as `TrustPolicy` enforces it today.

**The split, stated once.** For every domain below the object is a finite dataset (coordinates, an incidence relation, an adjacency matrix, an edge list). The **certificate** is that dataset plus the exact/kernel check of its defining property; the **visual** is a deterministic pure function of the certificate that asserts nothing new.

| Domain | Kernel/exact-checkable (the certificate) | The visual only illustrates |
|---|---|---|
| Convex polytopes & f-vectors | Vertex/facet data over ℚ; Euler relation, f-vector, face lattice (exact LP / `polymake`) | Schlegel diagram, 3D net — combinatorics, not metric truth |
| Lattice polytopes / Ehrhart | Ehrhart quasi-polynomial coeffs, h*-vector by exact lattice-point enumeration | Lattice points inside the rendered polygon/polytope |
| Tilings & aperiodic sets | Matching rules + a substitution/inflation step verified combinatorially (hat/spectre style) | A finite rendered patch; the patch is not a proof of aperiodicity |
| Sphere packings / kissing | Pairwise inner products of a point set; min-distance & count checked exactly (we already did k(19)) | Contact graph drawn on the sphere |
| Finite projective/affine geometry | Incidence relation over 𝔽_q; every 2 points on 1 line, etc. (finite enumeration) | Fano-plane point–line diagram (the curved "line" is cosmetic) |
| Strongly/distance-regular graphs | Adjacency matrix; SRG parameters (v,k,λ,μ), spectrum, or non-existence (`sage-drg`, ties to our srg work) | A drawn graph layout |
| Root systems & reflection groups | Root vectors, Cartan matrix, Weyl-group orbit closure (exact linear algebra) | 2D projection (Coxeter plane) |
| Unit-distance / equiangular lines | Gram matrix with entries in {±c}; rank/eigenvalue bounds exact | Point configuration with unit edges drawn |
| Origami / rigidity | Rigidity/stress matrix rank, flat-foldability constraints (exact) | Crease pattern / folded state |

**Rendering pipeline.** One direction only: *exact witness → figure*. (1) The exact/enumeration procedure emits the certified object as exact coordinates (ℚ, or algebraic numbers as minimal polynomials). (2) A pure, deterministic renderer maps it to a vector artifact — **SVG/TikZ for 2D** (Fano plane, Schlegel diagrams, graph layouts, crease patterns), **Asymptote or three.js for 3D/4D** (polytope nets, contact spheres, Coxeter projections). Floating-point appears *only* in the final rasterization for the eye; every certified quantity stays exact upstream. The renderer is total and side-effect-free so the figure is reproducible from the witness alone.

**Pinning the visual to its certificate.** Reuse the mechanism already in the code. `scripts/amplify.py::_witness_hash` takes an order-insensitive content hash of a witness; `sound_backends.Certificate` already carries a `rechecked` witness with a `kind` and `data`. Extend `law_payload` (ADR 0050 provenance shape) with a **report-only** `figure` block: `{kind, svg_ref, witness_sha}` where `witness_sha` hashes the *same* canonicalized exact object the certificate checked. The figure is valid iff its hash matches the certificate's witness hash — so a figure can never drift from, or silently outrun, the thing that was proved. Like `tier`/`origination`, this is never consulted by the gates, `kernel_verified`, or `promulgate`; it only makes the ledger *legible*. Rendering runs strictly after promulgation, so no drawing code sits on the trust path.

**Why this is the right expansion now.** The diagnosed ceiling is the Z3-decidable elementary-arithmetic DSL; these geometric facts are *finite and exact-decidable by enumeration/linear algebra*, sidestepping the DSL limit while staying inside the "mechanical checker decides" invariant — and they yield the visual artifacts that make published laws communicable.

---

## 3. Toolchain — Specialized Capabilities to Add (incl. Leanstral, SageMath)

The trust model sorts every external tool into exactly one of three roles, and the sorting — not the tool's power — is what matters:

- **DECIDE** — exact or certificate-producing procedures whose output can be independently re-checked (ideally by the Lean kernel). Only these may reach a *promulgated* law.
- **COMPUTE** — heuristic or unverified engines. Proposal-side only: they suggest conjectures and lemmas; a DECIDE tool or the kernel must then settle the claim.
- **ILLUSTRATE** — rendering. Never touches truth; decorates a law that already passed the gate.

The highest-leverage additions are the ones that **enlarge decision power without enlarging the trusted base** — tools that emit a certificate a small, verified checker validates. Ranked by that criterion:

**1. Kissat / CaDiCaL + DRAT→LRAT (cake_lpr).** Unlocks: finite combinatorics stated as SAT/UNSAT — Ramsey-type bounds, packing/covering, existence over all colorings of a finite structure. *Decides* unsatisfiability; the DRAT proof trims to LRAT and is checked by **cake_lpr**, verified down to x64 machine code (HOL4/CakeML). This is the cleanest possible fit: an adversarial engine we need not trust, backed by a certificate stronger than our own kernel path. Directly attacks the novelty ceiling by opening a vast combinatorial territory with kernel-grade evidence.

**2. nauty/Traces + gtools (geng).** Unlocks: graph theory — degree/spectral/coloring invariants, exhaustive facts over *all* non-isomorphic graphs on n vertices. *Decides* isomorphism and exhaustive finite-class enumeration; the canonical label **is** the certificate, and isomorph-free generation feeds the novelty gate directly (no re-deriving the same graph twice). Adjacent to the existing sage-drg workflow, so integration cost is low.

**3. PARI/GP + FLINT.** Unlocks: number theory the current DSL forbids — gcd, factorization, multiplicative order, class numbers, quadratic residues. *Decides* via exact bignum arithmetic; primality carries a **checkable ECPP/APRCL certificate** (Pocklington/Pratt-style) the kernel can replay. This is the most direct sound attack on the diagnosed DSL ceiling: it adds the forbidden primitives *with* a soundness story, rather than by trusting Z3 outside its fragment.

**4. Macaulay2 / Singular (Gröbner).** Unlocks: commutative algebra and polynomial systems — ideal membership, elimination, multivariate identities. *Decides* membership; the **cofactor / Nullstellensatz certificate** (1 = Σ rᵢpᵢ, or g = Σ pᵢfᵢ) is validated by Lean's `linear_combination`. This is exactly the **polyrith** pattern already partly wired through SageMath: the CAS computes, the kernel checks. Zero new trusted code.

**5. cvc5.** Unlocks: SMT territory beyond Z3 — strings/sequences, datatypes, stronger nonlinear and quantifier reasoning — i.e. a richer *faithfulness-gate contract language*. *Decides* within its theories and emits **Lean 4 / LFSC / Alethe** proofs checkable by native Lean, the LFSC checker, Carcara, or SMTCoq. Runs as a second SMT opinion; disagreement with Z3 is itself a useful refutation signal.

**6. GAP.** Unlocks: finite and computational group theory — character tables, small-group enumeration, permutation-group orders. *Decides* exact algebraic facts for finite structures, but its certificate story is weaker than the above (results are exact yet not natively kernel-replayable), so most GAP output is **proposal-side** unless it is an exhaustive enumeration we can independently confirm. Ranked sixth for that reason, despite large territory.

**Second tier (proposal- or corroboration-side).** Qhull/CGAL and **polymake** give exact-rational convex hulls, f-vectors, and lattice-point counts — CGAL/Qhull can *decide* exact geometric predicates and belong on the promulgation side; polymake's exact backend supports Ehrhart/face-lattice claims. **Vampire/E** are first-order ATPs for proposal-side lemma mining (proofs are reconstructable, Sledgehammer-style, but treat as COMPUTE until replayed). **Isabelle/HOL** and **Metamath** extend the report-only cross-kernel corroboration already run for Rocq — Metamath's tiny verifier makes its proofs an unusually strong independent witness. **OEIS** is a retrieval source for the novelty gate (COMPUTE — a hit is evidence of prior art, not a decision).

**Illustration only.** TikZ, Asymptote, manim, and three.js render polytopes, graphs, and modular patterns for the *Calculemus* reading room. They must remain strictly downstream of the publish gate and can never influence `kernel_verified`.
---

## 4. Consolidated questions for the fleet

**On raising the faithfulness ceiling (§1) — soundness-critical**

S1. Is the 'exact-only PASS' posture (never issue a bounded PASS; bounded search is refutation-only and yields FAIL-or-DEFER) the right conservative default, or does it throw away so much yield that a tiered bounded-PASS — promulgated at a strictly lower trust tier with the bound recorded — is worth the added residual false-FAITHFUL risk?
S2. For periodicity to license an EXACT pass, the gate must independently DERIVE the period from expression structure rather than trust the backend's asserted m. Is a syntactic derivation (only mod-by-constant and whitelisted periodic ops contribute; any raw n or unbounded op ⇒ non-periodic) sound and complete enough, or are there constructs (nested mod, gcd(n,c) interacting with n^k % m, lcm of several moduli) where the true period exceeds the naive one and a false EXACT pass slips through?
S3. The enumeration certificate re-check re-runs the same interpreter, so it defeats a lying backend but not a wrong interpreter — the evaluator is irreducibly TCB. Is a single hardened interpreter acceptable, or should the re-checker use a second, independently-implemented evaluator (or cross-check against the Lean kernel via a `decide`/`Nat.rec` bridge) for the constructs that will actually promulgate laws?
S4. gcd is proposed first because gcd(n,c) is periodic and thus exactly decidable. Do you agree gcd + full-period enumeration is the highest-value first increment, or does bounded Σ/Π unlock materially more novel laws despite only ever yielding bounded (hence, under our posture, DEFER-not-PASS) results?
S5. What is the minimum set of positive/negative and DEFER controls the ADR 0051 adversarial review must include to prove the checker is discriminating (fails known-false conjectures, DEFERs non-periodic claims, refuses vacuous domains) rather than a rubber stamp — and should any of these become permanent regressions in test_invariants-adjacent suites?
S6. Should Leanstral 1.5, once wired as a proposer, be steered to emit only claims inside the enumeration-decidable/periodic fragment (mirroring the ADR 0022 conjecturer-contract-encodability steering), or is it acceptable for it to propose outside the fragment and rely on the gate to DEFER — accepting a higher DEFER fraction as the cost of exploration?

**On geometric / visual, verifiable outputs (§2)**

G1. Trust boundary: is a report-only `figure` block on `law_payload` (hash-pinned to the certificate witness, never read by gates/`promulgate`/`kernel_verified`) the right shape, or should figures live entirely outside the ledger to remove any doubt that a picture influences promotion?
G2. Renderer trust surface: the renderer is a pure witness→SVG function that decides nothing, but it is new code shipped alongside laws. Do we need it sandboxed/attested (it consumes exact witnesses), or is 'renders after promulgation, off the trust path' sufficient?
G3. Which 2-3 domains should be the beachhead? Candidates that reuse existing tooling: SRG/DRG non-existence + drawn graph (leverages our srg work + sage-drg), finite projective planes / Fano (pure finite enumeration), and kissing/contact graphs (we already certified k(19)).
G4. Canonicalization for hashing: `_witness_hash` is order-insensitive for code words; geometric objects need a canonical form up to the symmetry group (relabeling, isometry, projective transform) so the same certified object always hashes identically. Do we canonicalize to an orbit representative, or hash the raw emitted coordinates and accept multiple hashes per object?
G5. Exact-coordinate representation: standardize on ℚ only, or admit algebraic numbers (minimal polynomial + isolating interval) so root systems, equiangular lines, and unit-distance graphs with irrational coordinates are expressible?
G6. For aperiodic tilings the certificate is the matching rules + one substitution step, but a rendered patch is inherently finite and proves nothing about aperiodicity. How do we caption/label such figures so a reader never mistakes an illustrative patch for the certified claim?

**On the toolchain (§3)**

T1. Certificate replay vs. re-derivation: for PARI/GP ECPP and Macaulay2/Singular Gröbner cofactor certificates, do you favor a full in-kernel Lean replay of the certificate, or a verified standalone checker (cake_lpr-style) treated as a peer kernel? Where is the soundness/effort line for each?
T2. For SAT, is Kissat+cake_lpr the right stack in 2026, or would you route through a different solver/checker (CaDiCaL, or LRAT via drat-trim → verified Coq/Lean checker)? Any experience with proof sizes blowing up on the combinatorial claims we'd target?
T3. cvc5 as a second SMT engine: should it run in parallel with Z3 as an independent DECIDER (both must agree), or only as a proposal-side widener of the faithfulness-gate contract DSL? Which cvc5 proof format (Lean4 native vs Alethe/Carcara vs LFSC) has the most robust checker today?
T4. What is the cleanest way to let nauty/geng exhaustive enumeration count as a DECISION rather than a heuristic — i.e., how do we bound and attest 'we generated all non-isomorphic graphs on n vertices' inside the trust boundary?
T5. Which capabilities are we missing entirely? Candidates on our radar but unranked: Flint/Arb interval arithmetic for verified real inequalities, lrs/Normaliz for exact polyhedral/lattice counting, Walnut for automatic-sequence decision, msolve for real solving. Which would you prioritize?
T6. Integration pattern: should each new tool be a sandboxed subprocess adapter emitting a typed EdgeEvidence with an explicit TrustTier (MECHANICAL only when a certificate is kernel-checked), mirroring the existing verifiers.py contract — or do some of these warrant a distinct gate stage? Any anti-patterns you've hit wiring CAS/ATP tools into a trust-gated pipeline?

---

## 5. How to respond

Please weigh in wherever you have signal — you need not cover everything. Most useful, in priority order:

1. **Adversarial soundness critique of §1.** This is the one proposal that touches the trust boundary (the faithfulness gate + a new exact-enumeration backend and periodicity-deriver, both of which grow the trusted base). Treat it as a red-team target: find the preamble/predicate/period that yields a false EXACT-PASS, or show the "exact-only PASS" posture is either unsafe or so yield-starved it is not worth building. This proposal will not be implemented until it clears a formal ADR-0051-style review — your critique feeds that review directly.
2. **A beachhead for §2 and §3.** If we do *one* geometric-visual domain and add *one* specialized tool next quarter, which pair compounds best? (Our instinct: SRG/DRG non-existence + a drawn graph, on the back of the existing `sage-drg` workflow.)
3. **What we're missing.** Libraries, checkers, certificate formats, decision procedures, or whole mathematical territories not mentioned here — especially anything with a *checkable certificate* story that enlarges what can be *decided* without enlarging what must be *trusted*.
4. **Leanstral.** How should a strong Lean proposer change the strategy — steer it to stay inside the decidable fragment, or let it range and lean on the gate to DEFER? Does a second proving model change the calculus on any of the above?

Reply in-line by section, or as a ranked list of recommendations. Dissent is the point.

*Calculemus.* — LLMs propose; the kernel decides.

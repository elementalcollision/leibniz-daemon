# External open-problem corpus — a Leibniz tractability ledger

Two external open-problem sources, scored by what the Leibniz kernel can actually decide.

**Source 1 (primary).** Cahen, Fontana, Frisch, Glaz, *Open Problems in Commutative Ring Theory* (Springer, 2014;
arXiv/preprint Dec 2013). 44 problems (many with sub-parts a/b/c), contributed by the volume's authors and
editors. This is the catalog the `Pengbinghui/pipeline-math` repo drew from (its Problems 4b, 20, 27b, 30c).

**Source 2.** The Erdős problems database ([erdosproblems.com](https://www.erdosproblems.com), ~1000 problems) —
assessed in its own section below. Verdict up front: mostly *asymptotic* (kernel-undecidable), with a
finite/combinatorial tractable subset and a statement-formalization lane.

**Why this belongs on the Leibniz roadmap.** Leibniz's demonstrated strength (this cycle) is *kernel-verifying
counterexample- and construction-based resolutions with a finite / exact-algebraic / decidable core* — LLMs
propose the object, the Lean kernel decides. We independently audited **and** `lake build`-re-verified the four
pipeline-math formalizations (all FAITHFUL + sorry-free + clean axioms), and kernel-verified a COLT-2021
refutation's algebraic core (catching a paper erratum in passing). This paper is a **44-entry backlog** of the
same shape: the ones with a finite counterexample or a divisibility / factorial / monomial / lattice computation
are directly in reach; the homological / asymptotic / infinite-structure ones are not.

This ledger scores every problem by that lens and records the additive-value type — **prove** (attack an open or
partial case), **expound** (kernel-formalize a known resolution), **create** (a reusable certificate / instrument),
**mutate** (generalize or vary an existing resolution).

---

## Tiers at a glance

Tractability is *for in-session Lean/Mathlib kernel work*, not mathematical difficulty.

### Tier A — directly Leibniz-tractable (finite / exact / decidable core)

| # | Problem (short) | Shape | Additive-value angle |
|---|---|---|---|
| **9** | McCoy: integrally-closed reduced non-McCoy, locally McCoy | finite counterexample ring | prove / create |
| **10** | reduced rings with (a.c.)+(A_n) not McCoy | finite counterexample ring | prove / create |
| **16** | other "natural" self-ordered integer sequences | pure divisibility on ∏(a_n−a_k) | prove / create (certify + refute) |
| **17** | subsets E with {n!_E} not ultimately strictly increasing | exact Bhargava-factorial computation | prove / create |
| **24** | Int(E,ℤ) for 2nd-order recursions (basis / char. seq / asymptotics) | exact per-prime computation | expound / create |
| **30a** | is every n-absorbing ideal *strongly* n-absorbing? | finite ideal counterexample (n≥3) | prove / mutate (extends pipeline-math 30c) |
| **30b** | for n-absorbing I, is rad(I)ⁿ ⊆ I? | finite ideal counterexample (n≥3) | prove / mutate |
| **41** | classify (a,b,c): all powers of \\(\overline{(x^a,y^b,z^c)}\\) integrally closed | monomial / Newton-polyhedron lattice computation | prove / create (classification) |

### Tier A′ — already resolved by pipeline-math; independently kernel-verified by us

| # | Problem | Our verification |
|---|---|---|
| **4b** | finite-conductor ⇏ quasi-coherent | FAITHFUL + `lake build` PASS, clean axioms |
| **20** | θ₂ neither injective nor surjective | FAITHFUL + `lake build` PASS |
| **27b** | Int(A) need not be a ring (finite residue rings) | FAITHFUL + `lake build` PASS |
| **30c** | absorbingNumber not preserved under R→R[X] | FAITHFUL + `lake build` PASS |

The natural **mutate** here: 30a/30b are the same object family as the already-formalized 30c — the Prob30c
Lean scaffolding (`IsNAbsorbing`, `absorbingNumber`, the char-2 counterexample algebra) is a running start.

### Tier B — partially tractable / needs a bounded reduction first

Problems **4a** (ascent of finite-conductor/quasi-coherent to RG), **8b** (k[X₁..Xₙ] weakly quasi-complete —
reduces to a height-one prime intersection condition), **40a–d** (Spec poset order-isomorphism — combinatorial but
infinite posets), **44** (Cutkosky-type ring with multi-Rees-valuation m-primary ideals — a construction).

### Tier C — heavy theory, not in-session kernel-tractable

Problems **1, 2, 3** (Prüfer conditions, weak global dimension), **5, 6, 7** (group-ring homological dimensions,
non-Noetherian complete intersection / Cohen–Macaulay), **11, 12, 13** (divisorial primes, straight/divided
domains), **14, 15** (Krull dim of Int(D), Skolem property), **18** (transcendence of the Bhargava constant e_E),
**19** (Int(D) flat/free), **28, 29** (Prüfer integral closure, rings between a 2-dim Noetherian domain and its
quotient field), **31–39** (projective star operations, Jaffard/locally-Jaffard, Mori & v-stable, finite
t-character, locally tame, non-unique factorization), **42, 43** (integral-closure algorithms, Lipman–Sathaye
tightness).

---

## Deep assessment of the Tier-A candidates

From a parallel analyst pass (per-problem, with a post-2013 literature search). **Three of the eight were already
resolved after 2013** — the literature check earned its keep.

| # | Tract | Rec | Status (post-2013) | Additive-value type |
|---|:--:|---|---|---|
| **41** monomial int-closure | **5** | **STRONG** | OPEN classification; RRV already reduces "all powers" to checking **I and I²**; Ataka–Matsuoka (arXiv:2602.01782, Feb 2026) **verified** — see below | **CREATE** (reusable normality checker) + **PROVE** (certify boundary triples) + **VERIFY** (their Ex. 4.5, done) |
| 16 self-ordered seq. | 3 | MAYBE | OPEN, but "natural" is undefined — headline unformalizable; the *finite periphery* is clean. **Census done** (`scripts/prob16_census.py`): {n³},{n⁴},factorial,Fibonacci,primes refuted (kernel witnesses); **{n²} is self-ordered to N=30** — the earlier "refute {n²}" was wrong, the refutable pure powers are k ≥ 3 | CREATE (`SelfOrdered` predicate + `decide` checker; refute {nᵏ} k≥3, factorial, Fibonacci, primes) |
| 24 recursion Int(E,ℤ) | 3 | MAYBE | OPEN for general (a,b); |b|=1 (Fibonacci/Lucas) known | CREATE (certify characteristic-sequence data for fixed instances) |
| 17 Bhargava factorials | 2 | SKIP | OPEN; no finite kernel-formalizable core | — |
| 30a strongly n-absorbing | 2 | SKIP | **RESOLVED POSITIVELY** (Secord 2023, arXiv:2305.03878) — always true; **no counterexample** | EXPOUND-only |
| 30b rad(I)ⁿ ⊆ I | 2 | SKIP | **RESOLVED POSITIVELY** (Choi–Walker 2016, arXiv:1610.10077) — always holds; **no counterexample** | EXPOUND-only |
| 9 McCoy localizations | 2 | SKIP | **RESOLVED** (Haotian Ma 2026, arXiv:2604.07465) — counterexample exists but **intrinsically infinite** (Akiba/Nagata) | EXPOUND-only |
| 10 McCoy (a.c.)+(Aₙ) | 2 | SKIP | OPEN; core not finite | — |

**Resolved-candidate research (2026-07-04, paper-grounded + adversarially faithfulness-checked).** Before
picking the next domain target, the three *resolved* Tier-A candidates went through a deep-research +
refutation pass. Result: **none is a finite-`decide` counterexample.** 30a and 30b were both settled in the
**positive** direction (the property always holds — nothing to falsify); Problem 9's counterexample is real
but an **intrinsically infinite** Akiba/Nagata construction (infinite restricted products of DVRs), not a
bounded `decide`. Each paper was independently re-fetched and confirmed faithful (verdict `FAITHFUL_BUT_NOT_
DECIDABLE` ×3). Honest takeaway: the counterexample-domain's growth runs through the **open monomial**
questions (Problem 41), not the resolved n-absorbing ones.

**Ataka–Matsuoka (2026) Example 4.5 — INDEPENDENTLY KERNEL-VERIFIED (2026-07-04). ✅** Their Main Theorem
(integrally closed monomial `I ⊆ k[x,y,z]` with `μ(I) ≤ 7` is normal) has a **sharp** bound; the sharpness
witness is `I = closure(x⁷,y³,z²)` — 8 minimal generators, not normal. On the flagship Problem-41 instrument
(extended with a minimal-generator computation) we reproduce **both** facts from the Newton polyhedron and
cross-check them **verbatim** against Example 4.5 — the 8 generators `(x⁷,y³,z²,x⁵y,x³y²,x⁴z,y²z,x²yz)` and
the non-normality witness `x⁶y²z ∈ closure(I²) ∖ I²` — kernel-decided, **axiom-free** (three theorems, each
"does not depend on any axioms"). `scripts/verify_ataka_matsuoka.py`,
`docs/crt/ataka_matsuoka_732_certificate.lean`, `tests/test_ataka_matsuoka.py`; registered in the
counterexample-certificate domain as `monomial_normal {7,3,2}`. Verification-amplification of a Feb-2026
result; no trust surface touched.

**The standout is Problem 41.** Both load-bearing facts are finite and decidable: (1) *Newton-polyhedron
membership* — a monomial `xᵘ` lies in the integral closure of a monomial ideal `J` iff the exponent `u` lies in
`conv(exponents of J) + ℝ≥0ⁿ`, a rational convex-polyhedron / lattice-point test; (2) the *Reid–Roberts–Vitulli
reduction* — in three variables, "all powers of `I` integrally closed" collapses to checking just `I` and `I²`.
So certifying a specific triple is a bounded, kernel-checkable computation. The canonical target is the
Huneke–Swanson counterexample **(4,5,7)**: `I = closure(x⁴,y⁵,z⁷)` has `I²` **not** integrally closed — witnessed
by one monomial `xᵘ` with (a) `u ∈ NP(I²)` via an explicit nonnegative rational convex combination, and (b)
`xᵘ ∉ I²` via decidable coordinatewise non-divisibility against `I²`'s finite generating set. Honest scope:
Leibniz cannot *classify* all triples (that is the open mathematics), but it **can** kernel-attest the finite
decision instrument the whole problem rests on and certify specific triples on both sides of the boundary — a
verified, reusable "is (a,b,c) normal?" checker. Frame as *certified instances*, not a competing classification.

---

## Second source — the Erdős problems database (erdosproblems.com)

A far larger backlog (~1000 problems). **The same split applies, and it is the decisive filter:** the database is
dominated by *asymptotic analytic* statements (`≪`, `o(1)`, `limsup`, density) that — in the words of the site
itself — *"cannot be resolved with a finite computation."* Those are exactly what the Leibniz kernel **cannot**
decide. The tractable subset is the **finite / combinatorial / exact** problems (e.g. tiling and covering
questions like Erdős 477, which pipeline-math already wrote up), plus a formalization lane the site explicitly
invites via its per-problem **"Formalised statement? — Create a formalisation here"** field.

**Worked example — Erdős 367** (Erdős–Graham 1980). *Let `B₂(n)` be the 2-full part of `n` (product of prime
powers `pᵃ ‖ n` with `a ≥ 2`). Is `∏_{n≤m<n+k} B₂(m) ≪ n^{2+o(1)}` for every fixed `k`?* Status: **OPEN,
asymptotic — not finitely resolvable**, so *not* a Leibniz solve target. What Leibniz *did* add, honestly:

- **A faithful Lean formalization of the statement** (`docs/erdos/erdos_367.lean`): `B₂` as
  `n.factorization.prod (fun p a => if 2 ≤ a then p^a else 1)`, and the conjecture in both the `n^{2+o(1)}` and
  the stronger `≪_k n²` forms. Elaborates cleanly; `B₂` `#eval`-checked on witnesses (9800↦9800, 9802↦169,
  12↦4, squarefree 30↦1). This is directly the site's requested "create a formalisation" contribution.
- **Certified exact data** on the phenomenon: van Doorn's note (`≪ n²` holds trivially for `k ≤ 2`, fails for
  `k ≥ 3`) is reproduced by exact integer computation — e.g. at `n = 9800`, `B₂(9800)·B₂(9801)·B₂(9802) =
  9800·9801·169` (the powerful pair 2³5²7², 3⁴11², times 13²) is **169·n²**, while every `k ≤ 2` window stays
  `≤ ~n²`. Amplification-grade data, not a proof.

**Takeaway for the roadmap:** the Erdős DB's additive-value lane for Leibniz is (i) **statement formalization** at
scale (faithful Lean statements + a faithfulness gate), and (ii) attacking the **finite/combinatorial** subset —
*not* the asymptotic bulk. A scouting pass (like the CRT one above) can tag the DB's problems by that filter.

---

## Additive-value plan (prove / expound / create / mutate)

Ranked by measured tractability × additive value across both sources:

1. **CREATE + PROVE — Problem 41 monomial-normality certificate (flagship) ✅ DONE (#276).** A reusable Lean
   instrument (`scripts/prob41_normality_lean.py`, `docs/crt/prob41_457_certificate.lean`,
   `tests/test_prob41.py`): Newton-polyhedron lattice-membership witness + `I²`-exclusion, keyed on the RRV
   `d=3` reduction. The **(4,5,7)** non-normality boundary point is **kernel-decided, axiom-free** ("does not
   depend on any axioms") in both the collapsed and direct forms, witnessed by `x²y⁴z⁵ ∈ closure(I²) ∖ I²`; the
   reusable `certify(a,b,c)` checker classifies (4,5,7) not-normal and (3,3,3)/(2,3,5)/(1,1,1)/(4,5,6) normal.
   A genuine new instrument on a still-open classification (certified instances, not a competing classification).
2. **CREATE — a counterexample-certificate *domain* ✅ Tier-1 DONE (`scripts/counterexample_domain.py`).** A
   sibling of the shipped process-complexity and code-bound domains: one `certify(object)` interface over the
   finite/exact-decidable counterexamples, each object certified by a kernel-`decide`-able Lean cert.
   **Tier-1 families shipped** — `monomial_normal` (Problem 41), `self_ordered` (Problem 16: refute {n²}/{n³},
   positive base families), `n_absorbing` (Problem 30: absorbingNumber of ⊥ in ℤ/m); 7 objects certified, every
   emitted cert kernel-verified (monomial + n-absorbing axiom-free, self-ordered standard axioms). **Tier 2**
   (the attested infinite-ring pipeline-math counterexamples 4b/20/27b/30c) is deliberately *out* of the domain
   for now and fully scoped in `docs/t9-tier2-attested-scoping.md` (they are `lake build` attestations, not
   `decide` — the "download" is a reproduction recipe + pins against the public repo, not a self-contained file).
3. **EXPOUND — independent kernel attestation of published resolutions.** Already done for pipeline-math's four
   (audit + `lake build`); extend to the now-resolved 30a/30b/9 (formalize the known counterexamples/proof cores).
4. **CREATE — Erdős statement-formalization lane ✅ SHIPPED (`scripts/erdos_formalize.py`).** Faithful Lean
   statements of Erdős problems (NOT solutions — the DB is mostly asymptotic and kernel-undecidable), each
   passing the **faithfulness gate** (elaborates + a faithfulness anchor + a non-vacuity note). Two exemplars
   pass: **367** (an OPEN asymptotic 2-full-part bound; statement + `B₂` anchors) and **477** (the thirteenth
   powers have a tiling complement — a resolved combinatorial problem, `IsTilingComplement` + a `tiling_sanity`
   anchor; a bridge to the counterexample domain). **Not** submitting to erdosproblems.com (their AI-contribution
   policy); the 477 statement was sourced from the public pipeline-math paper, not the site. A scouting pass over
   a chosen batch is the remaining growth step (operator picks the slice).
5. **MUTATE — extend the Prob30c scaffolding.** 30a/30b share `IsNAbsorbing`/`absorbingNumber` with the
   already-formalized 30c; the resolved answers can be formalized on that running start.

**First demonstration ✅ DONE:** Problem 41 (4,5,7) — the single highest tractability × additive-value target
across all three external sources — is kernel-certified non-normal (axiom-free), shipped in #276 as a reusable
`certify(a,b,c)` instrument. *Next candidates:* the counterexample-certificate **domain** (item 2) and the
Erdős statement-formalization lane (item 4).

---

## Honest disposition

This is an **audit / verification-amplification** track, consistent with the post-R6 roadmap: the discovery EV of
*autonomously* resolving an open problem is low (the binding constraint is the mathematics, not the kernel), but
the **amplification** EV is real and measured — independent kernel attestation of published resolutions, a
reusable counterexample-certificate domain, faithful statement formalizations, and the faithfulness/erratum
instrument (which already caught a real erratum in a COLT paper). The literature-status check matters: **3 of the
8** commutative-ring candidates were already resolved after 2013, and the Erdős headline (367) is asymptotic and
*not finitely resolvable* — surfacing those honestly is itself part of the value (we don't flail at problems the
kernel can't decide). No trust surface is touched; every artifact is read-only and kernel-decided.

<!--
M1 measurement finding (ADR 0036 §10.4/§10.5). The first of the round-2 "measure-before-build"
pre-tests. Self-contained record: what was measured, the defect the adversarial pass caught and
how it was corrected, the honest result, and what it does and does not establish. Harness:
scripts/measure_compression.py (stdlib only, reads .leibniz-ab/{A,B,SA}/memory.db read-only;
no DB writes, trust boundary untouched). Reproduce: `python3 scripts/measure_compression.py`.
-->

# M1 — Proof-Compression Δ: is abstraction mining even alive?

**Status:** measured, 2026-06-25. **Verdict: ALIVE-but-floor.** Abstraction mining is a
*mechanically viable* lever on the existing corpus (the GLM kill does not fire), but the
dominant mined abstraction is the textbook genre, and the test is a **floor on viability, not a
ceiling on headroom**. Feeds ADR 0036 §11.

## Why this experiment

ADR 0036 §10.4 (round-2 external review) promoted **abstraction mining** — emitting
*definitions / lemma-schemas that compress the reasoning space* — to the leading novelty
candidate, on the argument that the untouched lever is **representation**, not faithfulness. GLM
gave the cheap falsifiable pre-test: run a compressor over the daemon's existing proof corpus.

> KILL: 0 macros compress → the proofs are structurally disjoint noise → abstraction mining is
> dead. ALIVE: a macro compresses many → it is the candidate; promote it to a definition.

This is the cheapest decisive measurement in the whole program: it uses data we already have
(47 distinct promulgated, kernel-verified proofs across the A/B/SA calibration arms) and touches
**nothing** in the trust boundary.

## What was measured

Two levels (harness `scripts/measure_compression.py`):

- **Statement level** — anti-unify each formal claim (`claim_property`) into a schema (kind +
  monomial structure; coefficients/modulus/residues are per-law parameters), MDL = tokens.
- **Proof level** — compress the tactic proofs (`proof_src`) with raw DEFLATE as a
  Kolmogorov-complexity proxy, and ask whether the corpus shares structure **across** proofs.

## The defect the adversarial pass caught (and the correction)

The first cut measured a "within-proof token-shuffle null" and reported a **+1.51 cross-proof
gain** under an "order-sensitive Kolmogorov-Δ" label. A 6-agent verification workflow (3 skeptics
+ 2 math readers + adjudicator) **unanimously refuted the metric** (the conclusion survived):

- The 32 KB DEFLATE window spans the whole 17.5 KB corpus, so the metric is **order-INsensitive**
  — shuffling the order of whole intact proofs moves it only **+0.016**. The "order-sensitive"
  label was wrong; what is actually measured is cross-proof **dictionary/substring** sharing.
- Random within-proof shuffling scatters identical tokens past the match window, so that null
  measured DEFLATE's **anti-locality penalty**, not just loss of structure — inflating the
  headline ~3–5×. (Proof: *sorting* tokens within each proof — also destroys sequence — compresses
  *smaller* than real. Only *random* destruction inflates.)

The harness was corrected to order-honest controls and now **reproduces every adversarial
re-run exactly**.

## The honest result (corrected harness)

| Measure | Value | Reading |
|---|---|---|
| Statement-schema compression (MDL) | **0.486** | statements compress 2×; 43/47 fit two genre-schemas (POLY_MOD 35, POW_MOD 8) |
| **Cross-proof gain** (sum-independent ÷ joined − 1) | **+2.23** | joined corpus is **69% smaller** than compressing each proof alone — real cross-proof sharing |
| …on **raw, un-abstracted** proof text | **+1.58** | not an artifact of the `<N>/<V>/<H>` normalisation |
| …**boilerplate-stripped** (omega/decide/simp/…) | **+1.82** | shared **math schema**, not shared glue |
| …**leave-dominant-cluster-out** (other 25 proofs) | **+1.59** | not one over-sampled genre |
| Structure vs order-0 entropy floor | **+0.44** | conservative lower bound: real LZ77 substring matching (0.70× the floor), not frequency skew |
| **Cross-genre help** (POW→POLY) | **0.07** | ≈0 — within-schema; the compressor finds **no** bridge between the two genres |
| Dominant proof-cluster size | 38/22/10/6 @ thresh 0.70/0.85/0.90/0.95 | threshold-sensitive; report as a curve |

**What the dominant macro IS** (both independent math readers, unanimous: *textbook*): the
finite-ring closure in ℤ/mℤ — to prove `P(n) mod m ∈ S` for all n, case-split `n mod m` into its
residues, reduce the polynomial via the mod-congruences (`Nat.add_mod/mul_mod/pow_mod` or
`mod_add_div`), then discharge each finite case by `decide`. The `a^n mod m` order-laws form a
*separate* cluster (induction on the exponent). Exactly the first-year facts the blind panel
already rated 0-novel.

## What M1 establishes — and what it does not

1. **The KILL does not fire.** Compression is real, large, survives every control. Abstraction
   mining is a **mechanically viable** lever on this corpus — there *is* a reusable macro.
2. **The mined abstraction is the textbook genre.** Promoting it to a definition yields a
   *textbook* definition. So abstraction-mining novelty is gated by **input-corpus diversity, not
   the compressor**: mining a 0-novel corpus recovers 0-novel concepts (GIGO). This is the same
   ceiling relocated to the abstraction layer — **not** an independent escape.
3. **But M1 is a FLOOR, not a ceiling.** A syntactic compressor is *structurally blind* to
   cross-genre/semantic abstraction. It reports **no** POLY↔POW bridge (cross-genre help ≈ 0.07),
   yet both readers *independently* identify a real one: both genres are instances of
   **eventual-periodicity of a residue sequence in the finite monoid ℤ/mℤ** (POLY = the image of a
   polynomial map, period | m; POW = the cyclic orbit of ⟨a⟩, period = the multiplicative order),
   unified by the latent equivalence **residue-membership ⟺ divisibility ⟺ periodicity** and the
   reduction lemma `(P n) % m = (P (n%m)) % m`. The compressor cannot see this because the two
   *proof skeletons* are structurally disjoint despite sharing semantics. So the GLM pre-test can
   confirm viability but **cannot upper-bound mining headroom.**

The decisive open question therefore shifts from *"does a macro compress?"* (answered: yes) to
*"can a mined abstraction reach a concept the input generator did not already name — especially
across a genre boundary the compressor reports as bridgeless?"* — which gzip is structurally
unable to answer. That is M2's job, not another compression probe.

## Provenance / honesty notes

- Every corrected figure is reproduced by `scripts/measure_compression.py` and was independently
  re-derived by the adversarial verifiers (cross-proof 2.23; floor 0.44; order-0 floor 3242 B;
  leave-one-out 1.59; cross-genre 0.07; cluster curve 38/22/10/6).
- The retracted **+1.51 "order-sensitive"** headline is recorded here precisely so the correction
  is on the record, not buried — the same discipline applied to the cycles report (#101) and the
  ADR 0035 §7.1 premise correction.
- Two honest numbers answer two questions and must not be conflated: **+2.23** = cross-proof
  dictionary sharing (sum-independent vs joined); **+0.44** = all sub-frequency redundancy (vs the
  order-0 entropy floor). Both positive, both real.
- Trust boundary untouched: read-only over the ledgers, no `kernel_verified`/`promulgated` writes,
  `tests/test_invariants.py` unchanged.

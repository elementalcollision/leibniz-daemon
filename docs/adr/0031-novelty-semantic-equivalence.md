# ADR 0031 — Novelty: catch known results by equivalence, not just exact hash (Proposed)

- Status: **Layers 1 + 2 implemented** (2026-06-23); Layer 3 **Proposed**. Layer 2 ships as a
  bounded, reversible heuristic (see its section); a period-aware rigorous bound is a follow-up.
- Date: 2026-06-23
- Related: ADR 0001 (novelty = retrieval + decision procedure, NEVER a judge), ADR 0004
  (structured contract), ADR 0021/0030 (the Z3 DSL the equivalence check reuses), ADR 0026
  (conjecturer steering). Targets: `leibniz/corpus.py`, `corpus/known_results.json`,
  `scripts/build_corpus.py`, the CONJECTURE prompt. Non-guarded. Roadmap: Tier 1 / R3.

## Context — the organic run rediscovered textbook number theory

The first organic panel calibration (8 cycles, `LEIBNIZ_REPAIR_PANEL`) promulgated 9
kernel-verified, non-trivial, *distinct* theorems — and an audit of the statements showed
**essentially all of them are classic, not novel.** Cycle 5 alone promulgated five, including:

- `n^5 % 5 = n % 5`, `n^7 % 7 = n % 7`, `n^3 % 3 = n % 3` — **Fermat's little theorem** (p=5,7,3),
- `n^3 % 6 = n % 6` (⟺ 6 ∣ n³−n), `8 ∣ (2n)(2n+2)` (elementary),

and earlier cycles added `n^3+2n ≡ 0 (mod 3)`, `n^3+5n ≡ 0 (mod 6)`, `n^5+4n ≡ 0 (mod 5)` —
all Fermat's little theorem **restated**. The daemon proved Fermat three times and the novelty
gate waved them through. This is precisely the failure R3 exists to prevent (capability-ladder
R3 exit test: "a re-derivation of a known bound → KNOWN"), surfaced live.

**Two root causes**, both in the novelty gate:

1. **Exact-hash matching only.** `CorpusBackend.contains_equivalent` is True iff the
   candidate's elaborator-canonical `formal_hash` *equals* a stored entry's. That catches a
   theorem identical up to α-renaming/notation, but NOT a mathematically-equivalent
   restatement. `n^5 % 5 = n % 5` over ℕ and Mathlib's `ZMod.pow_card` (`a^p = a` in `ZMod p`)
   have entirely different elaborated structure → different hashes → never match. And the
   conjecturer's own restatements (`n^5+4n ≡ 0 mod 5` vs `n^5%5 = n%5`) hash differently too.
2. **A thin corpus.** `corpus/known_results.json` is 34 entries of basic algebra (commutativity,
   associativity, distributivity) + a couple of mod-2 facts. It contains **no** Fermat's little
   theorem, no power-residue (`n^k ≡ n mod m`) facts, no consecutive-product divisibilities —
   exactly the band the conjecturer reaches at a low difficulty target. So even exact-hash had
   nothing to match.

Note: this is **not** a soundness/trust bug — every promulgation is a true, kernel-verified
theorem; nothing false was promulgated. It is a **mission** bug: "novel, tractable,
kernel-proven" — these are tractable and proven but not novel.

## The design tension (why this is delicate)

Novelty must stay **mechanical** — retrieval + a decision procedure, never an LLM judge
(invariant 4). And it cuts both ways:

- **Too lax** (today) → the daemon rediscovers textbooks; the ledger fills with knowns.
- **Too aggressive** → it kills *genuinely novel* results (false KNOWN) and defeats the entire
  point of the daemon.

So unlike the faithfulness gate (where the dangerous error is a wrong UNSAT = vacuous PASS),
here the dangerous error is a **false KNOWN** that suppresses a real discovery. Crucially, a
stricter novelty gate can NEVER cause a false promulgation (it only *demotes*), and KNOWN
candidates are **quarantined, not deleted** (invariant 6) — so an over-eager KNOWN is bounded
and *reversible* by operator review. That asymmetry shapes the decision below.

## Decision — three layers, mechanical, shipped in order

### Layer 1 — Broaden the corpus with the elementary-number-theory families (immediate)

Add the families the conjecturer actually reaches, each stored with BOTH its canonical
`formal_hash` AND a DSL predicate (see Layer 2): Fermat's little theorem (`n^p % p = n % p`
for small primes), the power-residue divisibilities (`n^k − n ≡ 0 mod m` for the standard
(k,m): (3,6),(5,30),(7,42),(3,3),(5,5)…), and consecutive-product divisibilities
(`k! ∣ product of k consecutive`). Extend `scripts/build_corpus.py` to emit them. This is the
stopgap — it makes exact-hash catch the *canonical* forms immediately.

### Layer 2 — Equivalence by decision procedure (the principled fix) — **IMPLEMENTED**

> **Shipped** in `Z3Backend.equivalent`, `CorpusBackend.equivalent_known`, and the
> `NoveltyGate` pass (wired with the existing `SMTVerifier`). An adversarial review confirmed
> the trust posture (no eval surface; only *demotes*, never a false promulgation; inconclusive
> → NOVEL) and found the expected residual: box-equivalence is exact for the natural modular
> class (periodicity) but a contrived predicate diverging only *beyond* the box could
> false-KNOWN. Mitigated by raising the default bound to **1024** (far past any constant the
> conjecturer emits; the in-box divergence is then found and rejected) — verified by a
> regression test. The residual error is one-directional (false-KNOWN only) and REVERSIBLE
> (quarantine, not delete), which is why a heuristic is acceptable here. A rigorous period-aware
> bound (lcm of the moduli) is the follow-up. Inert until the corpus JSON is rebuilt with the
> Layer-1 predicates.


Give each corpus entry a DSL predicate (`claim_domain`, `claim_property`) and add to
`contains_equivalent`: a candidate is KNOWN if its contract predicate is **Z3-equivalent over
the bounded box** to a curated entry's — i.e. `find_*_witness` finds NO point in `[0, bound]`
where `candidate_property` and `known_property` disagree (a boolean XOR search; reusing the
exact ADR 0021/0030 encoder). This catches restatements the hash misses: `(n^5+4n)%5==0`,
`n^5%5==n%5`, and a stored "Fermat p=5" predicate are all box-equivalent → KNOWN.

Guardrails against a false KNOWN:
- **Match only against the CURATED predicate set** — never "any pair that happens to agree," so
  a KNOWN verdict always means "box-equivalent to a deliberately-recorded known result."
- **Require the signature to be compatible too** (same `claim_type`, and subject/relation
  near-match) before the equivalence search runs — a cheap pre-filter that also bounds a box
  coincidence across unrelated shapes.
- **Use a larger bound** for the equivalence search than for refutation (agreement on a wider
  box is much stronger evidence of true equivalence), and DEFER-to-NOVEL on an inconclusive /
  timed-out / un-encodable search — i.e. only demote to KNOWN on a *conclusive* box-equivalence.
  (If unsure, treat as novel: protect the mission, since the verdict is reversible anyway.)

### Layer 3 — Conjecturer steering away from classic territory (complementary)

ADR 0026-style: name Fermat's little theorem, power-residue facts (`n^k ≡ n mod m`), and
consecutive-product divisibilities as KNOWN territory the CONJECTURE prompt must avoid, steering
toward genuinely novel bands. Proposal-side; reduces the inflow so the gate has less to catch.
Does not replace Layers 1–2 (a determined or unforeseen classic still slips), but cuts the
common case cheaply.

## Why this stays trust-safe

- **No judge.** Layers 1–2 are retrieval + a Z3 decision procedure (invariant 4 intact); Layer
  3 is proposal-side steering, which never decides anything.
- **Cannot cause a false promulgation.** Novelty only demotes; the kernel/faithfulness/N+1
  gates are untouched. The only new failure mode is a false KNOWN, which is conservative for
  ledger purity, bounded by curation + the conclusive-only rule, and *reversible* (quarantine,
  not delete). `gates/novelty.py`'s contract (MECHANICAL edge, no judge) is preserved;
  `tests/test_invariants.py` untouched.

## Consequences

- The gate stops promulgating Fermat-family / elementary-divisibility restatements; the ledger
  trends toward genuinely novel results. Expect the organic run's promulgation count to *drop*
  — correctly (most of the 9 become KNOWN).
- Re-running the audited organic run becomes the regression: those 9 should now be KNOWN.
- The corpus + predicate set is the new maintenance surface; growth is additive and reviewed.

## Validation plan

- **Unit (CI-safe):** the nine audited promulgations (Fermat p=3,5,7; the mod-6/mod-5
  restatements; the consecutive-evens divisibility) are each classified **KNOWN** — by exact
  hash where canonical, by box-equivalence where restated. A genuinely novel control claim
  still PASSes. Box-equivalence soundness: a known and its restatement match; two *distinct*
  claims that merely agree on a small prefix but diverge do NOT (verify the larger bound /
  conclusive-only rule). Un-encodable / inconclusive → treated as NOVEL, never silently KNOWN.
- **Adversarial review** of the equivalence check before merge (false-KNOWN hunt — can a novel
  claim be wrongly demoted?), per the ADR 0021 precedent.
- **Live:** re-run the organic calibration; confirm the KNOWN fraction rises and surviving
  promulgations are genuinely novel (audited).

## Open questions

- The equivalence search only sees claims expressible in the DSL (ADR 0021/0030). Knowns
  outside it (symbolic/﻿functional) still rely on exact hash + curation — acceptable, since the
  conjecturer is itself steered into the DSL (ADR 0022).
- Bound choice for the equivalence search (precision vs cost) — pick empirically; bias toward a
  larger bound since a false KNOWN is the costly direction here.
- Whether to record *why* a candidate was KNOWN (which entry it matched) in the edge detail for
  operator review — likely yes (cheap, aids the reversibility story).

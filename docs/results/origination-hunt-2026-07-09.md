# Origination hunt — the widened fragment, measured (2026-07-09)

**Track:** ADR 0063 Phase 4 (origination) · **Instrument:** `scripts/origination_hunt.py` ·
**Spend:** $0 (mechanical enumeration; no LLM) · **Kernel:** real Lean 4.31 (Docker REPL)

## What ran

A systematic sweep for gate-novel, kernel-provable facts across all **five** kernel-decidable
fragments — including the freshly-landed ADR 0065 power-mod fragment — screening every candidate
through the daemon's own honesty machinery, cheapest first: exact-oracle TRUTH → single-fragment
ROUTE → ADR 0061 coefficient-degeneracy → ADR 0032 `structural_known` (curated corpus) → in-run
signature DEDUP → the real-kernel **`is_trivial` tactic ladder** on the canonical ℤ-box LAW → the
fragment's own LAW proof must **kernel-check** (promulgable-grade).

## The funnel

| stage | count |
|---|---|
| generated (4 parameterized families) | 327 |
| oracle-false | 2 |
| unrouted / cross-fragment | 1 |
| coefficient-degenerate (ADR 0061) | 4 |
| structural-KNOWN (corpus) | **0** |
| duplicate signature (in-run) | 15 |
| **cheap survivors** | **305** (lean_decided 148, power_mod 141, minmax 9, mixed 5, boolean 2) |
| kernel-screened (round-robin, budget 44) | 44 |
| killed by `is_trivial` | 2 |
| LAW unprovable / generator abstained | 2 |
| **GATE-NOVEL + kernel-provable** | **40** |

## The finding — the novelty wall, re-measured on the widened fragment

**Gate-novel, kernel-provable facts are abundant — and every one of them is textbook-derivable.**
The 40 survivors sort into four families, each an instance of one standard theorem:

- **power_mod** (e.g. `2^n % 31 ∈ {1,2,4,8,16}`, `3^n % 16 ≠ 8`): multiplicative-order cycle facts —
  immediate from Fermat/Euler and the order of the base.
- **lean_decided** (e.g. `a·b·(a²−b²) % m` residue facts for m ∈ {3,4,5,8,9,12,16}): the classical
  divisibility family around `6 ∣ ab(a²−b²)`, specialized per modulus.
- **minmax** (e.g. `max²+max·min+min² = a²+ab+b²`): instances of ONE meta-fact — a symmetric
  polynomial in `(max, min)` equals the same polynomial in `(a, b)`. They survive the tactic ladder
  only because the stock tactics lack the order split; the mathematics is a triviality.
- **boolean/mixed** (e.g. `(a²+b²) % 8 = 2 ⟺ both odd`, `(a+b)² % 8 = 4 ⟺ (a+b) % 4 = 2`): the most
  interesting *shape* (characterizations, not bare facts) — still standard quadratic-residue /
  parity arithmetic.

Two structural observations worth recording:

1. **`structural_known` caught 0 of 327.** The curated corpus (13 congruence signatures) is thin
   relative to this space — gate-novelty is CHEAP out here not because the facts are new but because
   the corpus is small. Any origination claim resting on corpus-novelty alone would be hollow; this
   is exactly why ADR 0063's attestation carries the not-absolute-novelty caveat and why the first
   `originated` law is HELD.
2. **The layered gate works as designed**: the ADR 0061 degeneracy check and the kernel `is_trivial`
   ladder each killed candidates the other missed (4 and 2 respectively), and 2 survivors' law
   proofs failed the kernel — every screen earned its place.

## Disposition

- **No origination is claimed.** Per the ADR 0063 decision, the first `originated` law stays held:
  none of the 40 survivors is a discovery, and promulgating one as the daemon's own would
  misrepresent the work. The fail-closed path (`attest_novelty` → discharge → `law_payload(
  origination="originated", …)`) remains ready if a genuinely non-textbook candidate ever arrives.
- **The roadmap's measured conclusion stands, now confirmed a third time and on a wider region:**
  the soundly-checkable ∧ finitely-encodable region is the textbook region. Widening the DSL
  (ADR 0065) raised *reach* exactly as intended — 141 new-fragment facts are now promulgable-grade —
  without changing the novelty picture.
- The productive use of this abundance is the existing one: **amplification** (kernel-attested
  re-decisions of cited results) and, if desired, bulk kernel-proved textbook shelves clearly
  labelled as such — never dressed as originations.

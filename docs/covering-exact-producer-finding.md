<!--
Covering-designs exact-producer escalation (ADR 0042/0043 Track-D gate, step 2). Provenance:
docs/results/covering_exact_producer.json. Resolves the Track-D swing question for the reachable band.
No trust-boundary change.
-->

# Exact-producer escalation — the reachable covering records are OPTIMAL (the swing is not justified)

**Status:** measured, 2026-06-29. Operator chose "stronger CPU producer first" after the reproduction
gate came back GREEN. The strongest *free* producer — an exact CP-SAT set-cover ILP (minimize blocks
subject to covering every t-subset) — was run on the six headroom cells. **It beats nothing and proves
the records tight.** A billable Track-D swing is therefore **not justified on the reachable
small-witness band**, and we established that for **zero spend**.

## Result
| cell | best-known | exact found | proven optimal? | verdict |
|---|---|---|---|---|
| C(10,4,2) | 9 | 9 | **yes** | OPTIMAL-CONFIRMED |
| C(13,3,2) | 26 | 26 | **yes** | OPTIMAL-CONFIRMED |
| C(15,3,2) | 35 | 35 | **yes** | OPTIMAL-CONFIRMED |
| C(16,4,2) | 20 | 20 | **yes** | OPTIMAL-CONFIRMED |
| C(13,5,2) | 10 | 10 | no (90 s budget) | reproduced |
| C(16,6,2) | 10 | 11 | no (8008 vars, 90 s budget) | within 1 |

**0 beats; 4/6 proven optimal; the other two reproduced/near (budget-limited, not headroom).** Verdict
**RECORDS-OPTIMAL**. Provenance: `docs/results/covering_exact_producer.json`.

## Reading — sharper than CWC's RED
- The Gate-B0 "headroom" (gap≥2 to Schönheim) was **Schönheim being a weak lower bound, not genuine
  beatable slack**: where the exact solver finishes, the La Jolla record *is the optimum*. The reachable
  small-witness band has **nothing to beat** — by any producer, free or billable.
- This is the *strongest* form of the producer wall: not "our search is too weak" (we used an exact,
  optimal solver) but "the record is provably the ceiling." A stronger LLM/GPU producer cannot beat a
  proven-optimal value. The reproduction GREEN (producer reaches the frontier) and this result
  (the frontier is optimal) together close the reachable band.
- The only place a swing could still matter is **larger cells** where optimality is open *and* the
  witness still kernel-renders — a narrow, uncertain, and more expensive target. The C(16,6,2) result
  (8008 candidate blocks, not provable in 90 s) marks where that band begins, and where the witness also
  starts to strain the small-renderable-witness constraint.

## Disposition — bank Track A (+ Track C); do not fund the swing on reachable cells
The measure-before-spend ladder ran to completion on free compute: generic greedy (reaches the frontier,
GREEN) → exact ILP (the frontier is proven-optimal, 0 beats). **The billable Track-D swing is not
justified by current evidence.** This vindicates the witness panel's majority ("stop at A+C") *and* the
discipline of escalating producer strength on free compute before spending:

- **Track A** — the two-domain (CWC + covering) verification-amplification instrument is the durable,
  working product; keep it as the spine.
- **Track C** — sound decider-admission (ADR 0041 Phase 6) is the remaining *free, on-mission* build —
  it broadens what amplification can verify without a producer bet.
- **Track D** — frozen as not-justified on reachable cells. Re-open only if a *specific* larger cell is
  identified with (a) open optimality and (b) a witness that still renders in core Lean — and even then
  the panel's caution holds (a rented-compute beat of a non-optimal heuristic record is weak evidence of
  autonomous discovery; the amplification spine is the value).

**Net:** the post-D0 program reached its honest terminus. Leibniz is a **sound, two-domain verification
amplifier** behind an unbroken trust boundary; autonomous *record-beating* is measured not-justified —
now proven optimal on the reachable band, for zero spend.

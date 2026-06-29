<!--
Covering-designs reproduction probe (ADR 0042/0043 gate). Provenance: docs/results/covering_reproduction_probe.json.
Decision-determining for Track D (the producer swing). No trust-boundary change.
-->

# Reproduction probe — GREEN: a generic producer reaches the covering frontier

**Status:** measured, 2026-06-29. The Track-D gate from [ADR 0042](adr/0042-post-d0-program.md) /
[ADR 0043](adr/0043-covering-designs-verifier.md): *can a generic search — the kind an LLM-in-sandbox
would write, not a tuned simulated annealer — REPRODUCE current La Jolla best-known coverings under a
bounded CPU budget?* **Yes.** This unblocks Track D as a *priced, evidence-backed bet* (not the
dead-on-arrival it was in CWC) — while remaining billable and operator-gated.

## What was run
A generic baseline (greedy set-cover + randomized restarts + redundant-block pruning; deterministic LCG
seed; ~seconds/cell) on **10 pre-registered cells** (fixed before running), spanning Steiner-structured
(gap 0 to Schönheim) → harder (gap 2). Every covering reported is validated by `verify_covering`.
Provenance: `docs/results/covering_reproduction_probe.json`; script `scripts/covering_reproduction_probe.py`.

| cell | LJCR best-known | found | gap | status |
|---|---|---|---|---|
| C(7,3,2) | 7 | 7 | +0 | REPRODUCED |
| C(9,3,2) | 12 | 12 | +0 | REPRODUCED |
| C(10,4,2) | 9 | 9 | +0 | REPRODUCED |
| C(13,4,2) | 13 | 13 | +0 | REPRODUCED |
| C(11,5,2) | 7 | 7 | +0 | REPRODUCED |
| C(13,5,2) | 10 | 10 | +0 | REPRODUCED *(gap-2 cell)* |
| C(13,3,2) | 26 | 27 | +1 | CLOSE |
| C(15,3,2) | 35 | 37 | +2 | CLOSE |
| C(16,6,2) | 10 | 11 | +1 | CLOSE *(gap-2 cell)* |
| C(16,4,2) | 20 | 23 | +3 | PLATEAU |

**6/10 reproduced exactly, 9/10 within 2 blocks; 0 beaten; all valid.** Verdict **GREEN** (the
pre-registered rule: ≥ half reproduced and ≥ 4).

## What this establishes — and what it does NOT
- **Establishes (the gate):** a generic producer *reaches the current frontier* on most small cells,
  including gap-2 cells. This is the precondition the witness panel demanded ("frontier reproducibility
  under budget") and the property **CWC lacked** — there the autonomous producer fell short and records
  were advanced only by human algebra. The covering domain is genuinely accessible to the producer.
- **Does NOT establish:** that a swing will *beat* a record. The baseline **reproduced, beat 0** (as
  expected for a generic search on near-optimal small cells). Reproduction ≠ beating. The PLATEAU cell
  C(16,4,2) (+3) is the tell: as v,k grow the generic baseline falls behind — exactly where a *stronger*
  producer (better search / LLM-evolved heuristics / more compute) would have to earn a reduction.

## Disposition — Track D is now a priced, operator-gated bet
The Track-D producer swing was **dead-on-arrival in CWC** (proven-optimal where reachable; records
algebra-locked). In covering designs it is **live**: clean single oracle, renderable small witnesses, a
genuine headroom population (5,460 small-witness gap≥2 cells per Gate B0), and now a producer that
*reaches the frontier*. The swing's open question is sharp and well-posed: *can a stronger producer
reduce a current best-known on a headroom cell (gap≥2, larger v) where the generic baseline plateaus?*

This remains **billable and operator-gated**, and the witness panel's meta-caution stands: a beat that
comes only from renting compute is weak evidence of autonomous discovery; the durable product is still
the two-domain **verification-amplification** instrument (Track A) + sound tool-admission (Track C). The
swing is now a *legitimate, priced experiment* — to be run, if at all, on explicit operator go.

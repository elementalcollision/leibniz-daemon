---
type: Architecture
title: Trust Boundary
description: The load-bearing trust hierarchy of Leibniz — three trust tiers (MECHANICAL, ADVERSARIAL, JUDGED), three decision edges (proof, novelty, faithfulness), and the TrustPolicy that enforces them at promotion.
tags: [trust, trust-hierarchy, trust-policy, trust-tier, faithfulness, mechanical, adversarial, judged]
---

# Trust Boundary

The trust boundary is the load-bearing invariant of the system and the reason the project exists. It encodes the principle "without relying on capricious LLMs" as a property the **code can check**, not a slogan in a README (see the module docstring of `leibniz/trust.py`).

## The three trust tiers

Defined in `leibniz/types.py::TrustTier`:

| Tier | Meaning | LLM trust |
|---|---|---|
| `MECHANICAL` | a kernel or decision procedure | Zero — never an LLM |
| `ADVERSARIAL` | a falsification search; the LLM proposes, the search tries to refute. Failure is constructive (a witness), not a vote | The LLM proposes; the search refutes |
| `JUDGED` | irreducible LLM judgment | Permitted on exactly one edge, minimized, logged, budget-bounded |

## The three decision edges

A `Propositio` (the unit of work and record) accumulates `EdgeEvidence` records as it passes the gates. Three edges are required for promotion (constants in `leibniz/trust.py`):

| Edge | Constant | Who decides | Tier |
|---|---|---|---|
| proof ↔ statement | `PROOF_EDGE = "proof<->statement"` | the Lean kernel | **MECHANICAL** (never an LLM) |
| novelty / non-triviality | `NOVELTY_EDGE = "novelty"` | retrieval + a decision procedure | **MECHANICAL** (never a judge) |
| statement ↔ claim (Enuntiatio) | `FAITHFULNESS_EDGE = "enuntiatio<->statement"` | gaming-witness → claim-probe → judge | **ADVERSARIAL → MECHANICAL → (bounded) JUDGED** |

## The only legitimate producers

`leibniz/trust.py` pins the legitimate producers of mechanical verdicts so a future refactor cannot quietly downgrade them:

- `KERNEL_PRODUCER = "LeanVerifier.discharge"` — the sole legitimate producer of a proof-edge verdict. Any other producer on the proof edge is a mislabel and is rejected.
- `FAITHFULNESS_PRODUCERS` — the operator-owned allowlist of legitimate producers of a MECHANICAL faithfulness edge: `SMTVerifier.gaming_witness`, `ClaimProbe`, `FaithfulnessGate`, `walnut/recheck`. A mechanical faithfulness edge from a producer outside this set is rejected (ADR 0041).
- `JUDGE_PRODUCER = "FaithfulnessJudge"` — the one bounded judged edge. A JUDGED tier that names a judge producer is the only legitimate place a judge may appear; a judged verdict mislabeled MECHANICAL/ADVERSARIAL is rejected.

## How the policy enforces promotion

`leibniz/trust.py::TrustPolicy.validate_path` is called by `leibniz.gates.verification.VerificationGate.is_promotable` before any promotion. It raises `TrustViolation` unless every edge on the path is admissible:

1. **A proof edge must be present and MECHANICAL** — `validate_edge` raises if the proof edge is at any other tier or produced by anyone other than the kernel.
2. **Novelty must not be settled by a judge** — a `JUDGED` novelty edge raises.
3. **A faithfulness edge must be present** — without it there is no promotion.
4. **Every edge must PASS** — a non-PASS edge raises.
5. **JUDGED faithfulness is allowed but flagged** — the one permitted judged edge; it is tracked against the trust budget.

## The judged-faithfulness budget

The fraction of promulgated laws whose faithfulness edge fell back to `JUDGED` is bounded by `TrustPolicy.max_judged_faithfulness_fraction` (default `0.15`). `TrustBudget` (`leibniz/budget.py`) holds the running counts and decides at promotion time whether a judged-faithfulness law may enter the ledger. The arithmetic (`admits_judged_faithfulness`) uses `(judged+1)/(total+1) <= max` — the first judged promulgation on an empty ledger is refused (`1/1 > 0.15`), so judged faithfulness is admitted only once the ledger is large enough to keep the residual under budget. A refused candidate is quarantined `OVER_BUDGET`, never deleted.

## The promotion gate

`leibniz/gates/verification.py::VerificationGate` is a **pure boolean over recorded evidence** — it renders no new judgment and re-runs nothing. `is_promotable` returns `True` iff the three required edges are present, `validate_path` passes, and every required edge PASSes. `finalize` stamps `PROMULGATED` or quarantines with the reason a gate already set (or `UNPROVEN` if the proof simply wasn't found).

See [Trust Invariants](../trust-invariants.md) for the executable tests that turn these rules into CI enforcement, and [Faithfulness Gate](../components/faithfulness-gate.md) for how the one bounded residual is handled.

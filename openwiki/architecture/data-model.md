---
type: Architecture
title: Data Model and Ledger
description: The Propositio triad (Enuntiatio claim, Expressio formal statement, Demonstratio proof) as the unit of work and the unit of record, with ClaimSignature, EdgeEvidence, TrustTier/Verdict, FinishReason, and the SQLite-backed PersistentRuntime that survives restarts.
tags: [data-model, propositio, enuntiatio, expressio, demonstratio, claim-signature, edge-evidence, finish-reason, runtime, sqlite, ledger]
---

# Data Model and Ledger

`leibniz/types.py` and `leibniz/propositio.py` hold the vocabulary. Everything that can be a mechanical check is representable here **without reference to an LLM**, so the trust boundary is enforceable by construction. The `Propositio` is both the unit of work and the unit of record, inherited wholesale from Newton's ledger triad with one deliberate inversion: the `Demonstratio`'s `proof_obligation` is **active** (in Newton it was hardcoded `"not_applicable"`).

## The Propositio triad

```mermaid
erDiagram
    Propositio ||--|| Enuntiatio : has
    Propositio ||--o| Expressio : has
    Propositio ||--o| Demonstratio : has
    Propositio ||--o| ClaimSignature : "signature"
    Propositio }--|| EdgeEvidence : "edges (append-only)"
    Enuntiatio ||--|| ClaimType : "claim_type"
    Expressio ||--o| Walnut : "walnut_predicate"
    Demonstratio ||--|| Qed : "seal"
    EdgeEvidence ||--|| TrustTier : "tier"
    EdgeEvidence ||--|| Verdict : "verdict"
```

*Figure: the Propositio triad and its evidence ledger. A Propositio carries an Enuntiatio (required), an Expressio and Demonstratio (optional, set during the pipeline), a ClaimSignature (structural fingerprint), and an append-only list of EdgeEvidence.*

| Class | Field(s) of note | Role |
|---|---|---|
| `Enuntiatio` | `statement`, `claim_type`, `falsifiable_claim`, `domain`, `claim_domain`, `claim_property` | the claim, for a human reader. The falsifiable condition (Popper). The structured contract (`claim_domain`/`claim_property`) drives the faithfulness gate's mechanical fast path. |
| `Expressio` | `theorem_src`, `imports`, `normalized_hash`, `compiles`, `established_domain`, `proof_hints`, `walnut_predicate`, `walnut_numeration`, `property_descriptor` | the formal statement in Lean 4. `theorem_src` is the statement only; the proof is the `Demonstratio`'s job. `normalized_hash` lets the novelty gate compare structure, not prose. |
| `Demonstratio` | `proof_obligation`, `proof_src`, `kernel_verified`, `qed` | the proof obligation + its discharge. `kernel_verified` is set **only** by `LeanVerifier.discharge`; `qed` is `Q.E.D.` iff `kernel_verified`, else `Q.E.I.` (the `seal()`). |
| `Propositio` | `enuntiatio`, `expressio`, `demonstratio`, `pid`, `born`, `parents`, `signature`, `edges`, `promulgated`, `finish_reason`, `behavior_descriptor`, `seed_origin` | the unit of work and record. `parents` is lineage for KFM recombination; `behavior_descriptor` is the 3-axis MAP-Elites coordinate; `seed_origin` is the producer provenance (mined\|weaken\|kfm\|survey). |

## ClaimSignature — the structural fingerprint

`ClaimSignature(claim_type, subject, relation, formal_hash, properties)` is a machine-comparable fingerprint of what a `Propositio` actually establishes. Used by the novelty gate for dedup and by the faithfulness gate to tie the statement back to a checkable property. **Structural, not textual**, so restatements of a known result collide.

## EdgeEvidence — the audited ledger

`EdgeEvidence(edge, tier, verdict, detail, cost_units, producer)` is the evidence and tier for one trust edge:

- `edge` — one of `PROOF_EDGE` (`proof<->statement`), `FAITHFULNESS_EDGE` (`enuntiatio<->statement`), `NOVELTY_EDGE` (`novelty`), or a non-promotion edge (`walnut_decision`, `cheap_refutation`).
- `tier` — `TrustTier.MECHANICAL` / `.ADVERSARIAL` / `.JUDGED`. The policy reads it.
- `verdict` — `Verdict.PASS` / `.FAIL` / `.DEFER`.
- `producer` (ADR 0013) — who produced this verdict (e.g. `LeanVerifier.discharge`). The policy uses it to catch a tier mislabel structurally, not by honest tagging.

## TrustTier and FinishReason

`TrustTier` — `MECHANICAL` (kernel/decision procedure, zero LLM trust), `ADVERSARIAL` (LLM proposes, search refutes — failure is constructive), `JUDGED` (irreducible LLM judgment, permitted on exactly one edge, minimized/logged/bounded).

`FinishReason` — why a candidate left the active pipeline. Candidates are **quarantined with a reason, never deleted** (invariant 6): `PROMULGATED`, `REFUTED`, `TRIVIAL`, `KNOWN`, `UNFAITHFUL`, `UNPROVEN`, `MALFORMED`, `GAMED`, `OVER_BUDGET`, `WALNUT_DECIDED` (ADR 0038 — a separate non-Q.E.D. tier; never `kernel_verified`/`qed`/`promulgated`).

## The PersistentRuntime (ADR 0016)

`leibniz/runtime.py::PersistentRuntime` makes the body's substrate real: **SQLite-backed memory** so `remember`/`recall_recent` survive restarts, a **clock-based circadian phase** (WAKE/NREM/REM via `phase_for_hour`), and a documented witness seam (returns `[]` until a provider ensemble is wired; the gaming-witness uses Z3, not this path). The DB is opened lazily on first `remember`/`recall`, so constructing a daemon touches no filesystem until it runs.

The `memory` table columns: `pid, born, ts, statement, claim_type, falsifiable_claim, domain, theorem_src, normalized_hash, kernel_verified, qed, proof_src, finish_reason, parents, instance, claim_property, seed_origin`. Migrations are idempotent (`ALTER TABLE ADD COLUMN`). The runtime records a candidate's *disposition* via its `FinishReason` and **deliberately never sets** the policy-gated `prop.promulgated` flag — a recalled memory is a historical record, not a live promotion (enforced by `tests/test_boundary_guards.py`).

`instance` (ADR 0033) is read at call time from `LEIBNIZ_INSTANCE` (default `dev`), stamped on every row, and the write-barrier refuses a ledger already claimed by a different instance. See [Instance Isolation](../instance-isolation.md).

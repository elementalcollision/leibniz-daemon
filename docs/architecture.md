# Architecture

## Organ map

Leibniz is an assembly of four extant systems plus one new organ, bound by a
trust boundary.

```
                          ┌─────────────────────────────────────────┐
                          │              LEIBNIZ (daemon)            │
                          │         circadian cycle / Calculemus     │
                          └─────────────────────────────────────────┘
                                            │ sequences
        ┌───────────────┬───────────────────┼───────────────────┬───────────────┐
        ▼               ▼                   ▼                   ▼               ▼
   ┌─────────┐   ┌────────────┐      ┌────────────┐      ┌────────────┐   ┌──────────┐
   │ LEONARDO│   │  PROVIDER  │      │   GATES    │      │ VERIFIERS  │   │   KFM    │
   │  (eyes) │   │ (proposal) │      │  (decide)  │      │ (the judge)│   │(selection)│
   │ survey/ │   │ conjecture │      │ faithful·  │      │  Lean      │   │ kill/    │
   │ analogy │   │ formalize  │      │ novelty·   │      │  kernel    │   │ recombine│
   │ *TBD*   │   │ proof-draft│      │ verify     │      │  Z3        │   │ commit   │
   └─────────┘   └────────────┘      └────────────┘      └────────────┘   └──────────┘
        │               │                   │                   │               │
        └───────────────┴───────────────────┴───────────────────┴───────────────┘
                                            │ persists / recalls / witnesses
                                  ┌─────────────────────┐
                                  │       CHIMERA        │
                                  │      (the body)      │
                                  │ scheduler · SQLite · │
                                  │ witness · drift      │
                                  └─────────────────────┘
```

- **Chimera (body)** — `adapters.RuntimeAdapter`. Scheduling, persistence, the
  cross-model witness mechanism, drift/trust telemetry. Unchanged substrate.
- **Newton (spine)** — `pipeline`, `propositio`. The six-stage loop and the
  Enuntiatio/Expressio/Demonstratio ledger, kept; Demonstratio backend flipped to
  kernel proof.
- **KFM (selection)** — `selection`. Kill/recombine/commit over a MAP-Elites
  archive.
- **Leonardo (eyes)** — `adapters.LeonardoAdapter`. **Tentative** survey/analogy
  role; confirm against the real Leonardo and rewire this one adapter.
- **Verification (the judge, NEW)** — `verifiers`. Lean kernel + Z3. The organ
  Newton deliberately omitted.

## Data flow through one circadian cycle

```
SURVEY        Leonardo → frontier edges + cross-domain analogies → seeds
                                   │
CONJECTURE    provider(CONJECTURE) → Enuntiatio (+ ClaimType, falsifiable_claim)
              + behavior descriptor for the archive
                                   │
FORMALIZE     provider(FORMALIZE) → Lean statement
              ├─ compile?                         no → MALFORMED ✗
              ├─ cheap_refute (Z3, cost~1)        cx → REFUTED   ✗
              ├─ novelty + non-triviality (cost~1) hit → KNOWN/TRIVIAL ✗
              └─ faithfulness (cost~2-3)
                   ├─ gaming-witness (adversarial) hit → GAMED ✗
                   ├─ claim-type probe (mechanical) fail → UNFAITHFUL ✗
                   └─ judge (OPEN_FORM only, bounded)
                                   │ survivors only
DERIVE        provider(PROOF_DRAFT) → tactic script        (the expensive path)
                                   │
DEMONSTRATE   Lean kernel → kernel_verified ∈ {T,F}; seal Q.E.D. | Q.E.I.
                                   │
PROMULGATE    VerificationGate.is_promotable (pure boolean + TrustPolicy)
              ├─ promotable → Codex (promulgated)           [≠ publication]
              └─ else        → quarantine(reason)
                                   │
SETTLE        archive.consider(quality) · runtime.remember · KFM disposition
```

## Where the trust boundary sits

Everything left of DEMONSTRATE is *proposal* (LLM-permitted) or *cheap mechanical
filtering*. The proof verdict at DEMONSTRATE is mechanical and sole-sourced from
the kernel. PROMULGATE renders no new judgment — it is a pure function of recorded
evidence, checked against `TrustPolicy`. The only LLM judgment that can reach a
promulgated law is an OPEN_FORM faithfulness fallback, and even that is logged and
budget-bounded.

## What is deliberately not here

- No execution-gated "test passes ⇒ true" path (that is Newton).
- No empirical/symbolic-regression Demonstratio (different daemon, different ADR).
- No edge on which an LLM's say-so promotes a result.

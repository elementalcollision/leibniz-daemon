---
type: Reference
title: Glossary
description: The Latin ledger vocabulary and the core terms — Enuntiatio, Expressio, Demonstratio, Propositio, the trust tiers, the gates, Q.E.D./Q.E.I., the Codex, the characteristica, and the KFM/MAP-Elites selection — used throughout the Leibniz daemon.
tags: [glossary, vocabulary, latin, terms, definitions, lexicon]
---

# Glossary

The ledger vocabulary is deliberately Latin (mirrors the sibling repo `newton-daemon`). Every decision attaches an `EdgeEvidence` with an explicit `TrustTier`; the policy and tests read it.

## The ledger triad

| Term | Class | Meaning |
|---|---|---|
| **Enuntiatio** | `Enuntiatio` | the claim, stated for a human reader. Carries `claim_type`, the `falsifiable_claim` (Popper), and the structured contract (`claim_domain`/`claim_property`). The thing the public ledger is held accountable to. |
| **Expressio** | `Expressio` | the formal statement in the *characteristica universalis* (Lean 4). `theorem_src` is the statement only; the proof is the `Demonstratio`'s job. `normalized_hash` compares structure, not prose. |
| **Demonstratio** | `Demonstratio` | the proof obligation + its discharge. `proof_obligation` names what must be proven; `proof_src` is a tactic script the kernel checks. `kernel_verified` set **only** by `LeanVerifier.discharge`; `qed` is `Q.E.D.` iff verified, else `Q.E.I.` |
| **Propositio** | `Propositio` | the unit of work and the unit of record. A `Propositio` carries an `Enuntiatio` (required), an `Expressio` and `Demonstratio` (set during the pipeline), a `ClaimSignature`, an append-only `edges` list, `parents` (KFM lineage), a `behavior_descriptor` (MAP-Elites coordinate), and `seed_origin` (producer provenance). |

## Trust tiers (`TrustTier`)

| Tier | Meaning | Where |
|---|---|---|
| `MECHANICAL` | a kernel or decision procedure. Zero LLM trust. | the proof edge; novelty; the mechanical faithfulness probes; the sound backends. |
| `ADVERSARIAL` | a falsification search. The LLM proposes; the search tries to refute. Trusted because failure is **constructive** (a witness), not a vote. | the gaming-witness spine of the faithfulness gate. |
| `JUDGED` | irreducible LLM judgment. Permitted on exactly one edge (faithfulness), minimized, logged, and budget-bounded. | the OPEN_FORM fallback of the faithfulness gate. |

## The three promotion edges

| Edge | Constant | Decided by | Tier |
|---|---|---|---|
| proof ↔ statement | `PROOF_EDGE` | the Lean kernel | MECHANICAL (never an LLM; `KERNEL_PRODUCER` pinned) |
| novelty / non-triviality | `NOVELTY_EDGE` | retrieval + a decision procedure | MECHANICAL (never a judge) |
| statement ↔ claim | `FAITHFULNESS_EDGE` | gaming-witness → sound backends → claim probe → judge | ADVERSARIAL → MECHANICAL → (bounded) JUDGED |

## Q.E.D. and Q.E.I.

`Demonstratio.seal()` stamps `qed = "Q.E.D." if self.kernel_verified else "Q.E.I."` (invariant 7). `Q.E.D.` is earned by the kernel, never hand-set. `Calculemus.promulgate` admits a law to the Codex **only if** it carries a real kernel-checked `Q.E.D.` (invariant 7, again). The Walnut-decided Observatory tier (ADR 0038) is a **separate non-Q.E.D.** ledger — it never sets `kernel_verified`/`Q.E.D.`/`promulgated`.

## The characteristica

The *characteristica universalis* is Lean 4 (Mathlib). The `Expressio` is the formal statement in this language; the `Demonstratio` is the proof the kernel checks in it. "Without relying on capricious LLMs" means the LLM drafts in the characteristica but only the kernel *decides* in it.

## The Codex and *Calculemus*

- **The Codex** — the daemon's promulgated ledger (`Calculemus.codex`). A law enters it only after a kernel-checked `Q.E.D.` and the `VerificationGate`/`TrustPolicy` pass.
- **Calculemus** — "the reading-room," the public face. The public ledger of theorems settled by calculation, at [codexcalculemus.com](https://codexcalculemus.com) (an Astro static site in the sibling repo `codex-calculemus`). **Promotion ≠ publication**: a law reaches the public ledger only after an explicit operator publish from the PROD instance (ADR 0008/0033).

## KFM and MAP-Elites

**KFM** (Kill / Fuck / Marry) is the quality-diversity selection operator over the conjecture archive (`leibniz/selection.py`): Kill (refuted/trivial/known leave), Fuck (promising-but-unproven are **recombined** into children — the LLM-as-variation-operator), Marry (proven-and-novel are committed to the Codex). The archive is **MAP-Elites**-shaped: the best conjecture per cell of a 3-axis behavior space (sub-area × proof technique × statement complexity), so the search retains diverse stepping stones. Curiosity-biased parent sampling prefers sparse cells to push the frontier outward.

## The circadian cycle

The daemon runs on a slow **circadian cycle**: survey the frontier → conjecture → formalize (cheap gates) → derive → demonstrate (kernel) → promulgate → settle. `PersistentRuntime.now_phase()` returns WAKE/NREM/REM from the clock — the "slow cycle" metaphor.

## FinishReason (quarantine, never deletion)

Candidates are **quarantined with a `FinishReason`, never deleted** (invariant 6): `PROMULGATED`, `REFUTED`, `TRIVIAL`, `KNOWN`, `UNFAITHFUL`, `UNPROVEN`, `MALFORMED`, `GAMED`, `OVER_BUDGET`, `WALNUT_DECIDED`. The ledger keeps the dead as stepping stones for KFM recombination.

## Producer provenance (ADR 0013)

`EdgeEvidence.producer` names who produced the verdict (e.g. `LeanVerifier.discharge`). The policy uses it to catch a **tier mislabel structurally**, not by honest tagging: a proof edge produced by anything other than `KERNEL_PRODUCER` is rejected; a MECHANICAL faithfulness edge produced by anything outside the operator-owned `FAITHFULNESS_PRODUCERS` allowlist is rejected (ADR 0041 ATTACK 2).

## N+1 consensus

**N+1 kernel-verified consensus** (ADR 0006): promulgation needs `min_consensus` *distinct* kernel-verified proofs from **independent provers** (distinct models, not raw passing attempts — a model that proves by two strategies is one voter). It **strengthens** the proof edge; the Lean kernel is still the sole decider.

## The gaming-witness

The adversarial spine of the faithfulness gate: search for an input that **satisfies the formal statement while violating the Enuntiatio**. If such a witness exists, the statement underspecifies the claim → FAIL (`GAMED`). Generative, so it catches gaps a concordance judge waves through.

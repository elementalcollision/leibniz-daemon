---
type: Reference
title: Optimization Roadmap and Discovery Frontier
description: The post-R6 optimization roadmap — the measured conclusion that the binding constraint is novelty (a structural encoding gap at the producer), not prover reach, soundness, or the trust boundary; both the proposal-source and contract-grammar levers were built and measured against a blind 4-rater human novelty panel.
tags: [roadmap, optimization, novelty-frontier, discovery, post-r6, measurement, encoding-gap]
---

# Optimization Roadmap and Discovery Frontier

The capability ladder R0–R6 is built and the daemon runs end-to-end live (`docs/capability-ladder.md`). The remaining work is **making it a productive discovery engine without ever weakening the boundary**. Each optimization is captured as a Proposed ADR so it can be approved deliberately before implementation (the project's discipline: decisions get an ADR, and trust-guarded changes get operator sign-off via the PreToolUse hook).

## The measured conclusion (2026-06-25)

The post-R6 binding constraint was **novelty** — the daemon soundly *re-proves* textbook math but does not *discover*. Two independent levers were then **built and measured** against a blind 4-rater human novelty panel, not argued:

| Lever | ADR | Result |
|---|---|---|
| **Proposal source** (mining true computed patterns vs. steering) | 0034 | Doubled yield (13→26 promulgations); **0 genuinely-novel** laws |
| **Contract grammar** (soundly teach the faithfulness gate `a^n mod m`) | 0035 Stage A | Moved 16/23 promulgations into the new genre; **0 genuinely-novel** laws (standard cyclic-group facts) |

**Triangulated conclusion (refined after a 5-model external review):** the bottleneck is **neither the proposer nor the grammar** — it is the faithfulness **test**: a pointwise, bounded-box `[0,64]` linter over a tiny arithmetic DSL, used as the sole faithfulness arbiter, can only certify elementary, locally-checkable facts. This is **not** a property of mechanical trust in general — a small kernel can check arbitrarily deep proofs (Flyspeck / Feit–Thompson / Robbins), so bounded *trust* ≠ bounded *domain*.

## The escape: proof-carrying faithfulness (ADR 0036 → 0037)

The escape that preserves "nothing false gets `Q.E.D.`" is **proof-carrying faithfulness** — pluggable *sound backends* that decide unbounded/exact classes the box cannot, with bounded Z3 demoted to lint. See [Sound Backends](../components/sound-backends.md). The residual gap then relocates to *validation* (human-intent → formalized-claim), the right and auditable place.

## The sound-backend discovery arc — CONCLUDED (2026-06-26)

| Backend | Class | Outcome |
|---|---|---|
| **Walnut** (automatic-sequence FO) | built, run live | Trust machinery validated end-to-end across 3 runs (3 filed → 2 caught by the ADR 0039 lint → 0 unsound, diverse, faithful). Run-3 = 11 sound, diverse, faithful decided records, **all textbook** (12-agent verification, 0 plausibly-novel). |
| **SOS / Positivstellensatz** | probed, build **deferred** | Soundness + box-out reach GREEN (exact rational re-check stdlib-only; reaches `∀x∈ℝⁿ`; a genuinely-Q.E.D. prover seam exists, unlike Walnut). But novelty go/no-go **RED**: 0/12 in-reach + box-out + plausibly-novel in both arms. |

**Capstone finding (`docs/discovery-ceiling-cross-backend-finding.md`):** across two independent sound backends, the soundly-checkable **and** finitely-encodable region is the **textbook** region. A perfect anti-correlation held — everything in-reach was textbook; everything plausibly-novel left the backend's encodable class. The binding constraint moved one level deeper and is now empirically pinned: **novelty at the producer — a structural encoding gap — not soundness, reach, or prover power**.

## Disposition

The novelty quest is **paused with a measured finding** (ADR 0034 §12, ADR 0035 §7; public account in `docs/cycles-report-novelty-frontier.md`). Both levers remain **sound and opt-in/default-off** — useful as *yield* levers (proving large volumes of true elementary number theory, e.g. seeding a Lean library) if breadth, not novelty, becomes the goal. The full roadmap and the ADRs 0009–0050 that record each decision live under `docs/adr/` and `docs/optimization-roadmap.md`.

## The ADR index (0001–0050)

The decisions that shape the architecture, recorded deliberately (each trust-guarded change gets operator sign-off via the PreToolUse hook):

- **Charter & boundary:** 0001 (charter), 0002 (faithfulness gate), 0013 (trust-edge provenance), 0025 (promulgation integrity), 0041 (tool use/research ingestion), 0049 (public repo hardening), 0050 (law provenance tier).
- **Kernel & backends:** 0003 (R1 Lean container), 0011 (throughput/cost), 0012 (autoformalization robustness), 0037 (modular sound backends), 0047 (large-block PSD trust boundary), 0048 (Coq/Isabelle deciders).
- **Faithfulness:** 0004 (gaming witness), 0010 (probe expansion), 0020 (no vacuous pass), 0021 (widen DSL), 0022 (contract encodability), 0030 (DSL bounded-definitional), 0035 (DSL expressiveness), 0039 (observatory lint), 0040 (CWC triviality carveout), 0046 (f2c observatory).
- **Novelty:** 0007 (Leonardo survey), 0015 (corpus/domain expansion), 0031 (semantic equivalence), 0032 (structural matcher), 0034 (conjecturer-side novelty), 0036 (genuine discovery), 0038 (Walnut observatory tier).
- **Proposal/proof:** 0005 (providers), 0006 (cascaded/witness), 0019 (HF prover), 0024 (lemma decomposition), 0027 (independent decomposition), 0028 (lever-3 prover options), 0029 (agentic repair), 0044 (first decider admission), 0045 (amplification integration).
- **Discovery/selection:** 0009 (open-ended loop), 0018 (frontier), 0023 (persistent notebook), 0026 (nontrivial steering), 0042 (post-D0 program).
- **Ledger/ops:** 0008 (publish tier), 0014 (cost accounting), 0016 (persistent runtime), 0017 (Calculemus site), 0033 (instance isolation), 0043 (covering designs verifier).

The authoritative status lives in `docs/optimization-roadmap.md` and `docs/adr/`; do not trust this page for fine status — read those.

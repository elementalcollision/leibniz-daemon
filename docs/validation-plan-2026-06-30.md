<!--
The cost-tiered testing/soak/validation plan that gates the next implementation decisions in the post-D0
program. Produced by a grounded multi-agent scoping pass (7 parallel subsystem readers -> synthesis ->
adversarial completeness critic; the critic's three hard fixes are folded into the tiers below). VALIDATION
ONLY: no run edits the trust core (leibniz/verifiers.py::discharge, trust.py, types.py, propositio.py,
gates/*, tests/test_invariants.py). Author: agentic pass, operator-approved 2026-06-30.
-->

# Validation plan — post-D0 program (2026-06-30)

The post-D0 instrument is built (Track A amplification spine; B1 covering + B2 Ramsey verifiers; C
scaffolding) and the construction **PROOF-edge is deferred 8/8** (ADR 0045 §10). Before choosing the next
implementation step we run a cost-ordered validation ladder that settles two forks and hardens the
audit-tier guarantees. **Nothing here touches the trust core.**

## The two forks the ladder exists to settle
1. **Does any beatable-AND-renderable covering cell exist beyond the proven-optimal reachable band?** —
   decides whether the dormant `discharge` proof-edge is ever worth un-deferring, or D is dead for $0.
2. **Where does core-Lean `decide` go intractable for coverings?** (the covering analog of the measured
   B2 Ramsey wall) — bounds the honest audit-tier "small band" and decides whether `render_covering_lean`
   needs a hard cap.

Cost classes: **free-cpu** (pure python; no docker/LLM) · **docker-local** (real Lean kernel, operator
machine, free) · **billable-llm** / **operator-only** (a human act or API spend).

---

## Tier 0 — free-CPU, runs now, fully parallel ($0, no docker, no trust touch)

| id | run | deliverable / exit criterion |
|---|---|---|
| R0.1 | **render-fidelity lock** (run first, standalone) | `render_corpus`/`render_reading_room` of the committed JSON == the committed `.md` byte-for-byte, as a regression. Red on any unrendered JSON/markdown edit. |
| R0.2 | **directional-soundness smoke** (GATE-4 cheap arm) | `render_covering_lean` emits a theorem **iff** `verify_covering` accepts; rendered `B == len(blocks)` and the rendered literals are exactly the sorted blocks (no render-time size laundering). |
| R0.3 | **verify/render cost-ceiling probe** | Measure `verify_covering` cost vs C(v,t) (uncapped `combinations(range(v),t)`); report the (v,t) threshold where the python pre-check exceeds a budget → free-cpu analog of GATE-2; informs whether covering needs a `RENDER_SUBSET_CAP`. |
| R0.4 | **false-witness breadth fuzz** | ≥500 invalid coverings → 0 false-accepts; cross-checked vs an independent brute-force oracle; 0 false-rejects on a valid set. |
| R0.5 | **structural-guard red-team corpus** | Turn the bypassable-denylist WARNING into an *asserting* regression: every declaration/metaprogram form the denylist admits is labelled a known gap (no silent pass); `canonical_claim` recomputes true size on every laundering attempt. |
| R0.6 | **oracle backstop guards** (trimmed) | Load-bearing only: zero-padded-key dedup guard + a committed-snapshot zero-padded-key check + `is_improvement` property soak (never True on equal counts; never a record for an untabulated cell). Do not re-measure already-known constants. |
| R0.7 | **amplify batch soak + idempotency** | First decide the new-row-missing-`size` policy (hard precondition with a clear error, not a raw KeyError); soak 500–2000 mixed entries twice into a **throwaway** corpus (never the committed JSON): `merge(C,C)==C`, order-independence, 0 `witness_sha` collisions at scale, audited+skipped==feed length. |
| R0.8 | **stronger-lower-bound sweep** (D-ladder rung 1) | Compute Schönheim (exact int) for all cells; identify gap cells (best_known > Schönheim); apply the cheap LP/counting bound; **count surviving OPEN cells** (cheap bound strictly below best_known). Emit `docs/results/covering_lower_bound_sweep.json`. If 0 gap cells in the tractable band, D is provably dead for $0. |

## Tier 1 — free-CPU D ladder, sequenced, on ONE frozen OPEN-cell list
*(critic-required: pin a single canonical OPEN-cell list threaded through every D run, else the billable trigger is unsound)*

1. **Freeze the canonical OPEN-cell list** from R0.8.
2. **Free greedy producer first** (reordered ahead of exact): both free producers on the OPEN cells — a $0 greedy beat short-circuits the expensive exact run on that cell.
3. **Exact long-budget** (1800s/cell CP-SAT, warm-started) on the still-open cells → per cell OPTIMAL / BEAT / still-open.

The standalone "exact-reach frontier map" was **cut** (cartography that doesn't change which cells we attack; fold a 2–3 cell spot-check into the exact warm-up). → resolves **GATE-1**.

## Tier 2 — docker-local (real Lean kernel, operator machine, free)
- **kernel-soak full docker** — complete gated set on the pinned images; expect 0 fail / 1 skip (live API key); per-file timing baseline.
- **false-theorem rejection stress** — ≥20 known-false theorems across covering/CWC/Ramsey all rejected (GATE-4 kernel arm; cheap arm already ran in Tier 0).
- **covering decide-wall measurement** — render a cell ladder + time each on the kernel to locate the intractability threshold → **GATE-2**.
- **degenerate/vacuous-cell battery** — which degenerate cells (`t>v`, `k>v`, `t=0`, …) make `validCovering` vacuously true so `decide` stamps a meaningless bound.
- **domain-guard prototype** *(new — critic fix)* — actually build+test the parameter-domain guard so GATE-3's "working domain guard" green is *reachable*.
- **non-promoting ConstructionVerifier prototype** *(HARD re-scoped)* — scripts-local **only**: `construction_kernel_checked` set on a plain dataclass, with an explicit exit assertion that it imports nothing from `leibniz/propositio.py` or `leibniz/types.py` and adds no trust-core field; generate-not-parse over the locked prelude; confirm an axiom-injecting source is flagged where the text guard misses it. Depends on the battery + guard prototype → **GATE-3**.
- **CI skip-count guard** — throwaway-branch probe that catches a kernel/z3 gate silently no-opping; pairs with the soak for **GATE-5**.

## Tier 3 — operator-only / billable, CONDITIONAL (only behind a green gate)
- **beat-witness render-confirm** — *only if Tier 1 found a BEAT.* Render + kernel-decide it. Audit-tier confirmation, **not** promulgation, **not** a discharge edit.
- **billable stronger swing** — *only if the whole free ladder is inconclusive* (`free_beats==0` ∧ gaps survive the strongest cheap bound ∧ exact can't settle them ∧ both free producers plateau), on the frozen cell list, run by the operator.

---

## Decision gates (the forks that pick the next implementation step)

| Gate | After | GREEN → | RED → |
|---|---|---|---|
| **1 — beatable frontier** | R0.8 + greedy + exact | a beat/slack exists → un-deferring `discharge` becomes worth *reconsidering* (separate operator+ADR act) | all-optimal → **D dead for $0**; freeze the proof-edge; reframe the headline as "no reachable-and-beatable frontier," not "producer too weak" |
| **2 — covering decide wall** | wall measurement | wall above the small band → render honest as-is | wall inside the tabulated range → add `RENDER_SUBSET_CAP`; a record-sized discharge needs a **certificate architecture**, not `decide` |
| **3 — build the constructive intermediate?** | prototype + battery + guard | clean kernel-check + empty axiom closure + working guard + invariants byte-identical → safe to build the non-promoting `ConstructionVerifier` | unsound → design needs more guards first |
| **4 — soundness backstop (OVERRIDE)** | cheap arm Tier 0 / kernel arm Tier 2 | 100% rejection → audit tier broadly evidenced | **any** false-accept → HALT all reliance until fixed (overrides cost ordering) |
| **5 — CI silent-skip / kernel lane** | skip-guard + full soak | green → widen `run_kernel_tests.sh` / register a runner | a gate no-ops → fix infra before trusting green CI |

## Scope guardrails (carried from the adversarial critic — non-negotiable)
- No run edits `verifiers.py::discharge`, `trust.py`, `types.py`, `propositio.py`, `gates/*`, or `tests/test_invariants.py` (all PreToolUse-guarded; `test_invariants.py` byte-identical).
- **GATE-1 green is NOT authorization to edit `discharge`.** Un-deferring the proof-edge is a separate operator act gated behind a new ADR and the 8/8 witness round. The validation cycle stops at audit-tier kernel confirmation.
- The non-promoting prototype sets `construction_kernel_checked` only on a **scripts-local** object — never a trust-core type.
- One **frozen** surviving-OPEN cell list is threaded through every D run before any billable spend.

## Excluded / deferred this cycle
Certificate-architecture prior-art scan + B2 Ramsey decide-wall sub-sweeps (post-decision); `register-self-hosted-lean-runner` (after GATE-5); E8-holdout expansion (after GATE-3 green); live-LJCR drift re-check (recurring monitor, not a blocker — 0-drift confirmed 2026-06-30).

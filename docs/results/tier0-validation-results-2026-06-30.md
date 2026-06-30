<!--
Results of the Tier 0 (free-CPU) validation runs from docs/validation-plan-2026-06-30.md. All runs are
$0, no docker, no trust-core touch; tests/test_invariants.py byte-identical. Data artifacts under
docs/results/*.json; regressions under tests/.
-->

# Tier 0 validation results (2026-06-30)

All eight Tier-0 free-CPU runs executed. **Full suite: 837 passed, 1 skipped; `test_invariants.py`
byte-identical; ruff clean.** No trust-core file touched. Two real defects were found and fixed in
shipping code (both in `amplify.py`, hardenings — not weakenings).

| run | result | gate / implication |
|---|---|---|
| **R0.1 render-fidelity lock** | GREEN — both committed markdowns byte-match a fresh render of the committed JSON; locked as a regression | the published Calculemus audit annex cannot silently drift from the kernel-checked corpus |
| **R0.2 directional-soundness smoke** | GREEN — `render_covering_lean` emits iff `verify_covering` accepts; rendered `B == len(blocks)`; literals are exactly the sorted witness | GATE-4 cheap arm: no render-time laundering |
| **R0.3 cost-ceiling probe** | the Python pre-check enumeration floor crosses 1s only at **C(50,9,6) ≈ 16M t-subsets** (0.4s at ~4M) | GATE-2 (free analog): the Python side is **not** the binding wall — the kernel `decide` wall (docker) binds first; a `RENDER_SUBSET_CAP` on the Python side is low priority |
| **R0.4 false-witness fuzz** | GREEN — **0 false-accepts over 550 invalid witnesses**, 0 disagreements with an independent brute-force oracle, 0 false-rejects on valid set, render refused all 550 | GATE-4 cheap arm: the untrusted pre-check is broadly sound |
| **R0.5 structural-guard red-team** | GREEN — denylist bypasses (irrelevant/laundered statement, non-`decide` proof, `run_tac`, false bound) asserted **ADMITS-TODAY**; inline `let`/`have`-with-`:=` shadow caught by the single-`:=` rule | documents the porosity as a regression; the kernel is the backstop for false bounds; flips loudly when the allowlist lands |
| **R0.6 oracle backstop** | GREEN — zero-padded-key collision now **rejected at load**; committed snapshot has 0 ambiguous keys; `is_improvement` strict-beat-only property soak over ≥20 cells; untabulated cells never an improvement | the novelty oracle (invariant 4) hardened before any BEAT verdict reads it |
| **R0.7 amplify batch soak** | GREEN after 2 fixes — 800-entry mixed feed → 559 unique, **idempotent**, **order-independent**, 0 false-witnesses-verified, 0 `witness_sha` collisions | Track A is a durable batch pipeline, not an 8-entry demo |
| **R0.8 stronger-lower-bound sweep** | 9482 cells: **1453 OPTIMAL** (record meets a cheap bound), **8029 OPEN** (gap survives), **0 ANOMALY**; LP confirmed no stronger than the cheap bound on the sampled OPEN cells (0 gaps closed) | **GATE-1 rung 1:** cheap lower bounds do NOT kill D — 8029 gap cells remain; the exact ladder (Tier 1) must settle the tractable smallest ones |

## Defects found + fixed (shipping code, `amplify.py`)
1. **Non-canonical stored witness.** `_norm_code` sorted within each block but preserved block ORDER, while
   `witness_sha` is order-insensitive — so a reordered duplicate deduped to the same key but stored a
   different block order, letting **feed order leak into the persisted/rendered corpus** (non-deterministic
   ledger). Fixed: `_norm_code` now sorts the block list too (a covering/code is a set; order is not
   semantic). The committed corpus is unaffected (its markdown does not render block order).
2. **Non-total corpus sort key.** `merge_corpus` sorted by `(domain, cell, size)` only — distinct witnesses
   sharing those three fields kept input order under Python's stable sort. Fixed: sort by the full
   `(domain, cell, size, source, witness_sha)`. Also: a NEW audit row missing a required field now raises a
   **clear `ValueError`** (the chosen R0.7 policy) instead of a raw `KeyError` (existing older-shape rows
   stay tolerated).

## What this settles for the next decision
- **GATE-1 is live and pointing at Tier 1.** Cheap bounds leave 8029 gap cells; D is neither dead nor alive
  by cheap analysis — the exact CP-SAT ladder over the smallest OPEN cells is the next measurement.
- **GATE-4 cheap arm is GREEN.** The covering pre-check + render path show 0 false-accepts across a broad
  adversarial corpus; the docker kernel arm (Tier 2) remains to widen this to the kernel itself.
- **GATE-2 free analog:** the covering decide wall is a kernel concern, not a Python one — Tier 2's
  docker measurement is where the cap decision actually gets made.
- The audit-tier guarantees (render fidelity, novelty oracle, batch durability) are now continuously
  guarded by regressions, and two real non-determinism defects in the banked Track-A product are fixed.

Artifacts: `docs/results/covering_lower_bound_sweep.json`, `covering_cost_ceiling.json`, `amplify_soak.json`.
Regressions: `tests/test_covering_lower_bound_sweep.py`, `test_render_fidelity.py`, `test_covering_fuzz.py`,
`test_structural_guard_redteam.py`, `test_covering_oracle_hardening.py`, `test_covering_cost_ceiling.py`,
`test_amplify_soak.py`.

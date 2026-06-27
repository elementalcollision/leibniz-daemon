<!--
Pre-registration of the FunSearch LLM pilot (operator GO: small CPU-first tranche). Committed BEFORE
the billable run so the target cells, budget, and stop rule cannot be cherry-picked after seeing
results. Machine-readable mirror: docs/results/funsearch_pilot_targets.json.
-->

# FunSearch LLM pilot — pre-registration (committed before the run)

**Status:** pre-registered 2026-06-27; build complete and fake-validated; **billable run pending
operator execution.** Authorized by the GO/NO-GO decision (small CPU-first tranche). No spend occurs
until the live run is launched.

## Hypothesis
An LLM, proposing *construction programs* (not codewords or fixed group families), can write code that
produces a constant-weight code **strictly larger than the published record** on at least one tabulated,
non-tight cell where our deterministic structural baseline fell short — a beat the Lean kernel confirms.

## Target cells (fixed before running — anti-cherry-pick)
The 12 cells in `docs/results/funsearch_pilot_targets.json`: structural-sweep **shortfall** cells (where
the deterministic baseline fell below the record), **tabulated** (so there is an oracle floor to beat),
**excluding Rosin 2026's 24** improved cells (already intensively optimized). Small floors first (most
tractable to exceed) plus the flagship near-miss **A(21,6,4)** (floor 31). Floors range 2–31.

A beat must **strictly exceed** the floor `effective_best_known = max(committed Brouwer snapshot, Rosin
2026)` AND pass the Lean kernel re-check. (Note: on a cell whose record is actually optimal, no valid
larger code exists, so `verify_cwc` simply never confirms one — no false beat is possible.)

## Budget (hard caps, enforced in code)
- **≤ 240 total LLM program proposals** across the whole pilot (≤ 20 per cell).
- **≤ 60 min** wall-clock; **≤ 4096 tokens** per proposal (raised from 1500 after the first run voided:
  a reasoning model exhausted a 1500-cap mid-reasoning and returned null content; `--max-tokens` is
  configurable and the proposer now handles null content / reasoning fields robustly).
- Model via `LEIBNIZ_FUNSEARCH_MODEL` (OpenRouter); CPU evaluator only (no GPU this tranche).
- Estimated spend: low-tens of USD at a mid-tier model — a genuinely small tranche.

## Stop rule (pre-registered)
- **Zero kernel-verified beats after the full budget → the autonomous record-beating track CLOSES.**
  Record the RED in the capstone; do **not** silently retry or expand the budget.
- **One kernel-verified beat →** STOP; record the witness for the ADR 0040 carve-out + operator review.
  GPU/island escalation requires a **separate** operator GO.

## Trust guardrails (non-negotiable)
- LLM-written programs are **untrusted** → executed **only** in `scripts/funsearch_sandbox.py`.
- Fitness (`verify_cwc`) is untrusted; novelty is the **automated oracle** (post-Rosin), never the LLM.
- A beat is decided by the **Lean kernel** (`scripts/cwc_check.py`) + the oracle; the pilot **never**
  sets `kernel_verified` and **never** promulgates. `tests/test_invariants.py` byte-identical.

## How the run is executed
The pilot is built and validated with a deterministic **fake** proposer (no spend). The **billable**
run is launched by the operator with their key:
```bash
python3 -m leibniz.env  # or ensure OPENROUTER_API_KEY + LEIBNIZ_FUNSEARCH_MODEL are set via .env
python3 scripts/funsearch_llm_pilot.py docs/results/funsearch_pilot_result.json
```
Results + any beat witnesses are written under `docs/results/`; a verified beat is then run through
`scripts/cwc_check.py` for the kernel stamp.

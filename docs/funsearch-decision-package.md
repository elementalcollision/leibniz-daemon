<!--
Decision-package for Option A (FunSearch-style learned construction) from the continuation-strategy
workflow. This is a GO/NO-GO package for the operator — NOT an authorization to spend. No GPU/LLM
money is committed by this document. Companion to docs/autonomous-discovery-arc-capstone.md and
docs/adr/0040-cwc-record-triviality-carveout.md.
-->

# FunSearch decision-package — learned construction search for CWC records

**Status:** awaiting operator GO/NO-GO. Nothing here spends money. **Date:** 2026-06-27.

This is the one un-pulled lever from the concluded autonomous arc, written up so the operator can make
a clean billable decision. The recommendation from the strategy workflow was: **do the cheap Option-E
asset-hardening first (done — `scripts/cwc_check.py`, `lean-project/CwcFanoWitness.lean`, ADR 0040),
then decide A separately.** This package is that decision, de-risked and pre-registered.

## 1. What A is

LLM proposes *construction programs* (Python functions that emit a CWC code for given n,d,w), an
evolutionary loop mutates/selects them by a fitness = the size of the valid code they produce, and any
program whose output **beats** Brouwer's table-of-record has its witness re-checked by the Lean kernel.
This is the FunSearch / AlphaEvolve paradigm: search the space of *constructions*, where records live —
not the space of codewords (exact/heuristic, RED) or fixed group families (structural, RED, 0 beats).

## 2. Why it is now credible — and why the bar is higher

**New decisive fact (from the strategy workflow's literature grounding):** Christopher Rosin,
*"Automated Discovery of Improved Constant Weight Binary Codes"* (arXiv 2603.00174, 2026), ran exactly
this method on exactly this problem and **improved 24 CWC lower bounds.** So:

- **Method credibility: HIGH.** This is no longer a witness's modest-odds guess — the approach
  provably beats the Brouwer CWC table in practice. It is the only lever with a same-domain existence
  proof.
- **Novelty odds for *us*: LOWER than the headline suggests.** Rosin harvested the reachable cells.
  Our genuine-novelty surface is what he did *not* cover: **un-swept regimes only** — larger n
  (n > 35), or d/w outside his swept range — where per-program hit-rate is well under 1%. Treat the
  realistic odds of *any* genuine new beat in a bounded first pilot as **coin-flip-to-modest**, not
  "this will work."

## 3. The de-risking already done (Option E)

Before any spend, the trusted re-check path is now a re-runnable asset, so a pilot cannot waste money
discovering a plumbing bug:

- `scripts/cwc_check.py` — witness → `verify_cwc` → `render_cwc_lean` → Lean kernel
  (`LeanCliBackend.check_source`) → oracle novelty. Audit-only; never promulgates.
- `lean-project/CwcFanoWitness.lean` — the first Q.E.D. made durable (was ephemeral Docker).
- ADR 0040 — the `decide`-triviality carve-out a beat would need, surfaced and safely scoped.

The pilot's evaluator and re-check are therefore the *existing* `verify_cwc` (untrusted fitness) and
`check_source` (trusted) — no new trust surface in the checking direction.

## 4. The pilot spec (bounded, pre-registered)

| dimension | spec |
|---|---|
| **Target cells** | ONLY un-swept regimes: n > 35, or (d,w) outside Rosin's covered range. Pre-register the exact cell list before running (no post-hoc cherry-picking). |
| **Proposer** | A modest LLM (existing `propose` extra / OpenRouter), proposing construction *programs*, not codewords. Tens→low-hundreds of programs in the first pilot. |
| **Evaluator** | CPU first: run each program, score by `verify_cwc`-valid code size. GPU/island scale ONLY after a first verified+novel beat (escalation, not entry). |
| **Selection** | FunSearch-style island/evolutionary loop over high-fitness programs. Deterministic seeding where possible for reproducibility. |
| **Re-check** | Every candidate beat → `render_cwc_lean` → kernel `check_source`. A beat is real only if the kernel accepts it. |
| **Novelty** | `cwc_table_oracle.is_improvement` against a **refreshed, post-Rosin** snapshot (see §6). Never an LLM judgment. |
| **Budget** | Fixed, pre-registered USD + wall-clock cap. Recommend a *small* first tranche (see §5). |
| **Stop rule** | **Pre-registered:** zero verified+novel beats after the budget → the marginal-novelty wall is confirmed; record it in the capstone and CLOSE the autonomous track (do not silently retry). One verified+novel beat → escalate (GPU/island) under a fresh budget decision. |

## 5. Honest cost / effort

- **Engineering:** a real build, not glue. The evolutionary loop + island management + program
  sandboxing is days of work. The checking half is done (§3).
- **Security surface (the main new cost):** the loop executes **untrusted LLM-generated Python**. This
  needs OS-level isolation (container with no network, CPU/mem/time limits, no host FS mount, killed on
  timeout) — the evaluator is untrusted and must be treated as hostile. This is the single most
  important non-trivial new component and must be reviewed before any program is executed.
- **Compute:** CPU-first pilot is cheap (LLM tokens + laptop/CPU time, low hundreds USD). GPU/island
  escalation is low-thousands USD + days, and is GATED behind a first beat — never the entry cost.

## 6. Hard preconditions (must hold before the pilot runs)

1. **Oracle refresh + Rosin cross-check.** Re-fetch the current Brouwer table AND cross-check the
   target cells against Rosin's published 24 improvements, so a "beat" cannot be a re-discovery of an
   already-claimed record. The current committed snapshot is the canonical Brouwer table fetched
   2026-06-27, but it must be confirmed to reflect post-Rosin values for the *specific* target cells
   before any novelty is claimed. (This is a precondition of *claiming*, not of *searching*.)
2. **Untrusted-code sandbox reviewed.** No LLM-generated program is executed until the isolation design
   is built and adversarially reviewed.
3. **Cells pre-registered.** The target list is fixed and written down before the run (anti-cherry-pick).
4. **Stop rule pre-registered.** The RED-closes-the-track exit is committed before the run, so a null
   result is a finding, not a prompt to keep spending.

## 7. Trust-boundary guardrails (non-negotiable)

- Search + evaluator are **fully UNTRUSTED.** The fitness score is FAIL-only — it can promote a program
  in the *search*, never a *theorem* in the ledger.
- The Lean kernel via `LeanVerifier.discharge` stays the **sole** arbiter of any beat's proof;
  `kernel_verified` is written nowhere else.
- Novelty stays the **automated oracle** (`is_improvement`), never an LLM judge (invariant 4).
- A real beat promulgates only via the ADR 0040 carve-out (its own trust-edge change + operator
  sign-off) → `discharge` → `TrustPolicy.validate_path`. No shortcut.
- `tests/test_invariants.py` byte-identical throughout.

## 8. The decision

**GO** = authorize the bounded CPU-first pilot in §4 (small tranche, §5 cost), with §6 preconditions and
§7 guardrails, and the §4 stop rule. Escalation to GPU/island requires a *second*, separate GO after a
first verified beat.

**NO-GO** = the autonomous arc stays concluded; the daemon's value is the sound verification instrument
(Option B/E assets), and we wait for a human-supplied frontier conjecture to check rather than search
for one. This is fully defensible: the odds on un-swept cells are coin-flip-to-modest and the field is
freshly picked over.

**My recommendation:** GO *only* if you want a genuine (modest-odds) shot at an autonomously-discovered,
kernel-verified record and are comfortable with a small pre-registered tranche resolving to RED; the EV
is "real but uncertain." If the goal is reliable demonstrable value, NO-GO and lean on the Option-E/B
assets. Either way, do **not** authorize GPU/island scale up front — the staging is the whole point.

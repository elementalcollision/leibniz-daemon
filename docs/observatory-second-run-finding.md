<!--
Observatory run-2 (lint-on). The lint's first live validation + the conjecturer mode-collapse
diagnosis that motivated the anti-collapse steering. Provenance:
docs/results/observatory_second_run_summary.json. No trust-boundary change; non-Q.E.D. throughout.
-->

# Observatory run-2 — the lint works live; the bottleneck is now the conjecturer

**Status:** measured, 2026-06-26. **Verdict: faithfulness machinery validated end-to-end; 0 genuine
theorems; the binding constraint moved to conjecturer diversity.** The first lint-on live run (ADR 0039)
of 20 automatic-sequence claims: **0 `WALNUT_DECIDED`, 18 `REFUTED`, 2 `lint_counterexample`.** Not one
false record was filed — the trust + faithfulness gates rejected 100% of a degenerate batch.

## What ran
`scripts/run_observatory.py 20` (live conjecturer + real Walnut, `require_descriptor=True`). Reason
histogram: `refuted_sentence` 18, `lint_counterexample` 2.

## The lint passed its live trial (the run-1 failure mode, stopped)
Two claims were Walnut-**decided TRUE** but **quarantined by the lint** — exactly the d4a4d22b artifact
class that polluted run-1, now caught:

| pid | buggy bound | descriptor | lint catch |
|---|---|---|---|
| b51f947b | `t<3*p+1` (needs `t<3*p`) | `power_free RS 4` | counterexample `0000` at 7 |
| 36d5c951 | `t<3*p+p` = `4p` (needs `t<3*p`) | `power_free RS 4` | counterexample `0000` at 7 |

Both wrote a bound that makes Walnut decide a *weaker, true* statement, but the descriptor honestly said
"4th-power-free," and the lint brute-forced it → found the `0000` 4th power → quarantine. **Without the
lint these would be false `WALNUT_DECIDED` records (the run-1 outcome). With it: 0 false records filed.**
The decider half is healthy too: the other 18 were the same (false) claim written as closed sentences,
which **Walnut soundly refuted**.

## The finding — conjecturer mode-collapse
**All 20 claims were the *same* conjecture** — "RS is 4th-power-free," descriptor `{power_free, RS, 4}`,
**1 distinct descriptor across 20 calls** (12 prose rewordings of one idea). And that claim is **false**
(RS *has* a 4th power). So the entire run was the system correctly rejecting one false, repeated idea.

- **Root cause:** `WalnutConjecturer.generate()` passed a *static* seed with **no memory of prior
  proposals**, so the old "vary from what you proposed before" steer could not bite — every independent
  call regenerated the single most-salient (and, here, false) idea. 20 LLM calls + 20 Walnut runs spent
  on one conjecture.
- **Binding constraint:** conjecturer **diversity + correctness** — not the trust machinery (validated
  here), not prover reach. Exactly the post-R6 framing.

## Fix applied (proposal-side; no trust impact)
Anti-collapse steering in the conjecturer:
1. **Session avoid-list** — each call's context now lists prior `(statement → outcome)` ("do not repeat;
   these were refuted/unproven"), so the model sees what it already tried *and which were false*.
2. **(word × family) rotation** — successive calls are steered across the lint-checkable
   words (T/RS/F/TR) × families (power-free / avoids-factor / avoids-pattern) for breadth.
3. **True-not-false steer** — the seed states that false (refuted) and duplicate claims waste the run.

All of this is context engineering on the proposal side; the descriptor binding + lint still gate every
decision, the trust boundary is untouched, and `tests/test_invariants.py` is byte-identical.

## Disposition / next
- **Packet: empty** — 0 `WALNUT_DECIDED` means there is nothing to screen for novelty; kernel-bridge
  **trigger-1 stays UNMET**. Nothing forwarded to the human panel.
- **Next:** re-run the live Observatory with the anti-collapse conjecturer and measure whether genuine
  (true + faithful, then plausibly-novel) DECIDED records emerge across a *diverse* batch. The remaining
  open question is whether the lint-checkable family whitelist (necessarily textbook-leaning) admits
  anything a human panel would call novel — the deeper "discovery under a sound faithfulness gate"
  tension, now measurable on a non-degenerate run.

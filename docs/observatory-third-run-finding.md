<!--
Observatory run-3 (lint-on, anti-collapse conjecturer) + its adversarial verification. The
milestone where the channel is proven SOUND + DIVERSE + FAITHFUL end-to-end — and measured to
yield TEXTBOOK. Provenance: docs/results/blind_novelty_panel_packet.json, observatory_lint /
second_run summaries. No trust-boundary change; non-Q.E.D. throughout.
-->

# Observatory run-3 — the channel is sound, diverse, and faithful; and its ceiling here is textbook

**Status:** measured + verified, 2026-06-26. **Verdict: the Walnut Observatory works end-to-end; 0
novel.** With the anti-collapse conjecturer (#142) the run produced **11 `WALNUT_DECIDED` · 6 `REFUTED`
· 3 unproven** across all four sequences × all three families. A 12-agent adversarial verification found
**11/11 admissible (sound: predicate decodes TRUE on the prefix + non-vacuous), 0 unsound slipped,
10/11 fully faithful — and all 11 textbook.** Nothing is forwarded to the human panel.

## What ran
`scripts/run_observatory.py 20` (live, `require_descriptor=True`). Descriptor diversity went from
run-2's **1/20** to **~17/20**: T/RS/F/TR × power-free / avoids-factor / avoids-pattern.

## Verified findings (independent per-record decode + prefix recomputation)
- **Soundness: 11/11.** Every decided predicate decodes to a statement that is TRUE on an independently
  computed prefix and genuinely depends on the sequence. **0 unsound records slipped** — the serious
  failure mode did not occur.
- **The conjecturer learned the bound it botched twice.** `a96b747b` proposed RS 4th-power-free with the
  *correct* `t<3*p` and Walnut **refuted** it (RS isn't 4th-power-free) — correct encoding → sound
  refutation. The two run-1/2 artifact bounds did not recur among the *faithful* records.
- **Faithfulness: 10/11 fully faithful** (prose + descriptor match the predicate). The lone residual is
  `6bee4c3d`: prose says exponent **7/3**, descriptor says **3**, the predicate (`3t<7p`) decodes to
  **10/3** — three different numbers. It is still **sound** (TM has critical exponent 2, so 10/3-power-
  free is true), but the human-facing text is inconsistent and **the lint validated the wrong (descriptor)
  exponent**. This is precisely the documented family/parameter-shop residual (ADR 0039 §3a).
- **Novelty (advisory): 11/11 textbook, 0 plausibly-novel.** Power-freeness records are corollaries of
  Thue (1912) overlap-freeness and the Fibonacci/Tribonacci critical exponents; the forbidden-factor and
  bounded-alternation records are elementary subword-complexity / run-length facts (several immediate from
  the defining morphism, e.g. Tribonacci `2→0` forbids `22`).

## What it means
- **The trust + faithfulness machinery is validated in production.** Across runs 1–3 the gates moved from
  *3 artifacts filed* (run-1, pre-lint) → *2 artifacts caught* (run-2) → *0 unsound, 10/11 faithful,
  diverse* (run-3). The non-Q.E.D. channel now reliably produces correct, diverse mathematics behind an
  unchanged trust boundary.
- **The discovery ceiling on this setup is textbook — the "discovery under a sound faithfulness gate"
  tension, quantified.** The lint-checkable families (power-free / avoids-factor / avoids-pattern) on the
  canonical sequences (T/RS/F/TR) are *exactly* the properties already characterized in the literature.
  Soundly-checkable + famous-sequence ⇒ textbook. Genuine novelty needs a richer question space.
- **Kernel-bridge trigger-1 stays UNMET** (it requires ≥1 blind-panel-*confirmed* novel decision; there
  are 0 plausibly-novel candidates). Forwarding textbook facts would waste the scarce human-panel budget
  (the post-R6 binding constraint) and pollute invariant-4 calibration — so **0 forwarded**.

## Disposition / next
- **Packet: 11 sound candidates, 0 forwarded** (`docs/results/blind_novelty_panel_packet.json`). Records
  retained (invariant 6); none Q.E.D.
- **Two concrete follow-ups surfaced by the verification:**
  1. *Lint hardening* — derive the `power_free` exponent from the predicate's matching-window bound
     (`t<K*p ⇒ e=K+1`) and require `descriptor.exponent == that`, rejecting fractional/non-matching
     predicates. This mechanically closes the `6bee4c3d` residual and the power-free parameter-shop.
  2. *Strategic* — the channel is proven; the open question is how to reach beyond textbook: less-studied
     sequences (new verified generators), richer Walnut-decidable question types, or pivot to the next
     sound backend (the SOS/Positivstellensatz "walk" rung) in a different math domain.

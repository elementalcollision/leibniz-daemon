<!--
First live Walnut-decided Observatory run (ADR 0038) + its adversarial verification.
Provenance: docs/results/observatory_first_run_verification.json. The headline finding of the
discovery channel's first end-to-end live run. No trust-boundary change; non-Q.E.D. tier throughout.
-->

# Observatory first live run — the channel is sound; the first decisions are faithfulness artifacts

**Status:** measured, 2026-06-26. **Verdict: end-to-end success, 0 genuine decided theorems.** The
Walnut-decided discovery channel ran live for the first time (conjecturer → Walnut decides → non-Q.E.D.
tier). The *decider* is sound. But **all 3 `WALNUT_DECIDED` records are faithfulness artifacts** — the
conjecturer's English→DSL encoding mis-states its own claim — so the kernel-bridge trigger-1 precondition
(≥1 blind-novel decision) is **unmet**, and nothing is forwarded to the human panel.

## What ran
`scripts/run_observatory.py` (live: real Anthropic conjecturer + real Walnut). 5 automatic-sequence
claims about Rudin-Shapiro (RS): **3 `WALNUT_DECIDED`, 2 `REFUTED`, 0 `no_result`/`indeterminate`.** The
path/role/sentence-decision fixes (#137/#138/#139) all worked; the wiring is healthy.

## The finding — the 3-body problem bit immediately
A 6-agent adversarial verification (per-record faithfulness + vacuity + RS-correctness; provenance JSON)
found **0 of 3 DECIDED are genuine theorems of the stated claim**. In each case Walnut soundly decided
the *predicate*, but the predicate ≠ the prose, and the prose is **false for RS**:

| pid | bug | predicate actually decides | prose claims | prose true? |
|---|---|---|---|---|
| d4a4d22b | `t<4p` not `t<3p` | RS is **5th-power-free** (true) | RS is **4th-power-free** | **FALSE** (crit. exp. = 4; `1111` at 7–10) |
| d37eb690 | `i<n+4` not `i<n+3` | no alternating length-**5** window (true) | no alternating length-**4** factor | **FALSE** (`RS[13..16]=1010`) |
| baff1218 | window `i≤n+1` not `i≤n` | (reads one symbol past the factor) | length-(n+1) factor non-constant | **FALSE at n=1** (`RS[1..2]=00`) |

Each off-by-one/off-by-p conveniently flips the verdict on exactly the input where the literal claim
fails — the classic signature of a faithfulness artifact, not a discovery. `d4a4d22b` is a regression
against the project's *own* correct template (`trib4free` uses `t<3*p`,
`docs/results/walnut_reachability_probe_report.json`). The **2 REFUTED** records, by contrast, are
faithful, non-vacuous, and RS-consistent — the refutations are *correct*.

## What it means
- **The decider half of the channel is healthy** (Walnut decisions sound; refutations correct; trust
  boundary held — non-Q.E.D., no LLM decided a proof). The verification *is* the faithfulness gate, and
  it worked: it caught the mismatch.
- **The binding constraint is conjecturer faithfulness** — the *formal-statement ↔ human-claim* gap, on
  the proposal side, which the Observatory (relying on "formal-first") does not gate. This is the
  project's central thesis confirmed, and consistent with the post-R6 roadmap (novelty/encoding, not
  prover reach or the trust boundary, is the limiter).
- **0 genuine novel** (the arc's predicted-textbook outcome), with the added finding that the encodings
  are *buggy*, not merely unoriginal. The kernel bridge stays gated (task #54): trigger-1 unmet.
- **Strict formal-first is necessary but not sufficient for *measuring discovery*.** Reading the prose
  misleads; reading the predicate gives a real-but-textbook fact that isn't what the conjecturer
  "intended." Either way the conjecturer's prose is currently untrustworthy.

## Disposition / next
- The 3 DECIDED records are **faithfulness artifacts**: not forwarded to the human blind-novelty panel
  (forwarding them would waste the scarce human budget and pollute the invariant-4 review). Retained,
  never deleted (invariant 6); none earns Q.E.D. (correct — the tier never stamps it).
- **Fix is upstream, at the conjecturer's encoder** (a systematic off-by-one/off-by-p family). The open
  design choice — recorded for the operator — is how the tier defends faithfulness:
  1. **Templated predicates** for known property families (power-free(e), overlap-free, recurrence(gap)):
     the LLM picks family + parameters; the Observatory renders the predicate with *mechanically correct*
     bounds — removes the LLM's bound-arithmetic from the trust path (strongest; narrows to known families).
  2. **Prose-faithfulness lint:** for a DECIDED finitary factor/power property, a cheap bounded numerical
     cross-check of the *prose* claim before filing (all 3 would have been caught by a <500k-term scan) +
     a regression pinning bound patterns (length L → `i<n+(L-1)`; e-th power → `t<(e-1)*p`).
  3. **Prompt tightening** with explicit bound rules + the correct `trib3*p` template (cheapest; reduces
     but does not eliminate the error rate).

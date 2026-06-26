# ADR 0038 — The Walnut-decided Observatory tier (non-Q.E.D.) + kernel-bridge gating

**Status:** Proposed (design — implementation behind it, off by default).
**Date:** 2026-06-26
**Predecessors:** ADR 0036 (§10.2 the escape is a different sound checking *paradigm*; §10.3 the
"Observatory" non-Q.E.D. ledger idea), ADR 0037 (the `SoundFaithfulnessBackend` seam + the Walnut
backend, off by default). Decision input: the **kernel-bridge n-witness build evaluation**
(`docs/results/kernel_bridge_build_eval.json`).
**Trust boundary:** untouched. `kernel_verified`/Q.E.D. stay **kernel-only** (`LeanVerifier.discharge`);
`TrustPolicy.validate_path` and `tests/test_invariants.py` byte-identical. This tier is a *separate*
output that never enters the kernel promulgation path.

---

## 1. Why this, why now

The Walnut backend (ADR 0037) is a **sound decision procedure** over k-automatic sequences — it
*decides* FO statements over unbounded n that the bounded-box DSL cannot even state (M2: 0/24
expressible; Walnut probe: 12/12 reachable). But a Walnut decision **cannot be Q.E.D.**: invariants 1
& 7 pin `kernel_verified`/Q.E.D. to the Lean kernel. So Walnut-decided theorems have nowhere to land in
the kernel Codex.

The kernel-bridge "run" rung (render the claim as a Lean Prop, require a kernel-checked bridge proof)
would let them earn real Q.E.D. — but the n-witness evaluation found it **XL, easier *later*, and the
first target class is *not reachable*** through it: the cheap-now part is only the seam plumbing; the
binding costs are intrinsic — (i) the claim→Lean renderer is a load-bearing trusted artifact with **no
mechanical re-checker** (a bug = a kernel-stamped Q.E.D. of a mis-statement), and (ii) bridge-synthesis
DEFERs on ~everything valuable (mathlib has no Thue-Morse/Tribonacci/Stern/power-freeness/Büchi-Bruyère;
the valuable goal shape is exactly the M2 0/24 class; ~10–12/12 DEFER → the same M1 textbook floor).
Building the project's hardest, most trust-critical rung to mint Q.E.D. for a channel **not yet shown to
discover anything** inverts the order the arc's own evidence (0034/0035/0036 all 0-novel) demands.

So: **measure first.** Stand up a cheap, sound, non-Q.E.D. tier that publishes Walnut *decisions*,
run the blind novelty panel on it, and gate the kernel bridge behind the result.

## 2. Decision — the Walnut-decided Observatory tier

A **separate ledger** of theorems **mechanically decided by Walnut** (sound over unbounded n), distinct
from both the kernel Q.E.D. Codex and the ADR 0036 §10.3 unproved-conjecture Observatory (it is
*stronger* than the latter — a sound decision, not a numerical-evidence conjecture). Design:

- **Decider, not faithfulness.** Here the claim's `walnut_predicate` IS the theorem (e.g. Thue-Morse
  overlap-freeness), and Walnut *decides* it. Two cases, with **different** trust strengths (both
  MECHANICAL, never a judge; both non-Q.E.D.):
  - **Closed sentence** (all variables bound — the common form, e.g. `A i,p …`): Walnut returns the
    bare token `true`/`false`. `true` → **DECIDED**, `false` → **REFUTED**. A 0-track token has no
    structure to re-derive, so this is *trusted as Walnut's decision* — sound only because the
    production runner is the real Walnut (`_default_runner`: input sanitization + stale-file deletion
    + clean-exit + fresh read), i.e. **Walnut joins the TCB** for this non-Q.E.D. tier (like Z3).
  - **Free-variable predicate** → a structured agreement automaton: `classify_agreement` → `universal`
    → **DECIDED** with an **independent re-check** (`recheck_walnut_certificate` /
    `automaton_is_universal`, ADR 0037 §7), `refuted` → **REFUTED**, `indeterminate` → **DEFER**
    (quarantined; never guessed).
- **Never Q.E.D., never promulgated.** A `WALNUT_DECIDED` record sets **no** `kernel_verified`, `qed`, or
  `promulgated`; it does **not** pass through `Promulgate`/`validate_path`. It is a distinct outcome in a
  distinct store. The Q.E.D. Codex remains kernel-only.
- **Faithfulness via formal-first.** The 3-body gap (predicate ↔ human claim) is handled by **formal-first
  publication**: the Walnut predicate + numeration is the authoritative statement of record; the prose is
  non-authoritative commentary. No new faithfulness gate; the renderer is *not* promoted into any TCB
  (the reason the kernel bridge, which would, is deferred).
- **Conjecturer generation.** A proposal role emits automatic-sequence FO conjectures (predicate +
  numeration + prose). LLM-proposed (the novelty bet); the daemon only *proposes*, Walnut *decides* — the
  propose/decide separation holds (Walnut, a decision procedure, is not an LLM).
- **Off by default / opt-in.** Like the Walnut backend: nothing wired into the default assembled pipeline;
  the operator opts the tier in. Live decisions require the Walnut binary (currently sandbox-blocked).

## 3. Why the trust boundary stays intact

| invariant | how it holds |
|---|---|
| 1 — `kernel_verified` only in `LeanVerifier.discharge` | the tier never sets it; Walnut decisions are a separate `FinishReason`, not a proof edge |
| 7 — Q.E.D. iff `kernel_verified` | `WALNUT_DECIDED` ≠ Q.E.D.; the tier never stamps Q.E.D. |
| an LLM never decides | the LLM *proposes* the conjecture; **Walnut** (a sound decision procedure) decides — independently re-checked for a free-variable agreement automaton, or trusted as Walnut's decision for a closed-sentence `true`/`false` (Walnut in the TCB, non-Q.E.D.) |
| promotion requires PROOF+FAITHFULNESS via `validate_path` | the tier does **not** promulgate — it is a parallel, non-Codex output; `validate_path`/`test_invariants` untouched, byte-identical |
| novelty never by an LLM judge | novelty is read by the unchanged **blind human panel** (ADR 0034 §5) |

`FinishReason.WALNUT_DECIDED` is additive and safe: `tests/test_invariants.py` does not reference
`FinishReason`. The tier ships with its **own** guard tests (a `WALNUT_DECIDED` record never carries
`promulgated`/`qed`/`kernel_verified`; DECIDED requires a re-checked certificate; indeterminate
quarantines) and an **adversarial soundness review** (a new tier is trust-adjacent).

## 4. The measurement — and the kernel-bridge gate

The tier exists to *measure* the only open question: does Walnut-backed discovery yield **blind-novel**
results? Run the unchanged blind novelty panel on the tier's DECIDED output (predicted, per the arc:
likely textbook — but now measured, not assumed). 

**Kernel bridge stays GATED** behind two conjunctive triggers (the eval's recommendation, recorded as
the ADR 0037 run-rung condition): (1) the tier yields **≥1 blind-panel-confirmed novel** Walnut decision,
**and** (2) a dedicated **bridge-synthesis reachability micro-probe** beats the on-paper RED. Only then is
the bridge built, behind an operator-signed ADR amendment authorizing renderer promotion into the
proof-edge TCB, with: formal-first publication, a restricted typed per-class rendering grammar, a
decider↔renderer round-trip/shared-IR agreement check, and a standing known-mis-statement adversarial
fixture set that must fail to promote.

## 5. Consequences

- A cheap (≈S–M), zero-new-TCB, invariant-preserving path to **measure** Walnut discovery, reusing the
  ADR 0037 backend + the reading-room. Nothing built here is throwaway if the bridge is later built.
- The honest status of a Walnut-decided result is explicit: *mechanically decided by Walnut over
  unbounded n, re-checked, but **not** kernel-Q.E.D.* — a distinct, weaker-than-Codex but
  stronger-than-conjecture tier.
- If the blind panel reads 0-novel (the predicted outcome), that is itself the measured finding that
  even the sound-unbounded-decision paradigm recovers textbook on this corpus — and the kernel bridge is
  *not* built, saving the project's scarcest resource (trust-critical review bandwidth). If it reads
  ≥1-novel, the gate opens and the bridge becomes justified. Either way, decided by evidence.

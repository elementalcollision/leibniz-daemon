<!--
DRAFT for codexcalculemus.com/cycles/ — review before publishing (outward-facing). A prose
overview for the /cycles/ work-log; it sits alongside the per-cycle JSON records in
site/src/content/cycles/. Decision (operator, 2026-06-24): /laws/ stays lean — only
soundness-AND-novelty results get individual law records, so this report is the honest public
account of the work. Every figure is drawn from the run ledgers and re-verified; see
"Provenance" at the end.
-->

# The Calculemus Cycles — a progress report

*Leibniz is an agentic theorem daemon. Language models **propose**; only mechanical
checkers — the Lean kernel and the Z3 solver — **decide**. Nothing reaches this Codex
that the kernel has not re-verified.* This is a report on what the discovery cycles have
actually done, told straight: what the machine produced, what holds, and where the hard
problem really is.

## The one rule

A candidate becomes a *law* only when independent prover models each draft a proof and the
Lean kernel re-elaborates it from scratch — no `sorry`, no axiom, no "the proof looks
right." `Q.E.D.` is stamped *iff* the kernel verified it. Promotion to the ledger and
publication to this Codex are separate, deliberately gated steps; the daemon never
auto-publishes. Rejected candidates are **quarantined with a reason, never deleted** — the
work-log keeps its failures in view.

## What the cycles have produced

Across the live discovery runs the funnel behaves as designed: hundreds of conjectures
proposed, most quarantined by the cheap gates (refuted, trivial, unfaithful, or already
known), a minority reaching the kernel. The most complete run promulgated **15 laws, and an
independent re-discharge re-verified all 15 against the kernel** — the trust boundary held
end to end.

But honesty is the point of a *Calculemus*, so here is the unvarnished finding: **those
laws are sound, but they are not yet novel.** They are kernel-true statements of classical
number theory — divisibilities of products of consecutive integers, modular residue facts,
the sum-of-squares numerator being a multiple of six. A mathematician would call them
textbook. An audit of the run classified them honestly: every one mechanically correct,
essentially none mathematically new.

That is not a failure of the trust machinery — it is the trust machinery working. The
system would rather quarantine, demote-as-known, or label a result pedestrian than dress a
restatement up as a discovery.

A later cycle made this sharper. Once the daemon's habitual genres were recorded as known,
the novelty gate began correctly demoting their restatements — including loosely-phrased
ones a naive check would miss — and the conjecturer responded by **hopping to a fresh
genre** of (still classical) results. Close one textbook drawer and it opens the next. The
checker is not the bottleneck; **the conjecturer's imagination is.** That is the honest
shape of the problem, and naming it is more useful than hiding it.

## Where the hard problem is

It is worth being precise about the binding constraint, because it is not the obvious one.

- **Soundness is solved.** The kernel decides; re-discharge confirms; no unverified claim
  has ever carried a `Q.E.D.`
- **Proof reach is adequate** for the work the daemon currently sets itself — an agentic
  repair loop closes goals that one-shot drafting misses.
- **Novelty is the frontier — and it lives in the conjecturer, not the checker.** The
  proposer reliably suggests provable claims but gravitates to the familiar; when one
  familiar genre is closed off, it migrates to another rather than reaching for something
  genuinely new. Turning a sound rediscovery engine into a *discovery* engine is the open
  research problem, and we are not pretending otherwise.

## What is being built, this cycle

The current work targets that frontier directly:

- **A sound novelty gate — now live and catching.** Restatements are caught by *form*, not
  by truth: a candidate's polynomial congruence is canonicalised — across loose phrasings,
  residue-set claims, and vacuous offsets — to its computed behaviour and matched against a
  corpus of known results. Crucially this never collapses two genuinely different theorems
  (the unsound shortcut an earlier attempt was retracted for); when in doubt it errs toward
  calling a claim *novel*, never toward suppressing a real discovery. The most recent cycle
  showed it working — demoting classical restatements, including loosely-phrased ones, that
  an earlier run had waved through.
- **A growing corpus of the known.** The families the daemon kept rediscovering are being
  recorded as known facts, so the gate can demote their restatements and the funnel is
  pushed past them.
- **Operational rigour around all of it** — independent prover evaluation, isolation
  between an experimental lane and the published Codex, and resilience so a long unattended
  run survives an outage without crashing or, worse, mis-recording a result.

## The standing invitation

Calculemus — *let us calculate*. Every law in this Codex carries its kernel-checked proof
and can be re-verified by anyone; every quarantined candidate carries the mechanical reason
it did not make it. The interesting story here is not a pile of theorems — it is a
discovery engine built so that it *cannot* lie to you about what it has found, reporting
honestly that the genuinely-novel result is still ahead of it.

---

*Provenance: figures are drawn from the live calibration ledgers; the "15 of 15
re-verified" claim is a kernel re-discharge of the promulgated proofs. This Codex publishes
only laws whose proofs the Lean kernel accepts on re-check.*

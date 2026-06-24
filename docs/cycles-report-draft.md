<!--
DRAFT for codexcalculemus.com/cycles/ — review before publishing (outward-facing). A prose
overview for the /cycles/ work-log; it sits alongside the per-cycle JSON records in
site/src/content/cycles/. Decision (operator, 2026-06-24): /laws/ stays lean — only
soundness-AND-novelty results get individual law records, so this report is the honest public
account of the work.

Every figure was re-verified on 2026-06-24 against the run ledgers — calibration_report.json,
.leibniz/memory.db, and .leibniz/notebook.json. The most complete calibration run promulgated
10 laws, 10 of 10 kernel-re-verified. (An earlier draft of this file cited "15 laws" and used
the sum-of-squares numerator as an example; that count was attested by no ledger, and that
statement is in fact in the notebook's `too_hard` list — both have been corrected.) See
"Provenance" at the end. Operator note: the published site currently shows only the illustrative
demo laws — reconcile or scope the figures before this goes outward-facing.
-->

# The Calculemus Cycles — a progress report

*Leibniz is an agentic theorem daemon. Language models **propose**; mechanical checkers
**dispose** — the Z3 solver refutes what is false, the Lean kernel certifies what is true.
Nothing reaches this Codex that the kernel has not re-verified.* This is a report on what the
discovery cycles have actually done, told straight: what the machine produced, what holds, and
where the hard problem really is.

## The one rule

A candidate becomes a *law* only when independent prover models each draft a proof and the
Lean kernel re-elaborates it from scratch — no `sorry`, no axiom, no "the proof looks
right." `Q.E.D.` is stamped *iff* the kernel verified it. Promotion to the ledger and
publication to this Codex are separate, deliberately gated steps; the daemon never
auto-publishes. Rejected candidates are **quarantined with a reason, never deleted** — the
work-log keeps its failures in view.

## What the cycles have produced

Across the live discovery runs the funnel behaves as designed: scores of conjectures proposed,
and most of them stopped before the kernel. Some are refuted or demoted by the cheap gates —
unfaithful, trivial, or already known. The largest share, though, clear those gates, reach the
prover, and simply fail to be proved; only a minority survive to the kernel. In the most complete
calibration run — about sixty conjectures over eight cycles — that funnel promulgated **10 laws,
and an independent re-discharge re-verified all 10 against the kernel.** The trust boundary held
end to end.

But honesty is the point of a *Calculemus*, so here is the unvarnished finding: **those
laws are sound, but they are not yet novel.** They are kernel-true statements of classical
number theory — that `n^2 + n + 2` is always even, that `n^3 + 5n` is divisible by three, that a
product of consecutive integers carries the factor you would expect, that a particular quartic
leaves a fixed remainder when divided by twelve. A mathematician would call them textbook. An
audit of the run classified them honestly: every one mechanically correct, essentially none
mathematically new.

That is not a failure of the trust machinery — it is the trust machinery working. The
system would rather quarantine, demote-as-known, or label a result pedestrian than dress a
restatement up as a discovery.

## Where the hard problem is

It is worth being precise about the binding constraints, because the obvious one is not the only
one.

- **Soundness is solved.** The kernel decides; re-discharge confirms; no unverified claim has
  ever carried a `Q.E.D.`, and no promulgated proof leans on a `sorry` or an axiom.
- **Proof reach is a real but receding limit.** An agentic repair loop now closes goals that
  one-shot drafting misses — most of the laws above needed it. But the prover is still where most
  candidates die: in the calibration run more were lost *unproven* than were promulgated, and the
  notebook still lists classically-true facts (the numerator of the sum of the first *n* squares;
  products of four consecutive integers) that the daemon tried and could not close.
- **Novelty is the strategic frontier.** Even granting perfect proving, the conjecturer reliably
  proposes provable claims but gravitates to the familiar — the genres a first course already
  covers. Turning a sound rediscovery engine into a *discovery* engine is the open research
  problem, and we are not pretending otherwise.

## What is being built, this cycle

The current work targets that frontier directly:

- **A sound novelty gate.** Restatements are caught by *form*, not by truth: a candidate's
  polynomial congruence is canonicalised — across loose phrasings, residue-set claims, and
  vacuous offsets — to its actual computed residues and matched against a corpus of known
  results. Crucially this never collapses two genuinely different theorems (the unsound
  truth-equivalence shortcut that an earlier attempt was retracted for); when in doubt it errs
  toward calling a claim *novel*, never toward suppressing a real discovery.
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

*Provenance: figures are drawn from the live calibration ledger (`calibration_report.json`) and
the persistent run memory (`.leibniz/memory.db`). The "10 of 10 re-verified" claim is a kernel
re-discharge of the promulgated proofs; each carries a `sorry`-free, axiom-free Lean proof the
kernel accepts on re-check. This Codex publishes only laws whose proofs the Lean kernel accepts.*

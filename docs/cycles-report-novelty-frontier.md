<!--
DRAFT for codexcalculemus.com/cycles/ — review before publishing (outward-facing). The honest
account of the novelty-frontier arc (ADR 0034 conjecturer-side novelty + ADR 0035 faithfulness-DSL
expressiveness). Every figure is drawn from the run ledgers (.leibniz-ab/{A,B,SA}/, the calibration
reports, and the blind-panel records) and is re-verifiable; see "Provenance" at the end. Operator
note: the published site currently shows only the illustrative demo laws — reconcile or scope the
figures before this goes outward-facing.
-->

# The Novelty Frontier — two experiments, one wall

*Leibniz is an agentic theorem daemon. Language models **propose**; mechanical checkers **dispose**
— the Z3 solver refutes what is false, the Lean kernel certifies what is true. Nothing reaches this
Codex the kernel has not re-verified.* An earlier report told the first honest finding: the machine
soundly **re-proves** textbook mathematics but does not yet **discover**. This is the report on what
happened when we tried to change that — and treated "can it discover?" as a question to **measure**,
not to assert.

## The question, made falsifiable

The daemon promulgates a law only when it can (a) state the claim in a small, mechanically-decidable
contract language, (b) hold the formal statement *faithful* to the claim by a bounded adversarial
search, and (c) get the Lean kernel to prove it — twice, from independent provers. The promulgated
laws were all *textbook*. Where is the bottleneck — the **proposer** (it reaches for familiar
shapes), the **language** (it can only state familiar shapes), or something deeper?

We built an honest instrument first: a read-only metric that scores how far each promulgation sits
from the known, and — the only referee that ultimately counts — a **blind panel** of independent
mathematician-graders who rate each law *textbook / variant / genuinely-novel*, never told which
experiment produced it, calibrated so that standard number theory (divisibility, quadratic residues,
multiplicative order, Fermat) counts as textbook. Then we ran two controlled experiments.

## Experiment 1 — a better proposer (the source)

We A/B-tested the conjecturer against itself on identical settings: one arm with steering only, one
arm that additionally **mines true patterns by computation** — scanning the integers for regularities
and handing them to the proposer as data instead of relying on its trained-in recall. Compute, not
memory.

It worked, as engineering: mining **doubled** the yield, from 13 promulgated laws to 26, at the same
proposal budget — because a computed pattern is true by construction, so it proves readily. But the
blind panel rated **all** of it — every law in both arms — **zero genuinely novel** (113 "textbook"
and 41 "variant" votes across the graders; not one "novel"). The mined laws were quadratic-residue
facts, found autonomously across many moduli but textbook all the same. **Changing the source moved
the volume and not the novelty.**

## Experiment 2 — a richer language (the grammar)

If the proposer wasn't the wall, perhaps the *language* was: the contract grammar could only state
polynomial congruences, so everything provable inside it was, by construction, that genre. So we
taught the faithfulness checker a new, genuinely different shape — `a^n mod m`, a fixed base raised
to the **variable** exponent — soundly. (The trick is exact and bounded: the powers of `a` modulo
`m` cycle with a fixed period, so the checker decides the claim over one whole period rather than an
incomplete window. Every other shape still safely declines rather than guess.)

This is a genre the machine literally **could not state** before. It used it: of 23 promulgated laws,
**16 were `a^n mod m` facts** — `2^n mod 7 ∈ {1,2,4}`, `7^n mod 16 ∈ {1,7,9,15}`, and the like —
each kernel-proved, none gamed. The genre truly moved: our structural metric, which only understands
polynomials, went **blind to 70% of the output** (it had understood 100% of the previous arm) — exactly
the signature of leaving the old language behind. And the blind panel rated them **zero genuinely
novel** (15 textbook, 4 variant, 0 novel): they are the standard cyclic behaviour of the powers of a
number modulo another — a first-year exercise via the *multiplicative order*. **Changing the grammar
moved the genre and not the novelty.**

## The wall

Two independent levers — the proposer's *source* and the contract *language* — each did exactly what
it was built to do, and each produced **zero** genuine novelty. That triangulates the answer, and it
is not the obvious one:

> The bottleneck is neither the proposer nor the grammar. It is the faithfulness **test** —
> specifically, a *pointwise, bounded-box* check (is there a counterexample in a small window?) used
> as the sole arbiter of whether a formal statement means what was claimed. That kind of test can
> only certify locally-checkable, elementary facts. It is **not** a limit of mechanical trust as
> such: a small trusted kernel can check arbitrarily deep proofs — the four-colour theorem, Kepler's
> conjecture, and Feit–Thompson were all machine-verified. **Bounded *trust* is not bounded *truth*.**
> The honest escape keeps `Q.E.D.` brutally formal but lets the faithfulness evidence be a checkable
> *certificate* — including exact, *unbounded* algebraic ones — instead of a bounded sample; the
> genuine wall then moves to where it belongs: not "is it true?" (the kernel settles that) but "does
> the formal statement match human intent?" — a *validation* question, audited, never hidden.

*(Refined 2026-06-25 after an independent five-model external review — see the project's
external-review reference. The first draft of this finding over-generalized "bounded-box check" to
"mechanical trust"; the corrected claim is above.)*

This is worth stating plainly because it is a *measured* result, not a hunch. We did not conclude
"novelty is hard." We changed the two things most people would change, measured both against a blind
human standard, and watched the novelty needle stay pinned at zero while everything else moved. The
frontier is now located precisely: genuine machine *discovery* under a hard trust boundary would
require a different notion of what it means to *check* a claim — one that admits mathematics not
decidable in a small box — without surrendering the guarantee that nothing false is ever stamped
`Q.E.D.` That is a research question, and an honest one to be left standing rather than papered over.

## What stands

Everything proved in these experiments is sound: every promulgated law carries a `sorry`-free,
axiom-free Lean proof the kernel accepts on re-check, and the faithfulness checker was independently
audited for the new construct before it ran. The negative result is about **novelty**, never about
soundness — the trust boundary held end to end, through every experiment, exactly as it is supposed
to. The machinery built along the way — the blind novelty panel, the structural-coverage tripwire,
the sound symbolic-exponent checker — remains, available and off by default, as the honest record of
where the wall is.

Calculemus — *let us calculate.* We calculated whether the engine could be made to discover, and the
calculation returned a clear, bounded, re-checkable *not yet, and here is exactly why.*

---

*Provenance: figures are drawn from the live calibration ledgers (`.leibniz-ab/A/`, `…/B/`, `…/SA/`)
and the blind-panel records. "Doubled, 13→26" and "16 of 23" are row counts in those ledgers;
"0 novel" is the consensus of four independent blind graders on the full promulgation sets (39 for
experiment 1, 19 distinct for experiment 2). The decisions and their soundness arguments are recorded
in ADR 0034 (§12) and ADR 0035 (§7). This Codex publishes only laws whose proofs the Lean kernel
accepts on re-check.*

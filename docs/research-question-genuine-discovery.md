# Research question — genuine mathematical discovery under a hard mechanical trust boundary

*A brief for external auditors / witnesses. Self-contained: assumes no access to the codebase.
We want you to (1) attack the conclusion below, and (2) answer the question — or tell us the
question is wrong. Adversarial, rigorous critique is more useful to us than agreement.*

## The system, in one paragraph

Leibniz is an autonomous theorem daemon. Language models **propose** conjectures and proofs; only
**mechanical checkers decide** — the Lean 4 kernel (for proofs) and the Z3 SMT solver (for
refutation and a faithfulness check). A statement becomes a promulgated *law* only when three
things hold: (1) it is expressed as a machine-checkable contract in a small arithmetic predicate
language (a "DSL": non-negative integers, `+ - *`, constant powers, constant mod/div, comparisons,
min/max, and — recently — `a^n mod m`); (2) it passes a **faithfulness gate**; and (3) the Lean
kernel verifies a proof of it, independently re-derived by two distinct prover models. `Q.E.D.` is
stamped **iff** the kernel verified it. The non-negotiable invariant — the reason the project
exists — is that an LLM never decides a proof, and **nothing false or un-faithful is ever stamped
`Q.E.D.`**

## The 3-body faithfulness problem (the crux)

The Lean kernel guarantees *proof ⟺ formal statement*. **Nothing mechanically guarantees *formal
statement ⟺ the human-readable claim*** — the claim the public ledger is held accountable to. A
kernel-valid proof of a *mis-stated* theorem is worse than no proof: it is most authoritative
exactly when it is most wrong. An LLM "does the statement match the claim?" judge is theater (it
shares the formalizer's blind spots), so we do not use one.

Instead, faithfulness is checked **adversarially and mechanically**: Z3 searches a bounded box
(inputs in `[0, 64]`) for a *gaming witness* — an input that satisfies the formal statement while
**violating** the human claim. No witness ⇒ faithful; a witness ⇒ rejected. The check is
**exact-or-DEFER**: every construct has an exact encoding so "UNSAT over the box" genuinely means
"no witness in the box," and anything not exactly encodable DEFERs (is refused) rather than guesses.

This bounded-mechanical check is the entire faithfulness guarantee — and, we now believe, the
binding constraint on novelty.

## The measured finding (the premise we want you to attack)

We treated "can the daemon *discover*, not just *re-prove*?" as an empirical question and ran
controlled experiments, scoring every promulgated law with a **blind panel of independent grader
models** rating each *textbook / variant / genuinely-novel* (blind to which experiment produced it,
calibrated so standard number theory — divisibility, quadratic residues, multiplicative order,
Fermat — counts as textbook).

1. **Changed the proposal *source*.** A/B test: LLM-recall conjecturing vs. additionally **mining
   true regularities by computation** (scanning integers for patterns, feeding them as data). Result:
   mining **doubled** the yield of true, kernel-proved theorems (13 → 26) and produced **0 / 39
   genuinely novel**. (The mined laws were quadratic-residue facts — found autonomously, textbook.)

2. **Changed the contract *grammar*.** We soundly extended the faithfulness checker to a genre it
   literally could not state before — `a^n mod m`, a fixed base to a *variable* exponent — decided
   exactly over the multiplicative-order period (so it stays exact-or-DEFER, never a bounded
   approximation). The genre genuinely **moved**: a structural metric that only understands
   polynomials went blind to 70% of the output. Result: **0 / 19 genuinely novel** — all standard
   cyclic-group facts (`2^n mod 7 ∈ {1,2,4}`, etc.).

**Conclusion (triangulated, re-checkable):** the novelty ceiling is **neither the proposer nor the
grammar** — it is the **bounded-mechanical-faithfulness model itself**. Anything that is
simultaneously (faithfulness-checkable over a bounded box) ∧ (automatically provable) appears to be
**elementary/textbook by construction.** Soundness held throughout; the negative result is about
*novelty*, never *correctness*.

## The question

**(a)** Is there a *different* trust-checkable notion of **faithfulness** that admits claims **not
decidable in a bounded box** — letting the daemon state and prove genuinely non-textbook
mathematics — **without** weakening the guarantee that nothing false or un-faithful is ever stamped
`Q.E.D.`?

**or (b)** Is genuine novel-**theorem** discovery *fundamentally* out of reach for an autonomous
daemon under a hard trust boundary — and if so, what is the **least-compromising real
contribution** instead (e.g., a clearly-labeled tier of genuinely-novel **conjectures** backed by
mechanical evidence but never claimed as proved; sheer breadth of verified elementary results; a
human-in-the-loop model where the human supplies the irreducibly-hard step)?

## The trap (please make sure your answer clears it)

Every widening we have tried merely **relocated** the textbook wall (polynomial residues →
cyclic-group residues, with novelty pinned at zero throughout). A good answer must say **why it does
not merely relocate the wall a third time**, and must be explicit about **where the residual trust
gap moves** (the 3-body gap never vanishes; it can only be relocated — to a better or worse place).

## Specifically, we would value your view on

1. **Is the conclusion sound?** Any flaw in the experiments, the blind-grading, or the inference
   that "the model, not the proposer/grammar, is the ceiling"? Is "everything bounded-decidable is
   elementary" actually true, or a false generalization from two genres?
2. **Faithfulness without the box.** The obvious move is to make faithfulness a **kernel-proved**
   *formal-statement ⟺ formalized-claim* equivalence (unbounded, sound by the kernel). Does that
   escape the 3-body regress or just relabel it (the *formalized*-claim vs the *human* claim gap
   remains)? Is the equivalence provable in useful cases, or only for the elementary ones we can
   already check?
3. **The conjecture tier.** Is a machine-generated "novel conjecture with computational evidence" a
   real mathematical contribution, or unverifiable noise that would dilute a ledger whose whole
   value is that it cannot lie? What evidence standard, if any, would make it credible?
4. **Prior art** we should learn from — automated conjecturing (e.g. the Ramanujan Machine),
   autoformalization, proof-assistant-backed discovery, or formal-methods notions of specification
   faithfulness that bear on the 3-body gap.

*We are not looking for encouragement. If the honest answer is "(b), accept the boundary," say so
and tell us what is genuinely worth building anyway. — Leibniz / Calculemus.*

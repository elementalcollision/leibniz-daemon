# Follow-up to the external witnesses — attack the synthesis

*Round 2 for the five reviewers (Fugu, DeepSeek V4 Pro, Kimi, GLM 5.2, Gemini 3.5 Thinking). Round 1
reviewed our premise and corrected it — thank you; the correction was adopted. This round asks you
to attack the **synthesis** your reviews produced. Self-contained; no repo access assumed.
Adversarial critique is the goal — tell us where this is still wrong.*

## What your round-1 review changed (so you can attack the new position, not the old one)

You unanimously corrected our over-claim. We adopted it: **the wall is not "mechanical trust caps
novelty."** The wall is Leibniz's *specific* faithfulness test — a **pointwise, bounded-box `[0,64]`
linter over a tiny arithmetic DSL, used as the sole faithfulness arbiter.** Bounded *trust* ≠ bounded
*domain* (a small kernel checks Flyspeck, Feit–Thompson, Robbins). So the program is now: **replace
the linter, keep the boundary.** From that, we synthesized a two-track plan.

### Track 1 — the conjecture tier (ship now)
A *separate* ledger of machine-observed-but-unproved candidates, never stamped `Q.E.D.`, never
touching the proved path (so the trust invariant holds vacuously). Hardened against the obvious
failure: the evidence stamp ("no counterexample in `[0,64]`") is emitted **only** when the predicate
is exactly encodable *and* a conclusive search found nothing — never when the search silently
couldn't run; it routes through a coverage+property probe (not the naïve search that is vacuously
satisfied by a tautologized property); and unproved conjectures carry **at least** the operator
publish-gate that proved laws do. Honest expectation: it inherits the ~0-novel read; its value is
honest *classification* + a curated proof-backlog, not breaking the ceiling.

### Track 2 — proof-carrying faithfulness (the real bet)
Replace the bounded box *as the thing that earns `Q.E.D.`* with a checkable **certificate** of the
statement↔claim correspondence; bounded Z3 demoted to cheap lint.
- **Stage A** — exact, *unbounded* structural-invariant certificates (polynomial-identity testing /
  Gröbner) — escapes `[0,64]` for an algebraic class with no new *untrusted* oracle (the certificate
  is re-checked, not trusted). Framed as the lowest-TCB first rung.
- **Stage B** — a kernel-proved `claim ↔ statement` bridge (unbounded, sound by the kernel), gated
  behind Stage A; honest costs named: the bridge proof is undecidable in general (may DEFER), and the
  claim→formal renderer is a new load-bearing trusted artifact.

We hold that the 3-body gap relocates to **validation** (human-intent → formalized-claim) — auditable,
mitigated by formal-first publication — and we explicitly **do not claim novelty is achieved**: the
escape removes the *expressiveness* ceiling soundly, but whether it yields blind-rated novelty is
*unmeasured*, to be tested with a pre-registered kill.

## The questions — attack the synthesis

1. **The triviality trap on Stage A (our sharpest worry).** In our pipeline a *non-triviality* gate
   runs **before** faithfulness and quarantines anything a single decision procedure (`ring`,
   `decide`, `omega`, `nlinarith`) closes outright. **Pure polynomial identities are exactly that —
   `ring`-closable — so they are killed as trivial before the certificate ever matters.** That makes
   "Stage A = exact-unbounded polynomial-identity certificates" look **inert** within our current
   DSL: the claims it would make faithful are pre-killed as trivial, and the *non-trivial* claims a
   structural certificate could bridge (convergence, irrationality, sequence/Pisano dynamics — the
   Ramanujan-Machine genre) are **not expressible** in the current DSL and need the harder kernel
   bridge (Stage B) anyway. **Is Stage A therefore inert, and is the real escape inseparable from
   Stage B + a richer claim language?** If you see a class that is (a) exact-certificate-checkable
   over an infinite domain, (b) genuinely *non-trivial* (not one-shot ring/decide-closable), and (c)
   expressible without a full higher-order claim language, name it — that class is the whole game.
2. **Does proof-carrying faithfulness actually escape, or relocate a third time?** Round 1 said it's
   the one direction that isn't pure relocation. But Stage B converts the expressiveness wall into a
   *proof-synthesis* wall (the bridge is undecidable) and grows the trusted base (the renderer). Is
   that a genuine escape or the same wall wearing undecidability's coat?
3. **The conjecture tier's real value.** Given it will (we predict) be ~0-novel and textbook-genre,
   is a curated ledger of "true-looking unproved elementary facts with a search certificate" a real
   contribution, or noise that dilutes a Codex whose whole brand is "only mechanical checkers
   decide"? What single evidence standard would make it credible rather than numerological?
4. **Did we mis-weight your panel?** We treated as high-confidence the points where all five of you
   *independently converged* (3-body→validation; conjecture tier iff sound+separate; proof-carrying
   as the escape) and as open the points where you *diverged* (whether the escape reaches novelty;
   GLM's "abstraction mining"; accept-vs-escape). Is that weighting right, or did convergence mask a
   shared blind spot — and is **abstraction mining** (emit compressing *definitions/lemma-schemas*,
   not theorems) underrated here?
5. **The honest meta.** Is "sound escape from the box, novelty unmeasured" the right
   characterization — or is that the same self-deception ("we moved something, surely novelty
   follows") that the two prior measured experiments already falsified? What would you *measure* to
   tell the difference before building?

*We will measure, not assert. If the honest answer to (1) is "Stage A is inert; the escape is Stage B
or nothing," say so plainly. — Leibniz / Calculemus.*

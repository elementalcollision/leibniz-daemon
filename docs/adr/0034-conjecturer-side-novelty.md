# ADR 0034 — Conjecturer-side novelty: making Leibniz reach beyond the textbook

**Status:** Proposed (awaiting operator approval — no code yet)
**Date:** 2026-06-24
**Extends:** 0009 (open-ended loop), 0018 (discovery frontier), 0026 (non-trivial
steering), 0031/0032 (novelty: corpus + structural matcher).
**Trust boundary:** untouched. Every mechanism here is *proposal-side*; the Lean kernel
and the mechanical gates remain the sole deciders. `Demonstratio.kernel_verified` is still
set only in `LeanVerifier.discharge`; `tests/test_invariants.py` stays byte-identical.

This ADR was scoped with a design panel (five independent approaches → judge → synthesis →
adversarial stress-test). The adversarial pass found a real flaw the synthesis only
half-admitted; that flaw is now §4 below, and it changes the recommendation. The numbers in
§1 and §4 were re-derived directly against the run ledgers, not taken from the panel.

---

## 1. Problem framing

The rung climb R1→R6 is done and the binding constraint has moved (`docs/optimization-roadmap.md`):
it is no longer prover reach or the trust boundary — it is **novelty**. The daemon proves
things soundly, and then we find it re-proved a textbook.

The measured organic-5 run is the evidence. Of 61 conjectures over 8 cycles, 10 promulgated;
all 10 re-discharged against the kernel, 0 with `sorry`/`axiom`. And all 10 are elementary
divisibility/residue facts in one variable — `n²+n+2` even, `n³+5n` ÷3, a product of
consecutive integers carrying its expected factor, a quartic ≡ 8 (mod 12). organic-3 had
exhausted the *consecutive-product* family; once those were recorded as known, organic-5
**hopped to quartics**. Close one textbook drawer, the conjecturer opens the next.

Three distinctions frame the work:

- **Genre-hop, not novelty.** The conjecturer is an LLM with a *closed set* of named results
  in its prior. Steered off one family it does not explore — it substitutes the next named
  family. ADR 0026's prompt bans and ADR 0031/0032's restatement-catchers slow the hop but do
  not change the *generative source*, so on their own they are whack-a-mole.

- **The novel-AND-tractable sweet spot.** A conjecture only promulgates if it is
  *formalizable* in the bounded DSL (polynomial congruences, integer inequalities, min/max —
  `backends/smt_z3.py::_conv`), *non-trivial* (survives `is_trivial`, which an automated
  tactic must NOT close — `gates/novelty.py:50`), AND *provable* by the ensemble within the
  difficulty band — and promulgation needs **N+1 = 2 distinct reasoners closing the same
  goal** (ADR 0029 panel). Genuine frontier mathematics is mostly unformalizable here or
  unprovable. The target is the narrow band that is all four at once. This is a **four-way
  intersection**, not the three-way one the panel first framed — see §7.

- **Corpus-novelty ≠ genuine novelty.** ADR 0032's matcher soundly answers "is this a
  restatement of a corpus entry?" But absence-from-corpus is *necessary, not sufficient*: the
  quartics were absent from the corpus and still textbook. The binary gate is a floor (it
  catches restatements). It does not *measure* how far a result sits from what we know, and it
  does not *propel* the conjecturer anywhere new.

## 2. The design panel

Five approaches, judged on novelty-potential × tractability × trust-safety × feasibility:

| Approach | Idea | Judge rank | Why |
|---|---|---|---|
| **empirical** | mine computed integer-space regularities; feed top-K as seeds | **1** | only design that changes the *generative source* (compute, not recall) |
| **frontier_anchored** | mechanical (LLM-free) arXiv-abstract analyst → tractable scaffolds | 2 | moves off textbook priors, but aims at harder/less-formalizable territory |
| **archive_extension** | generalize the daemon's *own* proven laws along a sparse signature axis | 3 | good idea, but mis-costed (see below) |
| **steering** | genre-kill list + curated novel-yet-elementary exemplars on `steer()` | 4 | cheapest, but alone only says "pick another signature" → genre-hop |
| **process** | propose→critique-novelty→revise loop; novelty reward in the controller | 5 | bolts an LLM novelty-nag on the same generator; partly violates invariant #4 |

Two panel claims were **wrong on the code and are rejected here**: `archive_extension` and
`process` both assume nearest-neighbor / sparse-region queries over the MAP-Elites Archive *in
signature space*. They are not reusable that way — the Archive is keyed by a 3-axis **behavior
descriptor** `(sub_area, technique, complexity)` (`selection.py:35`), which is **orthogonal**
to `congruence_signature` `(relop, m, reduced-poly, residues)` (`structural.py:320`).
Signature-space querying is *new* machinery, not "reuse what's there."

## 3. Recommended path (a graft, staged by leverage-per-effort)

No single design wins. The recommendation grafts the parts that survive scrutiny:

1. **Empirical pattern-mining is the spine** — the one change that moves the source.
2. **The existing `steer()` seam is the delivery vehicle** — reuse it for mined seeds and a
   small set of *positive* exemplars (the part of `steering` that adds reference points, not
   just bans).
3. **A structural-distance metric is built first, as read-only instrumentation** — but with
   eyes open about what it can and cannot tell us (§4).
4. **arXiv anchoring and archive-generalization are deferred, speculative** — only if the
   spine plateaus.

Concrete seams (all proposal-side, upstream of every gate):

- **`leibniz/pattern_mining.py` (new).** Pure compute, no LLM, no verdicts. Enumerate
  univariate polys conservatively (degree ≤ 4, |coeff| ≤ 10); for `m ∈ 2..64` compute the
  residue set `{P(i) mod m}`; canonicalize via the *existing* `structural.congruence_signature`
  (zero new math); drop signatures already in the corpus; emit top-K `(poly, m, residue_set)`
  as **text seeds**. The ProvabilityScore must avoid the triviality floor (§7).
- **`leibniz/discovery.py` — extend `steer()`/`DiscoveryNotebook`.** Blend ≤3 mined seeds and a
  small fixed `corpus/novelty_exemplars.json` block into the existing composition; add a bounded
  (≤6) family-level genre-kill list (sibling of the persisted `avoid` bucket). Everything capped
  so the prompt stays bounded.
- **`leibniz/pipeline.py::Survey.run`.** Also return mined seeds (origin-tagged) so they route
  through the *existing* seed pipe (`daemon.py::_run_seeds`) — no new routing path.
- **`leibniz/providers/__init__.py` — `AUTOFORMALIZE_PROMPTS[Role.CONJECTURE]`.** One framing
  line: "when a COMPUTED PATTERN seed is present, treat it as empirical data to formalize, not a
  topic to free-associate from." Proposal context only.

## 4. The hard problem the panel surfaced: measurement circularity

This is the centerpiece, and it is why this ADR does not promise a win.

The proposed success metric is *minimum distance in `congruence_signature` space* between a new
promulgation and everything known. But that space **is** `(relop, m, coeffs mod m, residues)`
over the narrow polynomial-congruence DSL — the *same* space that produced the textbook
clustering we are trying to escape. A miner that enumerates polys and canonicalizes via the
same function will, *by construction*, populate new signature cells — moving any distance
distribution rightward and growing the cluster count — **whether or not anything mathematically
novel happened.** A fresh `(P, m)` with a new residue set is a new drawer in the same cabinet.

> **The metric and the generator share a coordinate system, so the metric cannot referee the
> generator.** A mechanical signature-distance dashboard can move "right" on pure drawer-hopping.

I measured the coverage gap directly against the 10 organic-5 promulgations:

- **0 / 10** persist a signature-consumable property at all. `memory.db` stores the
  natural-language `statement` and the cheap-refute *negation*, never the canonical
  `claim_property` the matcher consumes (it is computed transiently in FORMALIZE —
  `novelty.py:82` — and dropped). *So the metric has an unstated prerequisite: persist or
  reconstruct the property.*
- Reconstructed to the DSL form, **10 / 10** are clean polynomial congruences → 6 distinct
  signatures. The metric covers our textbook output **perfectly**.
- And it goes **blind exactly where novelty would live**: `congruence_signature` returns
  `None` for symbolic exponents (`2^n`), named functions (`gcd`, factorial — still DSL-DEFERred
  per ADR 0030), inequalities, and renamed-multivariate claims. The instrument is best at
  measuring the genre we want to leave and worst at the genres we want to reach.

Conclusion: the mechanical metric is **necessary but not sufficient, and must never be the
go/no-go gate.** It is useful as a *negative* signal (if signature-distance does NOT move, we
have certainly not diversified) and as a coverage tripwire (a rising fraction of `None`-signature
promulgations is itself a sign of leaving the textbook DSL — track it). It is not a *positive*
proof of novelty.

## 5. How we measure success — honestly

Three measures, in order of trust, with the mechanical ones explicitly subordinate to the human read:

1. **Operator blind-rated genuine-novelty fraction (primary, irreducible).** Periodically, a
   sample of promulgations is rated textbook / variant / genuinely-novel-and-interesting — by a
   human, blind to origin. This is the only check on the corpus-vs-genuine gap, and it must stay
   human: an LLM scoring novelty would put a judge on the novelty decision, violating invariant
   #4 ("novelty is settled by retrieval + a decision procedure, never by a judge").
2. **Signature-distance + coverage (secondary, mechanical, necessary-not-sufficient).** Track
   the distance distribution, the distinct-cluster count, AND the `None`-signature fraction.
   Read as a *tripwire*, never a gate (§4).
3. **KNOWN/TRIVIAL fraction and genre entropy (mechanical, already partly available).** Does
   the share quarantined KNOWN/TRIVIAL fall and the family histogram spread? The roadmap already
   asks "does the KNOWN fraction move?"; this operationalizes it.

**Pre-registered kill condition for the real bet (Stage 2).** Mining is abandoned if, after a
calibration run, BOTH: (a) the operator-rated genuine-novelty fraction of *mined-origin*
promulgations does not exceed the current 0/10 baseline by a pre-set margin, AND (b)
mined-origin promulgations do not clear the triviality gate at a rate distinguishable from
chance. "The distance distribution shifted right" is **not** a success signal (it shifts on
drawer-hopping). We require a metric that can *fail*.

## 6. Why trust is untouched (and two explicit prohibitions)

Every seam sits upstream of the conjecturer, which sits upstream of every decision. The chain is
unchanged: Conjecture → cheap-refute → **novelty gate** → faithfulness gate (all before proof
compute) → Derive → kernel discharge. Specifically:

- Pattern-mining emits *seeds* (context), never verdicts. A mined pattern that is a disguised
  restatement is caught by the novelty gate matching the *claim's* signature; a too-simple one
  by triviality; an unprovable one fails Derive as UNPROVEN into the existing weaken-and-retry.
- No gate, kernel, or `TrustPolicy` change. `kernel_verified` is still set only in
  `LeanVerifier.discharge`; `Q.E.D.` iff `kernel_verified`. `tests/test_invariants.py` stays
  byte-identical.
- Reversible: if yield is poor this is proposal-side tuning — disable mining, revert to the
  frontier survey. No discovery is lost (quarantine, not deletion, is unchanged).

**Prohibition 1 — the signature-distance metric may rank or nudge, but must NEVER drop a
candidate.** A proposal-side distance *prefilter* that silently discards "too-close-to-corpus"
candidates before the conjecturer sees them would move a novelty judgment into untested
proposal code, outside `tests/test_invariants.py`'s view — doing the novelty gate's job in the
wrong place. The sole novelty arbiter stays `gates/novelty.py`. The metric is context, exactly
as trust-equivalent to the `FrontierController` band today.

**Prohibition 2 — no LLM novelty-scorer.** We explicitly reject the `process` design's
`critique_and_revise` novelty score: it is an LLM judging its own novelty (gameable, and
redundant with the *sound* mechanical gate). Novelty stays mechanical (retrieval + structure).

## 7. Tractability is a four-way intersection (the live risk)

The band a mined seed must hit is **novel ∧ in-DSL ∧ non-trivial ∧ within-panel-reach**, and
the middle two pull against each other:

- The novelty gate runs `is_trivial` **first** (`novelty.py:50`); ADR 0025 put `ring`/`nlinarith`
  etc. in the trivial-tactic set. A ProvabilityScore that "favors small residue sets and low
  degree" — i.e. what makes a claim easy — optimizes straight toward the `ring`/`decide`-closable
  **trivial** floor. Push toward provable and you push toward trivially-rejected; push toward
  non-trivial and you push toward the ensemble's reach wall (decomposition closed 0/85 sub-lemmas
  historically; the repair panel is the engine, ~50% reach).
- Therefore the ProvabilityScore must explicitly target the *non-trivial-but-reachable* middle,
  not "simplest." A plausible failure mode is that mined seeds promulgate ~nothing
  (trivia-filtered or unproven) — the too-low-band failure. Stage 2 must report this volume, not
  assume it.

This is also why Stage 2 is honestly a *better-steered hop within a slightly larger drawer*
(compute-driven point-selection in the same expressivity envelope), not the "changes the source"
the panel oversold. It is more than fancier steering and less than genuine reach into new
mathematics — and that is the most honest framing of the bet.

## 8. Cost

Promulgation requires the expensive frontier panel (organic-5: $15.89 / ~2.4 h / 8 cycles for
10 laws, N+1=2 distinct closers). Mining CPU is negligible (~1 s/cycle), but **breadth
multiplies prover spend linearly** against a ~50%-reach, 2-of-N funnel: more distinct clusters
attempted = proportionally more panel calls. Effort: Stage 0 ~80–120 LOC; Stage 1 ~100 LOC;
Stage 2 ~600–800 LOC.

## 9. Staged plan — what to try first

- **Stage 0 — instrumentation first (lowest risk, do this regardless).** Persist/reconstruct the
  canonical `claim_property` for promulgations and build the signature-distance + coverage
  metrics as **read-only**, replayable over existing runs. Establishes the baseline §5 needs.
  ~80–120 LOC. *Solid.*
- **Stage 1 — steering graft (cheap, but honestly whack-a-mole).** Genre-kill list + curated
  `novelty_exemplars.json` + the one framing line, through the existing `steer()` seam. Bare
  steering scored 2/5 on novelty for good reason; we do it because it is nearly free and is the
  delivery vehicle Stage 2 needs — not because it breaks textbook closure. (Caveat: the curated
  exemplars are a human injecting novelty the system can't yet generate; they don't scale past
  the operator's imagination, and the ≤6 kill list just lengthens the hop. Honest.) ~100 LOC.
  *Solid-but-limited.*
- **Stage 2 — the empirical spine (the real bet).** `pattern_mining.py` wired through
  `Survey.run` and `steer()`. Start conservative. Judge it by the §5 *kill condition*, not by
  the distance dashboard. ~600–800 LOC. *Plausible but unproven — the simplicity/triviality
  collision (§7) is the live risk.*
- **Stage 3 — speculative, only if Stage 2 plateaus:** (3a) promote the metric to a *soft* sparse-
  signature nudge (subject to Prohibition 1); (3b) the LLM-free arXiv analyst (shakier tractable
  bar); (3c) archive-generalization in signature space (needs the new signature index; risks
  orbiting the one proven family). All require building signature-space machinery that does not
  exist today. *Speculative.*

## 10. Open questions for the operator

1. **Authorize Stage 0 + Stage 1 now?** Both are nearly-free, sound, and reversible; Stage 0 is
   needed to measure anything.
2. **Greenlight Stage 2 as a pre-registered experiment** (with the §5 kill condition), or hold
   until Stage 0/1 data is in?
3. **Who does the blind novelty rating** (§5.1), and at what cadence? It is the only true success
   signal and it must be human.
4. Accept the honest framing that this targets a *wider textbook drawer*, with genuine
   beyond-DSL novelty (3b/3c) explicitly deferred and speculative?

## 11. Consequences

- If approved: Stage 0/1 land behind config flags (off by default); Stage 2 runs as an
  experiment with a defined kill condition. The trust boundary is unchanged throughout, so the
  downside of an ambitious conjecturer is bounded — the kernel and the (now-sound) gates still
  decide every result.
- If the bet fails honestly (kill condition trips), we will have *measured* that elementary
  integer-pattern mining stays inside textbook closure — itself a real result, and a sharper
  statement of where genuine mathematical novelty actually requires leaving the bounded DSL.
- This ADR deliberately ships its own strongest objection (§4). The point of a *Calculemus* is
  that we do not oversell what we can measure.

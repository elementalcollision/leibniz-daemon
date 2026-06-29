<!--
External-witness brief: the SECOND-DOMAIN (Gate B0) decision for the post-D0 program (ADR 0042 Track B).
Composed 2026-06-29 to validate/redirect the choice of a second finite-witness domain BEFORE building a
verifier for it (Track B1). Advisory only (invariant 4: no LLM decides). Responses get adversarially
synthesized and folded into the Gate B0 finding + the Track B1 ADR before any build. Prior rounds:
external-witness-brief-tool-foundation.md (ADR 0041), external-witness-brief-2026-06-26.md (direction),
external-witness-brief-acceleration.md (GPU/Python ops).
-->

# External-witness brief — the second-domain decision (Gate B0)

**Status:** composed 2026-06-29 for the 7-model witness round. **Advisory only** — input informs the
Gate B0 finding and the Track B1 ADR; a human approves; no model's verdict is binding (invariant 4).
**Disposition:** the operator collects the 7 responses, runs an adversarial synthesis (surviving guidance
only), and folds it into the B0 finding before any verifier is built.

**Why now:** Gate D0 came back **RED** — the autonomous-discovery bet is foreclosed *for constant-weight
codes (CWC)*. The operator chose a measured program (ADR 0042) whose whole point is to find out whether
that RED is CWC-specific or universal. Track B asks: *is there a second finite-witness domain where a
stronger producer could actually beat a record* — and if so, which? Before we spend build effort on a
new-domain verifier, we want external perspective on the **selection criterion** and the **candidates**.

---

## The prompt (given verbatim to each of the 7 witnesses)

> You are advising on a research-direction decision for **Leibniz**, an agentic theorem/discovery daemon.
> Your input is **advisory** — it informs a decision record that a human approves; no model's verdict is
> binding. Be rigorous and adversarial; we value dissent over validation.
>
> **What Leibniz is — and its one non-negotiable.** LLMs **propose**; only **mechanical checkers** (the
> Lean 4 kernel, Z3, automated table-of-record oracles) **decide**. The invariant is *"nothing false is
> ever stamped Q.E.D."*, enforced in code. The trusted computing base is small and explicit. This
> boundary is the product; we will not weaken it for capability. A usable "discovery" must therefore be a
> **finite witness a kernel can re-check**, with **novelty settled by a public table of record, never by
> an LLM judge**.
>
> **What we measured (the ground truth you must design around).** We ran a full autonomous
> record-*beating* arc on binary constant-weight codes A(n,d,w) — lower bounds vs. Brouwer's public
> table — across every producer: exact CP-SAT (max-clique), heuristic local search, group-theoretic
> structural construction, and an LLM **FunSearch** loop (an LLM writes construction *programs* → run in
> a locked-down sandbox → an untrusted fitness check → automated novelty oracle → the Lean kernel
> re-checks any "beat"). Across 100+ cells: **matched many records, beat none.** Then **Gate D0** (a
> deliberate diagnostic): on 5 cells the daemon's autonomous search missed, a stronger producer (exact
> CP-SAT) found the record and the **kernel verified all 5**. Reading: there is **no encoding/expressivity
> gap** (every record is a finite kernel-checkable witness), and **the producer is the wall** — but
> stronger producers only **match**. Two structural reasons the "beat" was dead-on-arrival in CWC:
> (a) where exact search ran to optimality it **proved the record optimal** — there is nothing left to
> beat; and (b) the genuine record *improvements* in CWC come from **deep human algebraic constructions**
> that a search/LLM producer does not reach. **Soundness held throughout; the boundary never moved.**
>
> **The decision you are advising.** We are NOT trying to revive autonomous discovery on faith. We adopted
> a measured program: (A) build out **verification amplification** — a stronger/human/research producer
> proposes a finite construction, the kernel re-checks it — which we have *built* and which is GREEN
> (it just kernel-verified the 5 D0 records + classical cases, 6/6); (B) **find a second finite-witness
> domain** where a producer-strength swing could actually be *meaningful*; (C) a sound, operator-gated way
> to admit a *verified* stronger checker; and only then (D) **spend on a much stronger producer** (GPU
> search / SOTA SAT / long exact runs) to try to **beat** a record. (D) was dead in CWC; the purpose of
> (B) is to discover whether any domain makes (D) live.
>
> **The crux for you (Track B / "Gate B0").** From the CWC autopsy, the property a second domain *must*
> have — the one CWC lacked — is **a frontier where records are actively set/improved by SEARCH we can
> strengthen** (heuristic / SAT / GPU), *not* one advanced only by human algebra and *not* one already
> proven optimal in its reachable range. It must *also* keep a **finite, kernel-checkable witness** at
> acceptable representation cost and a **public table of record** for automated novelty.
>
> **Our widened candidate survey (grounded; scored on representation, producer-beatability-by-search, and
> oracle):**
>
> | domain | witness / kernel check | frontier: who sets records? | public table | our read |
> |---|---|---|---|---|
> | **LABS** (low-autocorrelation binary sequences) | tiny ±1 sequence; sidelobe energy = sum of squares of aperiodic autocorrelations (trivial finite arithmetic) | **search**: optimal proven only to N≈66; N>66 best-known set by heuristic/GPU search, *actively improved 2024–25* (memetic tabu, GPU SAW+DFS) | yes (merit-factor records) | top: cheapest representation + genuinely search-beatable, real-valued objective |
> | **Covering designs C(v,k,t)** (La Jolla Covering Repository) | blocks of a v-set; check every t-subset is covered (finite, CWC-adjacent) | **search + synthesis**: live best-known table, contributed over 30 yrs, **updated 2026**; greedy/lexicographic + synthesis records | yes (La Jolla, v<100,k≤25,t≤8) | top: live search-set table, CWC-adjacent build, minimization objective |
> | **Ramsey lower bounds** R(...) | explicit graph/coloring avoiding a monochromatic clique; check = enumerate k-subsets (finite but combinatorial) | **search**: strongest evidence — 2024–25 records set *by SAT / SAT-modulo-symmetries* | yes (Radziszowski dynamic survey) | high ceiling, heaviest kernel check / largest witnesses |
> | Golomb rulers | mark set; all pairwise differences distinct (trivial) | search, but orders ≤28 now **proven optimal**; beating >28 needs *years* of distributed compute | yes | cheap witness, but beatable region astronomically compute-hard |
> | MOLS N(n) | k Latin squares + orthogonality check (finite) | mostly **constructions** (2024: N(54) 5→8 etc. via codes) — construction-driven, like CWC | yes | CWC-wall risk (algebra, not search) |
> | unrestricted A(n,d) codes | code + pairwise Hamming distance (near-trivial reuse of our CWC assets) | **constructions** (cyclic/BCH/Delsarte-Goethals) — construction-driven | yes (log₂A(n,d) tables) | cheapest BUILD, but most likely to re-hit CWC's exact wall |
>
> Our current lean: **LABS** (cheapest path to a *meaningful* swing), with **covering designs** and
> **Ramsey** close behind; the rest flagged for CWC-wall risk or intractable beatable regions.
>
> **Please answer, structured:**
> 1. **The selection criterion.** Is "records are actively set by *search we can strengthen*" the right
>    discriminator for a *meaningful* producer swing — or is there a sharper one (e.g. a measurable
>    "construction-vs-search gap", or a domain where a representation GREEN actually exists)? Steelman the
>    case that **every** finite-witness domain re-hits the producer wall, so Track B (and therefore D)
>    should not be attempted at all.
> 2. **Recommend a domain.** Pick from the shortlist or propose one we missed, with explicit reasoning on
>    (i) finite kernel-checkable witness + representation cost, (ii) is the *beatable* part of the frontier
>    set by search we can strengthen (not human algebra, not already proven-optimal, not astronomically
>    compute-hard), (iii) public table of record.
> 3. **Red-team the top three (LABS, covering designs, Ramsey).** For each, name the most likely way it
>    *secretly re-hits the CWC wall*: reachable range already proven-optimal; "records" actually from
>    theory not search; kernel check intractable at interesting sizes; objective real-valued/ill-posed for
>    an exact oracle; witnesses too large to render. Give the concrete pre-build probe that would expose it.
> 4. **Soundness.** Does your recommended domain keep the invariants clean — a *finite* witness the kernel
>    re-checks, novelty by a public table (not a judge), no LLM in a deciding role? Flag any domain whose
>    "witness" smuggles in structure a kernel cannot independently re-derive.
> 5. **The meta-question — should we even pursue (D)?** Suppose Track B finds a beatable frontier. Is
>    "Leibniz beats a heuristic search record" actually valuable and on-mission for a *sound verification +
>    amplification* instrument — or is the amplification spine (A), plus sound tool-admission (C), the real
>    product, with (D) a costly distraction? Under what condition would you greenlight the billable swing,
>    and under what condition would you tell us to stop at A (+C)?
> 6. **One thing we're likely getting wrong.** Your single most important warning or contrarian point.
>
> Be concrete and cite mechanisms, not platitudes. Assume we hold the soundness line absolutely; design
> within it, not around it.

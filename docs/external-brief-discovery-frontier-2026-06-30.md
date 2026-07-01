<!--
External research + proposal brief. Hand this to the external agent panel. Their output is ADVISORY
(Leibniz invariant 4: no LLM decides; novelty is settled by a decision procedure, never a judge). It informs
an operator decision about the program's next major direction. Self-contained: everything needed is below.
-->

# External brief — how should Leibniz reach *genuine, sound-checkable* discovery next?

You are an external research advisor to **Leibniz**, an agentic theorem daemon. We want your **grounded
research and ranked proposals** for the program's next major direction. Your output is **advisory** — in
Leibniz, LLMs only *propose*; only mechanical checkers *decide*. Be brutally honest; we would rather hear
"the ceiling is X" than an optimistic plan that dies at a wall we already measured.

## 1. What Leibniz is (the rules of the game)
- **Propose/decide split (non-negotiable).** LLMs may only propose. A result is accepted **iff** a mechanical
  checker confirms it: the **Lean 4.31 kernel** (proofs), **Z3** (SMT), **Walnut** (first-order statements
  about automatic sequences), or a **sound, DOI-pinned table oracle** (novelty). `Q.E.D.` is stamped only by
  the kernel. No "the proof looks right" shortcut ever reaches a promulgated law.
- **Novelty is a decision procedure, never a judge.** An "improvement" is settled by exact comparison
  against a machine-readable table of record + retrieval — not by an LLM's opinion.
- **Soundness is the whole point.** Nothing false may ever be stamped. We accept *incompleteness* (rejecting
  true things we can't check) but never *unsoundness*.
- **Measure before build.** Every build is gated by a cheap, falsifiable probe with a pre-registered exit
  criterion. We kill directions on $0 evidence before spending.

## 2. What is already built and working
- The trust boundary + the full checker stack (kernel via Docker; Z3; Walnut; validated table oracles).
- A **verification-amplification spine**: external finite constructions → sound checker → **kernel-checked,
  audit-tier corpus** (provenance'd, never promulgated). This is the current *product*.
- Sound witness checkers + Lean renderers for **covering designs C(v,k,t)**, **constant-weight codes
  A(n,d,w)**, and **Ramsey** (toy regime).
- A research scraper (weekly arxiv/ECCC/etc. feed) and a seeds→proposer path.
- The capability ladder R1–R6 is substantially complete. **The binding constraint is now NOVELTY — genuine
  discovery — not the trust boundary or prover reach.**

## 3. The measured walls (DO NOT re-propose these — they are killed on evidence)
This is the most important section. We have spent months measuring where discovery is *not* reachable:

- **Producer wall (autonomous table-beating is dead at reachable scale).**
  - Covering designs: exact CP-SAT over **71 tractable OPEN cells (t=2..8)** found **0 beats**; 22 records
    machine-proven optimal. The "D-line" (producer swing) is **banked** — no reachable-and-beatable frontier.
  - Constant-weight codes: a generic producer **cannot even reach** the Brouwer frontier (let alone beat it).
  - A 7-family novelty scout (packings/Steiner, binary codes A(n,d), difference sets, Costas/Golomb,
    orthogonal & covering arrays, additive combinatorics — caps/Sidon/sum-free, and Walnut/Z3/proof-
    compression) returned **ALL DEAD** as autonomous table-beats.
- **The structural law we derived** (please attack it, or exploit it):
  > *Wherever a positive witness is cheap for the kernel to `decide` (a polynomial-size predicate), the
  > record at reachable scale is already proven-optimal, closed-form, or exhaustively classified. The
  > cheap-witness band and the open-headroom band do not overlap.*
- **Decide wall.** Objects whose predicate is a *search* (Ramsey "no s-clique", packing optimality, Costas
  optimality) are exponential for the kernel's `decide` — intractable at frontier. A sound verdict there
  needs a **certificate architecture** (an external fast search emitting a small kernel-checkable
  certificate — the DRAT/LRAT analogue), not `decide`.
- **Oracle wall.** Automated novelty needs a *single, machine-readable, witness-shipping* table (like the La
  Jolla covering repo). Most families require a cross-source merge → no clean oracle → novelty degenerates
  to a judge (forbidden). This alone killed several families.
- **Ingestion wall.** The literature feed carries **title+abstract+citation only**; over 220 on-disk records,
  **0** carried a machine-usable finite witness. Papers publish *methods and theorems*, not enumerated
  witnesses; reconstructing a witness from a method is itself the (unsolved) producer problem.

**Net:** free-CPU autonomous discovery-by-table-beating is structurally exhausted. The trust boundary works;
amplification is a real but *non-novel* product (it re-verifies known constructions).

## 4. The questions we want you to research and answer
**Q1 (strategic).** Given §3, what is the **highest-expected-value path to genuine, sound-checkable
mathematical discovery** under Leibniz's trust boundary? Is genuine autonomous discovery reachable at all, or
is verification-amplification the honest ceiling? Defend your answer against the structural law in §3.

**Q2 (concrete proposals).** Evaluate, improve, and rank the candidate bets below — and **propose your own**
if you see a better one. For each, the key question is: *how does it escape the walls in §3 while staying
sound?*
  1. **Certificate architecture** — make the exponential-predicate objects (Ramsey, packing/Costas
     optimality, unsatisfiability-style non-existence) sound-checkable via a small kernel-verified
     certificate. Which object, which certificate format, and is there reachable open headroom there?
  2. **Full-text witness *reconstruction* producer** — turn a paper's construction *method* (base block +
     automorphism group, cyclic/difference construction) into an explicit enumerated witness the kernel can
     check. Is this feasible enough to yield novel-to-us (or genuinely novel) sound-checked results?
  3. **A different *kind* of result than a table beat** — e.g. new lemmas / identities / inequalities
     discovered and *decided* by Z3 or Walnut or the kernel, where novelty is settled by retrieval + a
     decision procedure. Is there a class where genuine, checkable, non-rediscovery output is reachable?
  4. **A new domain** with an intrinsically cheap sound checker AND genuinely open reachable headroom AND a
     clean oracle — i.e. a counterexample to our structural law. If one exists, name it.

**Q3 (first probe).** For your top 1–2 proposals, give the **cheapest falsifiable measure-before-build
probe** and its **exit criterion** — the $0-or-cheap experiment that would confirm or kill it before any
heavy build. Say explicitly if a proposal requires billable/GPU compute and at what stage.

## 5. Constraints your proposals must respect
- **Soundness first.** Explain exactly how the proposed output is *mechanically decided* (kernel/Z3/Walnut/
  certificate-checker) and how an LLM error cannot leak into an accepted result. If the checker isn't sound
  or isn't tractable, say so.
- **Novelty by decision procedure.** State how novelty is settled (which oracle / retrieval + decision
  procedure). "An LLM judges it novel" is disqualifying.
- **Reachability honesty.** We have been burned four+ times by producers that can't originate structure.
  Rate producer-reachability candidly (free-CPU / modest / heavy-billable / unreachable).
- **Prefer a cheap first probe.** A proposal with a $0 falsifiable probe beats a grander one without.

## 6. Output format (per proposal)
Return a ranked list; for each: **title · thesis (1 sentence) · mechanism (the sound checker) · soundness
argument (how it respects the trust boundary) · how it escapes the §3 walls · producer-reachability · novelty
mechanism (the oracle/decision procedure) · first probe + exit criterion · est. cost/stage · expected value ·
top risks · kill-criteria.** Then a one-paragraph **honest bottom line**: is genuine discovery reachable, and
if so, what is the single first thing to run?

## 7. Reference (Leibniz internal findings, if useful to cite)
`docs/results/tier1-results-2026-06-30.md` (covering GATE-1, 0 beats), `docs/results/tier2-results-2026-06-30.md`
(decide-wall + soundness backstop), `docs/results/novelty-frontier-scout-2026-06-30.md` (7-family scout, all
DEAD + the structural law), `docs/ingestion-pipeline-baseline.md` (ingestion RED),
`docs/optimization-roadmap.md` (program state), `docs/adr/0045-*` (the deferred construction proof-edge),
`docs/gate-b2-ramsey-decide-wall-finding.md` (the certificate motivation).

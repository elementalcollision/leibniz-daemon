<!--
Strategic-discovery handoff (operator decision 2026-07-02): the formalization ladder is banked
(F1+F2a merged; F2b brief out; F2c = Observatory per ADR 0046). This queues the DISCOVERY pivot.
Written for fresh sessions, in the style of docs/handoff-terwilliger-sessions-2026-07-01.md — read
that doc's "standing traps" and process constants first; they all still apply.
-->

# Handoff — Terwilliger discovery pivot (2026-07-02)

## State snapshot (main at `8001338`+)

PRs #230–#236 merged. Reach probe verdict: the base 2005 three-point family **cannot discover** — where it
solves, post-2005 methods already win; the d=12 frontier cells are **measured Delsarte-ties** (bound-blocked).
Solve leg is FIXED (eq.(8) normalization + SDPA-GMP); d≥10 faithfulness validated; three kernel-attested
certs banked; F1 whole-cert-in-kernel; F2a weak duality in Lean/Mathlib. The umbrella-Mathlib REPL bug is
fixed and the images are rebuilt. Discovery evidence and pivot options: `docs/results/terwilliger-reach-probe-2026-07-01.md`,
`docs/results/terwilliger-solve-leg-2026-07-02.md`, scope doc "Discovery outlook".

## Ticket D1 (task #102) — Johnson-scheme (constant-weight) Terwilliger build  ← START HERE

**Kickoff prompt:**
> Build the constant-weight (Johnson-scheme) Terwilliger three-point producer — task #102. Read
> `docs/handoff-terwilliger-discovery-2026-07-02.md` (D1) first; standing traps in
> `docs/handoff-terwilliger-sessions-2026-07-01.md` still apply.

The scope doc's panel-D1 option: a *separate* algebra build (new β, new blocks) targeting Schrijver's
**Table II** A(n,d,w) cells. Measure-before-build ladder: (1) transcribe the constant-weight block
structure; (2) float-reproduce 2–3 Table II cells (the formulation-faithfulness gate — the unrestricted
build's exact analogue of (19,6)/(20,8)); (3) reuse `certify_lp`/`kernel_verify_lp` unchanged for the exact
+ kernel legs (they are structure-agnostic given `collected()`-style specs); (4) only then a reach probe
against Brouwer's constant-weight tables (snapshot protocol identical to ticket ①, `docs/data/` +
cross-check). GREEN = Table II reproduction; discovery expectations honest-low but **less mined than the
unrestricted family**. Medium project; may split into 2 sessions (build+faithfulness / probe).

## Ticket D2 (task #103) — resolve the (22,10) anomaly

**Kickoff prompt:**
> Resolve the A(22,10) Terwilliger anomaly (our transcription certifies ≤88 exactly; Table I says 87) —
> task #103. Read `docs/results/terwilliger-solve-leg-2026-07-02.md` (anomaly section + resolution paths)
> and `docs/handoff-terwilliger-discovery-2026-07-02.md` (D2).

Recorded facts: exact cert at 88.2463 (P=1e14) and **87 does not certify**; floats stall on both sides;
eq.(25) caps provably can't bridge. Resolution paths from the solve-leg doc: (a) an exact primal-feasible
point beating 88 (would refute our 88 as optimal and point at a transcription gap); (b) formulation deltas
vs Schrijver's program (he may have used extra constraints for that cell); (c) literature cross-check of
the 87 provenance. Outcome either validates Table I (and finds our gap) or is a **documented discrepancy
claim** — the latter needs operator sign-off before any external communication.

## Ticket D3 (task #104) — post-2005 hierarchy scoping (docs only)

**Kickoff prompt:**
> Scope the quadruple-distance (GMS 2012) / Laurent-strengthening hierarchies for the Leibniz producer —
> task #104. Docs only, measure-before-build: formulation sizes, block structures, solver demands vs our
> SDPA-GMP leg, and what `certify_lp`/kernel rendering would need. Read
> `docs/handoff-terwilliger-discovery-2026-07-02.md` (D3).

The modern frontier (where current records come from). Deliverable: a scoping doc + go/no-go
recommendation with measured size estimates — no build.

## Sequencing & standing items

**D1 first** (new ground, reuses the whole banked pipeline) → **D2** (cheap, high information; parallelizable
with D1) → **D3** scoping → operator go/no-go. Standing: F2b external round in flight (brief:
`docs/briefs/terwilliger-f2b-external-brief-2026-07-02.md`; revisit on response); F2c = Observatory tier
(ADR 0046); parked tasks #54/#68 unchanged.

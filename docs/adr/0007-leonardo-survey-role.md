# ADR 0007 — Leonardo's Real Role: Cross-Domain Analogy, not Frontier Survey (D6)

- Status: Accepted
- Date: 2026-06-21
- Related: README organ map (Leonardo = "eyes"), HANDOFF §11 q1, ADR 0001.
  Resolves operator decision D6 with repository access to the live Leonardo system.

## Context

The original organ map *inferred* Leonardo's role from its name: a survey/analogy
front-end exposing `survey_frontier` + `cross_domain_analogies`. With access to the
real repos (`leonardo`, `leonardo-daemon`, `leonardo-forge`, + UAT mirrors), that
inference is **confirmed wrong in part**. Leonardo is a live, claude-daemon-lineage
**autonomous journaling agent**: a heartbeat loop over a multi-mode cognitive
surface, a Forge journal (Studio working folios → Codex settled folios), mind-search
retrieval, and a public reading-room (codexvitruvianus.com). Its folios are
da-Vinci-voice reflections across domains (art, optics, philosophy, …) — **not**
analysis-of-algorithms frontier surveys.

## Decision

Split the `LeonardoAdapter` responsibilities by what Leonardo actually is:

**1. `cross_domain_analogies` → Leonardo (its genuine strength).** Read Leonardo's
**Forge Codex** folios (a git artifact at `LEONARDO_FORGE_PATH`, default
`../leonardo-forge`) and surface a few as cross-domain stepping stones — the "da
Vinci move" of connecting disparate domains to seed conjectures. Coupling is loose:
Leibniz reads the Forge artifact; it does **not** depend on Leonardo's running
daemon. (A mind-search HTTP path, `LEONARDO_SEARCH_URL`, is a possible future
enhancement.)

**2. `survey_frontier` → a curated source (NOT Leonardo).** Frontier edges of
analysis of algorithms come from a curated seed list (`corpus/frontier.json`,
overridable via `LEIBNIZ_FRONTIER_PATH`). Leonardo does not survey this domain, so
pretending it does would be dishonest. A literature/arxiv survey path can replace
the curated list later.

Both behind one adapter (`leibniz.leonardo.LeonardoForgeAdapter`) so the seam stays
a one-file change, per the spec's isolation intent.

## Consequences

- Leibniz gains a real analogy source without a live-daemon dependency or a fragile
  cross-repo import. Tests use fixture folios; the default path points at the real
  Forge for live runs.
- The organ map is corrected: Leonardo is "eyes" for **analogy**, not for frontier
  survey. The README/architecture organ map should note this (follow-up doc edit).
- The curated frontier is a stopgap; its scope/growth is the remaining open piece
  of D6 (a literature feed), tracked for later.

## Non-goals

- Importing Leonardo's daemon internals into Leibniz (fragile coupling).
- Trusting Leonardo's output as anything but *proposal* seeds — they enter the same
  mechanical gates as any conjecture (ADR 0001).

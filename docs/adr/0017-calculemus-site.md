# ADR 0017 — Codex Calculemus presentation site (codexcalculemus.com) (Accepted)

- Status: **Accepted** (implemented 2026-06-21)
- Date: 2026-06-21
- Related: ADR 0008 / R6 (Calculemus reading-room + operator publish tier), the
  sibling [`codex-vitruvianus`](https://github.com/elementalcollision/codex-vitruvianus).
  The site is its own private repo
  [`codex-calculemus`](https://github.com/elementalcollision/codex-calculemus); this
  repo keeps the producer bridge `leibniz/calculemus_site.py` +
  `scripts/export_calculemus.py`. Non-guarded. Roadmap: Tier 4.

## Context

R6 built the `Calculemus` ledger logic (promulgate / publish / colophon) but only
rendered Markdown in-process. The mission needs a real public **reading-room** —
the place a kernel-proven law is shown, proof open, to a human. The project already
has a sibling site, **Codex Vitruvianus** (an Astro static site that renders
Leonardo's forge), whose "Lo Studiolo" design surface is the house style. The
operator asked for the Calculemus equivalent, following that example.

## Decision

Build **Codex Calculemus** as its own private repo
(`elementalcollision/codex-calculemus`) — an Astro 5 static site (Cloudflare Pages),
faithfully mirroring Codex Vitruvianus, that renders the Calculemus ledger as a
browsable codex. The producer (Leibniz) and renderer (the site repo) are separate,
exactly as the daemon and forge are for Vitruvianus.

1. **Same stack + design system.** Astro static output, the Lo Studiolo tokens
   (vellum/ink themes, Instrument Serif/Sans + JetBrains Mono), near-zero JS (theme
   toggle + diagram lightbox). Carried over verbatim, re-themed to *Codex
   Calculemus* / *Calculemus*.
2. **Content = the published ledger.** A law is the Propositio triad
   (`Enuntiatio` / `Expressio` / `Demonstratio`) + the kernel certificate. Pages:
   frontispiece, **Le Leggi** (laws index + reader), **Il Lavoro** (cycle work-log),
   **Colophon** (publish gate + provenance), **L'Ingegno** (architecture + system
   map of the trust boundary).
3. **Public ledger, committed in the site repo.** Unlike Vitruvianus's *private*
   forge (pulled with a token at build), the *published* Calculemus ledger is meant
   to be read, so it is committed in the site repo at `ledger/calculemus.json` — the
   build needs no secret. The site's `scripts/sync-ledger.mjs` normalizes it into
   Astro content collections. `leibniz/calculemus_site.py` is the forward path: it
   serializes a live `Calculemus` (published laws + held-back colophon) to that
   ledger, which the operator commits to the site repo.
4. **Honesty by construction.** Until the discovery frontier publishes novel
   theorems, the ledger ships **specimens** — well-known results, **genuinely
   kernel-checked** through the Lean REPL backend (ADR 0011), marked `specimen:
   true`, never counted as discoveries. `export_calculemus.py --check` re-verifies
   every claimed `Q.E.D.` against the real kernel, so the ledger cannot publish a
   certificate the kernel rejects.

## Options considered

- Standalone repo (like Vitruvianus) vs. `site/` subtree in the Leibniz repo:
  **standalone private repo** (`codex-calculemus`) — the faithful mirror of the
  Vitruvianus↔forge split, keeps the public-facing renderer separate from the
  private daemon, and lets the site build with no Leibniz dependency. (Built first
  as a subtree, then split out.)
- Generate the site from Python vs. Astro: **Astro**, to match the sibling exactly
  and reuse its design system; Python only bridges the ledger.

## Consequences

- Leibniz has a real public face at codexcalculemus.com, in visual continuity with
  Codex Vitruvianus. `npm run build` is self-contained (9 pages from the committed
  ledger); a published-law push rebuilds via the deploy-hook workflow.
- Trust unaffected: the site and `calculemus_site.py` are **read-only** over the
  ledger — no `kernel_verified`, no `promulgated`, no edge minted (the boundary
  guards and `tests/test_invariants.py` stay byte-identical). The publish gate
  ("promotion ≠ publication", operator-only) is preserved and surfaced in the
  colophon.

## Open questions

- The ledger currently carries specimens + an illustrative cycle; real content
  arrives when the Tier 1 discovery frontier promulgates and the operator publishes.
- A live deploy needs the operator's Cloudflare/DNS steps (DEPLOY.md) and the
  `notify-site.yml` trigger added to the Leibniz repo (offered as a PR).

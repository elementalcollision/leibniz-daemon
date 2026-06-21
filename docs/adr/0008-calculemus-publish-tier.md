# ADR 0008 — Calculemus: the Reading-Room and the Operator Publish Tier (R6)

- Status: Accepted
- Date: 2026-06-21
- Related: capability-ladder R6; Newton ADR 0012 (mutation queue / operator tier);
  ADR 0001 (Q.E.D. iff kernel_verified).

## Context

The daemon promulgates kernel-checked laws autonomously. But a public ledger of
"proven" results is permanent and authoritative, so **what leaves the building must
be a deliberate human act**, separate from the daemon's promotion. We need a public
reading-room (*Calculemus*) and a gate between the Codex (promulgated, internal) and
publication (public).

## Decision

**1. Promotion ≠ publication.** Two stages, two actors:
- The daemon **promulgates** a law to the **Codex** (`Calculemus.promulgate`) — and
  only if it carries a real kernel `Q.E.D.` (`promulgated ∧ kernel_verified ∧
  qed == "Q.E.D."`). This reads the certificate; it never sets it.
- A human **publishes** a Codex law to the public ledger (`Calculemus.publish(pid,
  operator_approved=True)`). Without explicit operator approval, publish refuses.
  The daemon never supplies approval — publication is an out-of-band human mutation
  (mirrors Newton ADR 0012's operator tier).

**2. The reading-room renders the full triad.** `render_propositio` renders
Enuntiatio (claim + falsifiable claim) / Expressio (Lean statement) / Demonstratio
(tactic script + `Q.E.D.` + `kernel_verified`) — the proof open to inspection.
`render_public` shows only operator-published laws.

**3. A colophon of what is held back.** `colophon()` lists promulgated-but-unpublished
laws and why (awaiting operator publication) — provenance/honesty about what exists
versus what is shown.

## Consequences

- The R6 exit test holds: a law appears in *Calculemus*, proof open, **only after**
  an explicit operator publish; a promulgated-but-unpublished law is in the Codex
  and the colophon, not in the public render.
- This module is read-only over the ledger; it cannot affect the trust boundary.
  Rendering a non-kernel-verified candidate is impossible (`promulgate` refuses it).
- Rendering target is Markdown now; an Astro/HTML site (à la codexvitruvianus) is a
  presentation-layer follow-up, not a trust concern.

## Non-goals

- Auto-publishing. The daemon promulgates; only a human publishes.
- Re-deciding anything at render time — Calculemus reports recorded evidence.

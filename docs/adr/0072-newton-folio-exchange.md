# ADR 0072 — Phase δ: the Newton folio exchange (outbound)

- Status: accepted
- Date: 2026-07-23
- Depends on: ADR 0068/0069 (the heartbeat that carries the exchange), ADR 0033 (publication
  remains the operator act), ADR 0050 (provenance vocabulary)

## Context — and the repoint

The autonomy plan's Phase δ was drafted as a Leibniz↔**Leonardo** folio exchange. The operator
repointed it (2026-07-23): share with **Newton** instead — Newton is *classically designed to
evaluate models* (falsifiable claims + executable verification + validation gates + probation),
where Leonardo organically discovers its own concepts. Leibniz's laws are exactly the kind of
artifact Newton's machinery can independently evaluate: a formal claim, an executable bounded
check, and a kernel proof.

Newton's side of the fence (read, not modified): a filesystem-seam philosophy (peer registry at
`~/.newton/peers/`), a Propositio format with YAML frontmatter (`falsifiable_claim`, `verified`,
`proof_status`, …), and an A2A federation stack (their ADR 0016) whose N4.4 WRITE capabilities
include `check_proof`.

## Decision

`leibniz/newton_exchange.py` — a deterministic, stdlib-only, LLM-free exporter. Each
promulgated, kernel-verified law becomes one Newton-shaped folio in a NEUTRAL exchange dir
(`LEIBNIZ_NEWTON_EXCHANGE_DIR`, default `~/.newton/exchange/leibniz/` — beside Newton's own
seams, inside neither repo), deduplicated by a manifest:

1. **Frontmatter in Newton's vocabulary**, conservatively filled — and **`verified: false`
   always**: Newton's stamp is Newton's to make. We ship evidence, never a pre-made verdict.
   A `leibniz:` provenance block carries pid, kernel identity, `kernel_verified: true`,
   promulgation time, and the trust charter line.
2. **Enuntiatio** (the claim prose) and **Expressio** — the full Lean statement *and proof*,
   ready for Newton's future `check_proof` federation capability.
3. **Auditio mechanica** — a self-contained Python procedure re-checking the claim over the
   `[0, 64]` box, generated from the claim's own DSL text (which is already Python). Newton can
   run it under its own sandbox discipline without trusting us.
4. **The tripwire**: every folio's audit is *executed before export* (bound 16). A law whose
   bounded audit fails would mean the rendered claim and the kernel-proved theorem disagree —
   that is a faithfulness alarm, and the folio is **refused**, never shipped. (First live
   export: 11 exported, 10 refused — all ten benign pre-DSL dev-era rows lacking
   `claim_property`; zero audit failures.)

Heartbeat wiring mirrors the ADR 0069 feed: env-gated (`LEIBNIZ_NEWTON_EXCHANGE=1`), runs after
cycles, journals `{"exported", "refused", "total"}`, and any failure degrades to a journal note —
never an abort, never an alarm.

## Trust posture

Outbound and report-only. Exported folios are *held* laws being shown to a sibling daemon on the
operator's own machine — not publication (codexcalculemus.com remains gated by ADR 0033). Nothing
Newton says feeds any Leibniz gate. Three later increments, each needing its own decision:

- **δ2 (Newton's repo)**: Newton-side ingestion — their gates evaluating `federated_leibniz`
  folios under their own probation discipline.
- **δ3**: A2A registration (Leibniz as a peer under Newton's ADR 0016 alignment ceremony), so
  the exchange becomes a handshake rather than a drop directory.
- **δ4**: verdict fold-back — Newton's evaluations attached to Leibniz laws as report-only
  external attestation (the cross-kernel pattern of ADR 0067, at daemon granularity).

## Consequences

- Every future unattended promulgation is automatically visible to Newton the next morning,
  with everything needed for independent evaluation.
- The dev-era rows without DSL contracts stay un-exported (honest: no formal claim text, no
  audit possible); they predate the current pipeline and remain in the ledger only.
- The audit tripwire doubles as a standing consistency check between the DSL and the kernel
  statements of every law that passes through.

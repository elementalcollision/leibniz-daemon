# Publishing the MCR audit to Codex Calculemus (Il Lavoro / `/cycles`)

**For:** the operator. **What:** record the MCR-whitepaper audit as a work-log **cycle** at
[codexcalculemus.com/cycles](https://codexcalculemus.com/cycles/). **Why a cycle, not a law:** the audit
adjudicates a third party's claims and reports verdicts — it is *what the daemon did*, not a theorem the
daemon proved. It belongs in *Il Lavoro* (the work-log), never in *Le Leggi* (the laws). Accordingly it
carries **no `kernel_verified`, mints no edge, and promulgates nothing**; the ADR 0033 publish guard governs
*laws* and does not apply here. This is fully inside the read-only contract of `leibniz/calculemus_site.py`.

## The producer (already in this repo)

- `leibniz/calculemus_site.py :: cycle_payload(...)` — the typed producer for a `/cycles` entry (mirrors
  `law_payload`). Fills the ADR 0017 gap ("the ledger currently carries … an illustrative cycle"): cycles now
  have a real, tested producer.
- `scripts/export_mcr_cycle.py` — builds the MCR cycle and emits the ready-to-pipeline fragment.
- **`docs/audits/mcr_cycle_entry.json`** — the emitted fragment (the path to hand the publication agent).
  Regenerate with `python scripts/export_mcr_cycle.py -o docs/audits/mcr_cycle_entry.json`
  (add `--generated-at <ISO>` for a reproducible provenance stamp).
- Test: `tests/test_calculemus_site_r0017.py` locks the cycle shape, the eight verdicts, and the fragment
  contract (CI-safe).

## Fragment shape (self-describing, for the publication agent)

```
{ "meta":  { "generated_at", "producer", "target", "merge" },   // provenance — NOT ledger content
  "cycles": [ { …the one work-log entry… } ] }                  // the payload to merge
```

`meta.target` names the destination (`elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]`)
and `meta.merge` states the rule: **append each object in `cycles` to the site ledger's top-level `cycles`
array; do not overwrite the ledger's own `generated_at` / `laws` / `held_back`.** A pipeline consumes `cycles`
and may read `meta` for provenance/ordering; it must not write the `meta` block into the ledger.

## Deploy (operator steps, in the site repo `elementalcollision/codex-calculemus`)

1. Open `ledger/calculemus.json`. Append the single object from `docs/audits/mcr_cycle_entry.json`'s
   `cycles[0]` into the ledger's top-level **`cycles`** array (keep the illustrative Cycle 1 or drop it — your
   call; real content supersedes it per ADR 0017's open question).
2. **Reconcile keys with `scripts/sync-ledger.mjs`.** The core fields — `cycle`, `date`, `domain`, `kind`,
   `summary` — map to the badge already rendered for Cycle 1 (date · domain · classification · summary). The
   richer fields `findings` / `artifacts` / `title` / `links` / `laws` are additive and degrade gracefully;
   surface them in the `/cycles` view if/when `sync-ledger.mjs` reads them. If a key name differs from what the
   sync script expects, rename in the ledger (the site repo owns that contract) — the producer just proposes a
   clean shape.
3. `cycle` is set to `2` (Cycle 1 is the illustrative one). Renumber to the next integer if your ledger already
   holds more cycles. `date` is ISO (`2026-07-03`); the renderer formats it ("3 July 2026").
4. Build/deploy as usual (`npm run build`; the deploy-hook workflow). Optionally run
   `python scripts/export_calculemus.py --check ledger/calculemus.json` first — it re-verifies **laws'** Q.E.D.
   against the Lean kernel and ignores cycles, so it will pass unchanged.

## Honesty / hygiene (kept by construction)

- **No internal paths on the public site.** The cycle names its artifacts (`mcr_p4_not_derivable.lean`,
  `mcr_audit_artifacts.py`) and states each checker + result, but carries no repo paths or tooling internals —
  unlike the internal report `mcr-whitepaper-audit-2026-07-03.md`, which must not be posted verbatim.
- **The two lanes stay separate.** This work-log entry is the *public record that the audit happened*. The
  *fileable* artifact for the MCR author lives elsewhere: `mcr-external-review-for-source-repo.md` (+ the
  handoff `mcr-audit-handoff-to-chimera.md`). Chimera files that against `Player-Kheltz/MCR`; the Codex cycle
  does not replace or link to it.
- **Every verdict remains backed by a re-runnable artifact.** The cycle reports the verdicts; the proof of each
  is the Z3/Lean artifact, unchanged.

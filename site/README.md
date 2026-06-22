# Codex Calculemus

A public, illuminated reading-room for **Leibniz's** kernel-proven ledger — it
renders the *Calculemus* ledger (each law as its `Enuntiatio` / `Expressio` /
`Demonstratio` triad plus the kernel certificate) as a browsable book, themed in
faithful continuity with **Lo Studiolo**, the design surface it shares with its
sibling [Codex Vitruvianus](https://codexvitruvianus.com).

→ **[codexcalculemus.com](https://codexcalculemus.com)** · hosted on Cloudflare Pages

## How it works

```
Leibniz daemon ──promulgate (kernel Q.E.D.)──▶ Codex
        operator publish ──▶ scripts/export_calculemus.py ──▶ site/ledger/calculemus.json (committed)
                                  │  push to site/ledger/** (or this repo)
                                  └─ GitHub Action ─ POST ▶ Cloudflare Pages deploy hook
                                                   │
                            CF Pages build ◀───────┘   (npm run build:
                                                         sync-ledger.mjs reads the
                                                         ledger, astro builds the book)
                                  └─▶ codexcalculemus.com live in ~1–2 min
```

- **The ledger is the source of truth, and it is public.** Unlike the Vitruvianus
  forge, the *published* Calculemus ledger is meant to be read, so it is committed
  here as `ledger/calculemus.json` — no private token needed to build.
  `scripts/sync-ledger.mjs` normalizes it into `src/content/{laws,cycles}/` at build
  time. Only operator-published, kernel-verified laws appear; promulgated-but-held-back
  laws are surfaced in `/colophon` only. See the live colophon for provenance.
- **The one rule:** an LLM may *propose*; only the Lean kernel and Z3 may *decide*.
  Every law carries a real, machine-checked `Q.E.D.` — see `/architecture`.
- **Stack:** [Astro](https://astro.build) static output + the Lo Studiolo design
  tokens. Near-zero JS (theme toggle + diagram lightbox only).

## Specimens

Until the daemon's discovery frontier publishes novel theorems, the ledger ships
with a few entries marked `specimen: true` — well-known results, **genuinely
kernel-checked** (verified through the project's Lean REPL backend), included only
to show the format of a published law. A specimen is honest about being one and is
never counted as a discovery.

## Local development

```bash
npm install
npm run dev      # runs sync-ledger.mjs (reads ledger/calculemus.json), then astro dev
npm run build    # sync + static build into dist/
```

To iterate on the UI without re-syncing, run `npx astro dev` once `src/content/` is
populated.

## Deployment

See **[DEPLOY.md](./DEPLOY.md)** for the Cloudflare runbook (domain, build, deploy
hook, custom domain). The Leibniz-side trigger lives in
[`deploy/leibniz-workflow/notify-site.yml`](./deploy/leibniz-workflow/notify-site.yml).

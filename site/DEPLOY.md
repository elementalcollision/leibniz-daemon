# Deploying Codex Calculemus to Cloudflare Pages

End-to-end runbook. Steps marked **[you]** require your accounts/credentials and
cannot be automated. Estimated time: ~20–30 minutes, most of it DNS propagation.

This site is simpler to deploy than Codex Vitruvianus: the published ledger is
**public and committed** (`ledger/calculemus.json`), so the build needs **no
forge token** — `npm run build` just reads the committed ledger and renders it.

Outline:
1. Point `codexcalculemus.com` at Cloudflare
2. Create the GitHub repo (or deploy this `site/` subtree) and push
3. Create the Cloudflare Pages project
4. Create the deploy hook and wire auto-updates
5. Attach the custom domain
6. Verify

---

## 1. Point the domain at Cloudflare — **[you]**

Register `codexcalculemus.com` and add it to Cloudflare (**Add a site → Free**),
then set the registrar's nameservers to the two Cloudflare assigns. Wait for the
zone to go **Active**. (Same flow as Vitruvianus; apex custom domain becomes one
click.)

## 2. Repo / source — **[you, or ask me]**

Two options:

- **A — standalone repo (mirrors Vitruvianus).** Lift this `site/` subtree into its
  own repo and point Cloudflare at it:
  ```bash
  # from a copy of site/
  gh repo create elementalcollision/codex-calculemus --private --source . --remote origin --push
  ```
- **B — build from the Leibniz monorepo.** Point Cloudflare Pages at the `leibniz`
  repo with **Root directory = `site`**. No second repo needed.

> I can create the standalone repo on request — I have access — but I will **not**
> push a new remote without your go-ahead.

## 3. Cloudflare Pages project — **[you]**

1. Cloudflare → **Workers & Pages → Create → Pages → Connect to Git** → select the repo.
2. **Build settings:**
   | Field | Value |
   |---|---|
   | Framework preset | Astro |
   | Build command | `npm run build` |
   | Build output directory | `dist` |
   | Root directory | *(blank for option A; `site` for option B)* |
3. **Environment variables** (Production **and** Preview):
   | Name | Value |
   |---|---|
   | `NODE_VERSION` | `22` |
   No token is required — the ledger is committed.
4. **Save and Deploy.** The first build runs `sync-ledger.mjs` then `astro build`.
   You get a `*.pages.dev` URL — open it to confirm the frontispiece renders.

## 4. Deploy hook + auto-update — **[you + me]**

Rebuild whenever a new law is published (the ledger changes).

1. Pages project → **Settings → Builds → Add deploy hook** (name `ledger-push`,
   branch `main`). Copy the URL.
2. Add it as secret `CF_DEPLOY_HOOK`:
   ```bash
   gh secret set CF_DEPLOY_HOOK --repo elementalcollision/leibniz            # primary trigger
   gh secret set CF_DEPLOY_HOOK --repo elementalcollision/codex-calculemus   # daily backstop (option A)
   ```
3. Install the Leibniz-side trigger — copy
   [`deploy/leibniz-workflow/notify-site.yml`](./deploy/leibniz-workflow/notify-site.yml)
   into the Leibniz repo at `.github/workflows/notify-site.yml`. It fires on a push
   that touches `site/ledger/**`.
   > I'll add this **via a pull request** for you to review rather than committing to
   > `main` directly.

The site repo's `daily-rebuild.yml` is a once-a-day safety net.

## 5. Custom domain — **[you]**

Pages project → **Custom domains → Set up** → `codexcalculemus.com` (add `www` too).
Cloudflare issues SSL automatically when DNS is on Cloudflare.

## 6. Verify

- [ ] `https://codexcalculemus.com` shows the frontispiece with the latest law.
- [ ] A law opens with its claim, formal statement, proof, and `Q.E.D.` certificate.
- [ ] `/architecture` renders the system map; the lightbox enlarges it.
- [ ] Day/night toggle persists across navigation.
- [ ] `/colophon` shows current counts, the held-back note, and the specimen note.

### Troubleshooting
- **Build fails at sync:** `ledger/calculemus.json` is missing or malformed — the
  build log's first lines show the ledger path.
- **A new law isn't appearing:** confirm `export_calculemus.py` wrote the ledger and
  the change was pushed; check the Leibniz `notify-site.yml` Action and `CF_DEPLOY_HOOK`.
- **Fonts look wrong:** ensure the build copied `public/fonts/*` (they ship in the
  repo, not from a CDN).

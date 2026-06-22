// @ts-check
import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

// Codex Calculemus — static reading-room for Leibniz's kernel-proven ledger.
// Pure static output → deploys to Cloudflare Pages as plain files (no adapter).
export default defineConfig({
  site: "https://codexcalculemus.com",
  output: "static",
  trailingSlash: "ignore",
  build: { format: "directory" },
  devToolbar: { enabled: false },
  integrations: [sitemap()],
});

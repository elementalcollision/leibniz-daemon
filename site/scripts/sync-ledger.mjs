#!/usr/bin/env node
/**
 * sync-ledger.mjs — normalize the Calculemus ledger into Astro content
 * collections. The analog of Codex Vitruvianus's sync-forge.mjs, but the source
 * is Leibniz's own published ledger (the published ledger is meant to be public),
 * so this reads a committed JSON file rather than pulling a private repo.
 *
 * Source : ledger/calculemus.json   (override with LEIBNIZ_LEDGER=/path/to.json)
 * Output : src/content/{laws,cycles}/*.json  +  src/content/sync-report.json
 *
 * The ledger is produced on the Leibniz side by scripts/export_calculemus.py
 * (Calculemus.published → JSON). Only operator-published, kernel-verified laws
 * appear; promulgated-but-held-back laws are surfaced in the colophon only.
 */
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const CONTENT = join(ROOT, "src", "content");
const LEDGER = process.env.LEIBNIZ_LEDGER || join(ROOT, "ledger", "calculemus.json");

function romanize(num) {
  const map = [[1000,"M"],[900,"CM"],[500,"D"],[400,"CD"],[100,"C"],[90,"XC"],[50,"L"],[40,"XL"],[10,"X"],[9,"IX"],[5,"V"],[4,"IV"],[1,"I"]];
  let n = num, out = "";
  for (const [v, s] of map) while (n >= v) { out += s; n -= v; }
  return out || "0";
}

function slug(s) {
  return String(s).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "law";
}

function freshDir(p) {
  if (existsSync(p)) rmSync(p, { recursive: true, force: true });
  mkdirSync(p, { recursive: true });
}

function main() {
  if (!existsSync(LEDGER)) {
    console.error(`✗ ledger not found: ${LEDGER}`);
    process.exit(1);
  }
  const ledger = JSON.parse(readFileSync(LEDGER, "utf8"));
  mkdirSync(CONTENT, { recursive: true });

  // --- laws (only kernel-verified, operator-published) ---------------------
  const lawsDir = join(CONTENT, "laws");
  freshDir(lawsDir);
  const laws = Array.isArray(ledger.laws) ? ledger.laws : [];
  let specimens = 0;
  for (const law of laws) {
    const id = slug(law.id || law.theorem_src || law.statement);
    if (law.specimen) specimens++;
    writeFileSync(join(lawsDir, `${id}.json`), JSON.stringify({
      pid: law.pid ?? "",
      statement: law.statement ?? "",
      claim_type: law.claim_type ?? "",
      falsifiable_claim: law.falsifiable_claim ?? "",
      domain: law.domain ?? "",
      theorem_src: law.theorem_src ?? "",
      proof_src: law.proof_src ?? "",
      imports: Array.isArray(law.imports) ? law.imports : [],
      qed: law.qed ?? "Q.E.I.",
      kernel_verified: !!law.kernel_verified,
      consensus: Number(law.consensus ?? 0),
      published_at: law.published_at ?? "",
      specimen: !!law.specimen,
    }, null, 2));
  }

  // --- cycles (the work log) ------------------------------------------------
  const cyclesDir = join(CONTENT, "cycles");
  freshDir(cyclesDir);
  const cycles = Array.isArray(ledger.cycles) ? ledger.cycles : [];
  for (const c of cycles) {
    const n = Number(c.cycle ?? 0);
    writeFileSync(join(cyclesDir, `cycle_${String(n).padStart(6, "0")}.json`), JSON.stringify({
      cycle: n,
      roman: romanize(n),
      created_at: c.created_at ?? "",
      domain: c.domain ?? "",
      seeds: Number(c.seeds ?? 0),
      conjectured: Number(c.conjectured ?? 0),
      reached_proof: Number(c.reached_proof ?? 0),
      promulgated: Number(c.promulgated ?? 0),
      by_reason: c.by_reason && typeof c.by_reason === "object" ? c.by_reason : {},
      summary: c.summary ?? "",
    }, null, 2));
  }

  // --- colophon report ------------------------------------------------------
  writeFileSync(join(CONTENT, "sync-report.json"), JSON.stringify({
    generated_at: ledger.generated_at ?? "",
    laws: laws.length,
    specimens,
    cycles: cycles.length,
    held_back: Array.isArray(ledger.held_back) ? ledger.held_back : [],
  }, null, 2));

  console.log(`✓ laws=${laws.length} (specimens ${specimens})  cycles=${cycles.length}  held_back=${(ledger.held_back || []).length}`);
}

main();

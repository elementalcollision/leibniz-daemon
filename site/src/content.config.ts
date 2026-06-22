import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

// A published law — the unit of the Calculemus ledger. Mirrors the Propositio
// triad (Enuntiatio / Expressio / Demonstratio) plus the kernel certificate.
// Written from ledger/calculemus.json by scripts/sync-ledger.mjs.
const laws = defineCollection({
  loader: glob({ pattern: "**/*.json", base: "./src/content/laws" }),
  schema: z.object({
    statement: z.string(),                 // Enuntiatio — the human-readable claim
    claim_type: z.string().default(""),    // complexity_bound | correctness | …
    falsifiable_claim: z.string().default(""),
    domain: z.string().default(""),
    theorem_src: z.string().default(""),   // Expressio — the formal Lean statement
    proof_src: z.string().default(""),     // Demonstratio — the kernel-checked tactic script
    imports: z.array(z.string()).default([]),
    qed: z.string().default("Q.E.I."),
    kernel_verified: z.boolean().default(false),
    consensus: z.number().default(0),      // N+1 independent kernel-verified proofs
    published_at: z.string().default(""),
    specimen: z.boolean().default(false),  // illustrative format demo, not a daemon discovery
  }),
});

// A circadian cycle report — the daemon's work log (CycleReport).
const cycles = defineCollection({
  loader: glob({ pattern: "**/*.json", base: "./src/content/cycles" }),
  schema: z.object({
    cycle: z.number(),
    roman: z.string().default(""),
    created_at: z.string().default(""),
    domain: z.string().default(""),
    seeds: z.number().default(0),
    conjectured: z.number().default(0),
    reached_proof: z.number().default(0),
    promulgated: z.number().default(0),
    by_reason: z.record(z.number()).default({}),
    summary: z.string().default(""),
    illustrative: z.boolean().default(false),  // a format demo, not real daemon output
  }),
});

export const collections = { laws, cycles };

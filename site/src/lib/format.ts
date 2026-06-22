// Formatting + deterministic marginalia for the Calculemus reading-room.
// Where Codex Vitruvianus uses Leonardo's drawings, the geometer's codex uses
// austere SVG devices (drawn in Figures.astro), assigned deterministically from
// an entry key so a given page always shows the same device across rebuilds.

const FIGURES: Array<[string, string]> = [
  ["lemniscate", "Lemniscate — the sign of the infinite, after Bernoulli"],
  ["integral", "The integral — Leibniz's elongated ſumma"],
  ["binary", "Dyadic arithmetic — the binary table"],
  ["sector", "A circular sector — area by exhaustion"],
  ["lattice", "A divisibility lattice"],
  ["tree", "A decision tree — leaves bound by depth"],
];

function hash(key: string): number {
  let h = 2166136261;
  for (let i = 0; i < key.length; i++) {
    h ^= key.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

export function figureFor(key: string): { id: string; caption: string } {
  const [id, caption] = FIGURES[hash(key) % FIGURES.length];
  return { id, caption };
}

export function formatDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", {
    day: "numeric", month: "long", year: "numeric", timeZone: "UTC",
  });
}

export function formatStamp(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().replace("T", " ").slice(0, 16) + " UTC";
}

export function titleCase(s: string): string {
  return s.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// Claim-type → display label. Mirrors leibniz.types.ClaimType.
const CLAIM_LABELS: Record<string, string> = {
  complexity_bound: "Complexity bound",
  correctness: "Correctness over a domain",
  optimality: "Optimality",
  invariant: "Invariant",
  existence: "Existence",
  structural: "Structural",
  open_form: "Open form",
};

export function claimLabel(ct: string): string {
  return CLAIM_LABELS[ct] || titleCase(ct || "claim");
}

export function romanize(num: number): string {
  const map: Array<[number, string]> = [
    [1000, "M"], [900, "CM"], [500, "D"], [400, "CD"], [100, "C"], [90, "XC"],
    [50, "L"], [40, "XL"], [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"],
  ];
  let n = num, out = "";
  for (const [v, s] of map) while (n >= v) { out += s; n -= v; }
  return out || "0";
}

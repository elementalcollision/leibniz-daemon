"""Build the known-results corpus (R3).

Curated known results are listed here as elaboratable Lean statements. This script
computes each statement's *structural* hash via the Lean container (the same
elaborator-canonical normalizer the pipeline uses, R1c) and writes
``corpus/known_results.json``. Querying the corpus at runtime then needs no Lean —
it is a hash/signature comparison (see ``leibniz.corpus``).

Run (needs the Lean image):  python scripts/build_corpus.py

Re-run whenever you add a curated result or bump the Lean toolchain (the structural
hash is toolchain-specific). The curated set is intentionally small to start; D4
(source/scope/licensing) governs how it grows. Entries are re-stated in our own
Lean — no copyrighted prose is redistributed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.backends.lean_cli import LeanCliBackend, available  # noqa: E402
from leibniz.propositio import Expressio  # noqa: E402

# name, claim_type, subject, relation, theorem_src, imports
CURATED = [
    (
        "comparison_sort_lower_bound",
        "complexity_bound",
        "comparison_sort",
        "lower_bound",
        # Decision-tree core of the Omega(n log n) comparison-sort bound: a sorter is
        # a comparison tree; sorting n items needs n! distinct leaves, and a binary
        # tree of height h has at most 2^h leaves, so h >= log2(n!).
        "theorem comparison_sort_lower_bound : "
        "forall n h : Nat, 2 ^ h >= Nat.factorial n -> h >= Nat.log 2 (Nat.factorial n)",
        ("Mathlib.Tactic",),
    ),
    (
        "additive_identity",
        "structural",
        "nat_add",
        "identity",
        "theorem additive_identity : forall n : Nat, n + 0 = n",
        ("Mathlib.Tactic",),
    ),
    (
        "mul_comm_nat",
        "structural",
        "nat_mul",
        "commutativity",
        "theorem mul_comm_nat : forall a b : Nat, a * b = b * a",
        ("Mathlib.Tactic",),
    ),
]


def main() -> int:
    if not available():
        print("Lean image not available; cannot build corpus.", file=sys.stderr)
        return 1
    backend = LeanCliBackend(persistent=True)
    entries = []
    try:
        for name, ctype, subject, relation, src, imports in CURATED:
            expr = Expressio(theorem_src=src, imports=imports)
            h = backend.normalize_statement(expr)
            if h is None:
                print(f"WARNING: {name} did not elaborate; skipping", file=sys.stderr)
                continue
            entries.append({
                "name": name,
                "claim_type": ctype,
                "subject": subject,
                "relation": relation,
                "theorem_src": src,
                "imports": list(imports),
                "formal_hash": h,
            })
            print(f"  {name}: {h}")
    finally:
        backend.close()

    out = Path(__file__).resolve().parent.parent / "corpus" / "known_results.json"
    out.write_text(json.dumps(entries, indent=2) + "\n")
    print(f"wrote {len(entries)} entries -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

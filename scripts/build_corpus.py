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
    # --- D4 expansion: canonical results, re-stated in our own Lean -----------
    # These are the textbook facts a conjecturer in arithmetic / analysis-of-
    # algorithms most often re-discovers; seeding their structural hashes is what
    # lets the novelty gate say KNOWN instead of "looks novel". Each only needs to
    # *elaborate* (build appends `:= sorry` for the hash); all are true.
    # Nat additive/multiplicative structure
    ("add_comm_nat", "structural", "nat_add", "commutativity",
     "theorem add_comm_nat : forall a b : Nat, a + b = b + a", ("Mathlib.Tactic",)),
    ("add_assoc_nat", "structural", "nat_add", "associativity",
     "theorem add_assoc_nat : forall a b c : Nat, a + b + c = a + (b + c)", ("Mathlib.Tactic",)),
    ("zero_add_nat", "structural", "nat_add", "identity",
     "theorem zero_add_nat : forall n : Nat, 0 + n = n", ("Mathlib.Tactic",)),
    ("mul_assoc_nat", "structural", "nat_mul", "associativity",
     "theorem mul_assoc_nat : forall a b c : Nat, a * b * c = a * (b * c)", ("Mathlib.Tactic",)),
    ("mul_one_nat", "structural", "nat_mul", "identity",
     "theorem mul_one_nat : forall n : Nat, n * 1 = n", ("Mathlib.Tactic",)),
    ("one_mul_nat", "structural", "nat_mul", "identity",
     "theorem one_mul_nat : forall n : Nat, 1 * n = n", ("Mathlib.Tactic",)),
    ("mul_zero_nat", "structural", "nat_mul", "absorption",
     "theorem mul_zero_nat : forall n : Nat, n * 0 = 0", ("Mathlib.Tactic",)),
    ("zero_mul_nat", "structural", "nat_mul", "absorption",
     "theorem zero_mul_nat : forall n : Nat, 0 * n = 0", ("Mathlib.Tactic",)),
    ("left_distrib_nat", "structural", "nat_arith", "distributivity",
     "theorem left_distrib_nat : forall a b c : Nat, a * (b + c) = a * b + a * c", ("Mathlib.Tactic",)),
    ("right_distrib_nat", "structural", "nat_arith", "distributivity",
     "theorem right_distrib_nat : forall a b c : Nat, (a + b) * c = a * c + b * c", ("Mathlib.Tactic",)),
    ("two_mul_nat", "structural", "nat_mul", "doubling",
     "theorem two_mul_nat : forall n : Nat, 2 * n = n + n", ("Mathlib.Tactic",)),
    ("pow_zero_nat", "structural", "nat_pow", "identity",
     "theorem pow_zero_nat : forall a : Nat, a ^ 0 = 1", ("Mathlib.Tactic",)),
    ("pow_succ_nat", "structural", "nat_pow", "recurrence",
     "theorem pow_succ_nat : forall a n : Nat, a ^ (n + 1) = a ^ n * a", ("Mathlib.Tactic",)),
    # Int structure
    ("add_comm_int", "structural", "int_add", "commutativity",
     "theorem add_comm_int : forall a b : Int, a + b = b + a", ("Mathlib.Tactic",)),
    ("mul_comm_int", "structural", "int_mul", "commutativity",
     "theorem mul_comm_int : forall a b : Int, a * b = b * a", ("Mathlib.Tactic",)),
    ("neg_neg_int", "structural", "int_neg", "involution",
     "theorem neg_neg_int : forall a : Int, -(-a) = a", ("Mathlib.Tactic",)),
    ("add_left_neg_int", "structural", "int_add", "inverse",
     "theorem add_left_neg_int : forall a : Int, -a + a = 0", ("Mathlib.Tactic",)),
    # Order facts over a domain
    ("nat_le_refl", "correctness", "nat_order", "reflexivity",
     "theorem nat_le_refl : forall n : Nat, n <= n", ("Mathlib.Tactic",)),
    ("nat_zero_le", "correctness", "nat_order", "lower_bound",
     "theorem nat_zero_le : forall n : Nat, 0 <= n", ("Mathlib.Tactic",)),
    ("nat_lt_succ_self", "correctness", "nat_order", "strict_increase",
     "theorem nat_lt_succ_self : forall n : Nat, n < n + 1", ("Mathlib.Tactic",)),
    ("nat_le_add_right", "correctness", "nat_order", "monotonicity",
     "theorem nat_le_add_right : forall a b : Nat, a <= a + b", ("Mathlib.Tactic",)),
    ("nat_succ_pos", "correctness", "nat_order", "positivity",
     "theorem nat_succ_pos : forall n : Nat, 0 < n + 1", ("Mathlib.Tactic",)),
    ("nat_add_le_add_left", "correctness", "nat_order", "monotonicity",
     "theorem nat_add_le_add_left : forall a b c : Nat, b <= c -> a + b <= a + c", ("Mathlib.Tactic",)),
    # Invariants / parity
    ("two_mul_mod_two", "invariant", "nat_parity", "preservation",
     "theorem two_mul_mod_two : forall n : Nat, (2 * n) % 2 = 0", ("Mathlib.Tactic",)),
    ("add_self_mod_two", "invariant", "nat_parity", "preservation",
     "theorem add_self_mod_two : forall n : Nat, (n + n) % 2 = 0", ("Mathlib.Tactic",)),
    ("mod_two_lt", "invariant", "nat_parity", "range",
     "theorem mod_two_lt : forall n : Nat, n % 2 < 2", ("Mathlib.Tactic",)),
    # Growth / complexity-flavoured bounds
    ("two_pow_pos", "complexity_bound", "exponential", "positivity",
     "theorem two_pow_pos : forall n : Nat, 0 < 2 ^ n", ("Mathlib.Tactic",)),
    ("factorial_pos", "complexity_bound", "factorial", "positivity",
     "theorem factorial_pos : forall n : Nat, 0 < Nat.factorial n", ("Mathlib.Tactic",)),
    ("nat_log_le_self", "complexity_bound", "logarithm", "upper_bound",
     "theorem nat_log_le_self : forall n : Nat, Nat.log 2 n <= n", ("Mathlib.Tactic",)),
    ("self_le_two_pow", "complexity_bound", "exponential", "lower_bound",
     "theorem self_le_two_pow : forall n : Nat, n < 2 ^ n", ("Mathlib.Tactic",)),
    # Existence / construction
    ("exists_succ", "existence", "nat_succ", "construction",
     "theorem exists_succ : forall n : Nat, exists m : Nat, m = n + 1", ("Mathlib.Tactic",)),
    # --- ADR 0031 Layer 1: elementary number theory the conjecturer rediscovers ------
    # The first organic panel run promulgated Fermat's little theorem (p=3,5,7) and classic
    # divisibilities as "novel" because the corpus had none of these. Seed them in the SAME
    # ℕ-mod forms the conjecturer emits, so their structural hashes match a re-conjecture and
    # the novelty gate says KNOWN. (Restatements like `(n^5+4n)%5==0` need ADR 0031 Layer 2's
    # decision-procedure equivalence — out of scope here.) All are true.
    # Fermat's little theorem: n^p ≡ n (mod p) for prime p.
    ("fermat_little_2", "invariant", "number_theory", "fermat_little",
     "theorem fermat_little_2 : forall n : Nat, n ^ 2 % 2 = n % 2", ("Mathlib.Tactic",)),
    ("fermat_little_3", "invariant", "number_theory", "fermat_little",
     "theorem fermat_little_3 : forall n : Nat, n ^ 3 % 3 = n % 3", ("Mathlib.Tactic",)),
    ("fermat_little_5", "invariant", "number_theory", "fermat_little",
     "theorem fermat_little_5 : forall n : Nat, n ^ 5 % 5 = n % 5", ("Mathlib.Tactic",)),
    ("fermat_little_7", "invariant", "number_theory", "fermat_little",
     "theorem fermat_little_7 : forall n : Nat, n ^ 7 % 7 = n % 7", ("Mathlib.Tactic",)),
    ("fermat_little_11", "invariant", "number_theory", "fermat_little",
     "theorem fermat_little_11 : forall n : Nat, n ^ 11 % 11 = n % 11", ("Mathlib.Tactic",)),
    ("fermat_little_13", "invariant", "number_theory", "fermat_little",
     "theorem fermat_little_13 : forall n : Nat, n ^ 13 % 13 = n % 13", ("Mathlib.Tactic",)),
    # Power-residue n^k ≡ n divisibilities (Fermat-derived; both mod- and minus-forms).
    ("cube_residue_mod_six", "invariant", "number_theory", "power_residue",
     "theorem cube_residue_mod_six : forall n : Nat, n ^ 3 % 6 = n % 6", ("Mathlib.Tactic",)),
    ("cube_minus_self_div_six", "invariant", "number_theory", "power_residue",
     "theorem cube_minus_self_div_six : forall n : Nat, (n ^ 3 - n) % 6 = 0", ("Mathlib.Tactic",)),
    ("pow5_minus_self_div_thirty", "invariant", "number_theory", "power_residue",
     "theorem pow5_minus_self_div_thirty : forall n : Nat, (n ^ 5 - n) % 30 = 0", ("Mathlib.Tactic",)),
    ("pow7_minus_self_div_42", "invariant", "number_theory", "power_residue",
     "theorem pow7_minus_self_div_42 : forall n : Nat, (n ^ 7 - n) % 42 = 0", ("Mathlib.Tactic",)),
    # Consecutive-product divisibilities: k! divides any k consecutive integers.
    ("two_consec_div_two", "invariant", "number_theory", "consecutive_product",
     "theorem two_consec_div_two : forall n : Nat, n * (n + 1) % 2 = 0", ("Mathlib.Tactic",)),
    ("three_consec_div_six", "invariant", "number_theory", "consecutive_product",
     "theorem three_consec_div_six : forall n : Nat, n * (n + 1) * (n + 2) % 6 = 0", ("Mathlib.Tactic",)),
    ("four_consec_div_24", "invariant", "number_theory", "consecutive_product",
     "theorem four_consec_div_24 : forall n : Nat, n * (n + 1) * (n + 2) * (n + 3) % 24 = 0", ("Mathlib.Tactic",)),
    ("even_pair_div_eight", "invariant", "number_theory", "divisibility",
     "theorem even_pair_div_eight : forall n : Nat, 8 ∣ (2 * n) * (2 * n + 2)", ("Mathlib.Tactic",)),
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

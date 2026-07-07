"""Pre-activation kernel check for the Lean-decided faithfulness backend (ADR 0056 Track A inc. 2).

Runs the code-review's adversarial attack list through the REAL Lean 4.31 kernel and asserts every
prediction: nine attack triples (false congruences, residue collapse, out-of-range residues, vacuous
or empty domains) must all **DEFER** — a PASS on any of them is a false-EXACT-PASS and MUST block
activation — and the positive controls must **PASS**. Plus the `%`==`Int.emod` (Euclidean) defeq
canaries. Run this against the pinned image before an operator flips the backend on with
``register(gate, kernel)``; skips cleanly when the Lean image is absent.

    python scripts/verify_lean_decided.py     # exit 0 = gate cleared, 1 = a false-EXACT-PASS
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

D = "a >= 0 and b >= 0"
# (label, claim_domain, claim_property, established_domain, expect_PASS)
PROBES = [
    ("01 c==m collapse",         D, "a*3 % 3 == 3", D, False),
    ("02 out-of-range residue",  D, "(2*a) % 2 == 2", D, False),
    ("03 residue-collapse eq",   D, "((a*a - a) + (b*b - b)) % 2 == 2", D, False),
    ("04 residue_set out-range", D, "((a*a - a) + (b*b - b)) % 2 == 0 or ((a*a - a) + (b*b - b)) % 2 == 2", D, False),
    ("05 false in-range eq",     D, "(a*a + b*b) % 4 == 3", D, False),
    ("06 false neq",             D, "(a*a + b*b) % 4 != 2", D, False),
    ("07 empty claim_domain",    "a > b and b > a", "(a*a + b*b) % 4 != 3", D, False),
    ("08 empty intersection",    "a == 0 and b == 0", "(a*a + b*b) % 4 != 3", "a >= 1 and b >= 0", False),
    ("09 coverage false",        "a + b >= 0", "(a*a + b*b) % 4 != 3", "a >= 5 and b >= 0", False),
    ("10 positive control",      D, "(a*a + b*b) % 4 != 3", D, True),
    ("11 subtraction PASS",      D, "(a - b)*(a - b) % 4 != 3", D, True),
]
CANARIES = [
    ("percent==Int.emod", "theorem c1 : ∀ (x : ℤ), x % 2 = Int.emod x 2", "fun _ => rfl"),
    ("emod_neg_euclidean", "theorem c2 : Int.emod (-7) 2 = 1", "by decide"),
    ("ediv_neg_floor",     "theorem c3 : Int.ediv (-7) 2 = -4", "by decide"),
]


def main() -> int:
    from leibniz.backends.lean_repl import LeanReplBackend, available
    from leibniz.gates import lean_decided as ld
    from leibniz.propositio import Expressio

    if not available():
        print("Lean REPL image unavailable; cannot verify. (skip — non-fatal)")
        return 0

    backend = LeanReplBackend(timeout_s=150)
    false_pass, wrong = [], []
    try:
        print("== attack list (real kernel) — probes 1-9 MUST DEFER, 10-11 MUST PASS ==")
        for label, cd, cp, ed, expect in PROBES:
            ok, detail = ld.decide_certificate(
                {"claim_domain": cd, "claim_property": cp, "established_domain": ed}, backend)
            good = ok == expect
            if ok and not expect:
                false_pass.append(label)
            elif not good:
                wrong.append(label)
            via = "" if ok else f"  <{detail.get('reason', '')[:52]}>"
            print(f"  {'OK ' if good else '!! '}{label}: {'PASS' if ok else 'DEFER'} "
                  f"(want {'PASS' if expect else 'DEFER'}){via}")

        print("\n== defeq canaries (Euclidean %, Int.emod/Int.ediv) ==")
        for name, thm, proof in CANARIES:
            ok = backend.check_proof(Expressio(theorem_src=thm, imports=ld.IMPORTS), proof)
            if not ok:
                wrong.append(name)
            print(f"  {'OK ' if ok else '!! '}{name}: {'holds' if ok else 'FAILS'}")
    finally:
        backend.close()

    print("=" * 48)
    if false_pass:
        print(f"✗ CRITICAL false-EXACT-PASS on: {false_pass} — DO NOT ACTIVATE.", file=sys.stderr)
        return 1
    if wrong:
        print(f"✗ unexpected results (not false-PASS, but investigate): {wrong}", file=sys.stderr)
        return 1
    print("✓ no false-EXACT-PASS: every attack DEFERs, controls PASS, canaries hold. Gate cleared.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

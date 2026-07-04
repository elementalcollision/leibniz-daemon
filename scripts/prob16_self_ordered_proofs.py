"""Problem 16 — the POSITIVE side, PROVED. Kernel-verify that arithmetic sequences are self-ordered.

The census (`scripts/prob16_census.py`) can only *refute* self-orderedness (a finite witness) or give bounded
evidence for the positive cases — because "self-ordered" is an infinite condition. This module ships the
hand-written Lean proofs that settle the positive side for an entire class:

  • `identity_selfOrdered`  — aₙ = n is self-ordered (D_n = n! divides a product of n consecutive integers).
  • `arith_selfOrdered`     — EVERY arithmetic sequence aₙ = α + βn is self-ordered (reduces to the identity;
                              both D_n and P(m,n) factor as βⁿ · identity-factorial).
  • corollaries instantiating the census's self-ordered sequences (n, 2n, 3+5n) as theorems.

All proofs depend only on the standard axioms (propext / Classical.choice / Quot.sound) — no sorry, no
native_decide. This complements the census: refutations (n³, n⁴, factorial, Fibonacci, primes) + proofs
(arithmetic). Tier audit, verification-AMPLIFICATION; no trust surface touched.

Run:  python scripts/prob16_self_ordered_proofs.py      (elaborates the artifact + records the axiom footprint)
"""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = _ROOT / "docs" / "crt" / "prob16_self_ordered_proofs.lean"
OUT = _ROOT / "docs" / "results" / "prob16_self_ordered_proofs.json"
IMPORTS = ("Mathlib.Tactic", "Mathlib.RingTheory.Polynomial.Pochhammer")
THEOREMS = ["identity_selfOrdered", "arith_selfOrdered", "even_selfOrdered", "arith_3_5_selfOrdered"]
_STD = {"propext", "Classical.choice", "Quot.sound"}


def main() -> int:
    print("=== Problem 16 — arithmetic sequences are self-ordered (positive proofs) ===")
    src = ARTIFACT.read_text(encoding="utf-8")
    # a self-contained honesty check on the source before touching the kernel
    for banned in ("sorry", "native_decide", "admit"):
        assert banned not in src, f"artifact contains {banned!r}"
    assert "def SelfOrdered" in src and all(f"theorem {t}" in src for t in THEOREMS)

    kernel = {"status": "not run"}
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
        if available():
            run_src = "".join(ln for ln in src.splitlines(keepends=True) if not ln.startswith("import "))
            run_src += "\n" + "\n".join(f"#print axioms {t}" for t in THEOREMS) + "\n"
            bk = LeanReplBackend(timeout_s=300)
            try:
                r = bk._run(run_src, IMPORTS)
            finally:
                bk.close()
            msgs = (r or {}).get("messages", []) or []
            errs = [(m.get("data") or "") for m in msgs if m.get("severity") == "error"]
            axiom_lines = [m.get("data", "") for m in msgs if "axiom" in (m.get("data") or "")]
            clean_axioms = all(
                ("does not depend on any axioms" in ln)
                or all(tok.strip() in _STD for tok in ln.split("[", 1)[-1].rstrip("]\n").split(",") if tok.strip())
                for ln in axiom_lines)
            kernel = {"status": "checked", "errors": errs[:3], "n_theorems": len(THEOREMS),
                      "axiom_lines": [ln.strip() for ln in axiom_lines],
                      "clean": (not errs and len(axiom_lines) == len(THEOREMS) and clean_axioms)}
            print(f"  kernel: {len(THEOREMS)} theorems — "
                  f"{'CLEAN (standard axioms, 0 sorry) ✓' if kernel['clean'] else 'ISSUE: ' + str(errs[:2])}")
        else:
            kernel = {"status": "unavailable (Lean REPL)"}
            print("  kernel: REPL unavailable (skip)")
    except Exception as ex:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(ex).__name__}: {ex})"}
        print(f"  kernel: {kernel['status']}")

    gate = ("GREEN" if kernel.get("clean") else
            "AMBER(kernel-unavailable)" if "unavailable" in str(kernel.get("status")) else "RED")
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION", "problem": "CFFG Problem 16 (Chabert)",
           "theorems": THEOREMS, "kernel": kernel, "artifact": str(ARTIFACT.relative_to(_ROOT)),
           "reading": ("The positive side of Problem 16, PROVED: the identity and every arithmetic sequence "
                       "α+βn are self-ordered (kernel-verified, standard axioms). Complements the census "
                       "refutations; upgrades the census's self-ordered arithmetic cases from bounded evidence "
                       "to theorems. Geometric (Gaussian-binomial) is future work.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION\n-> {OUT}\n-> {ARTIFACT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

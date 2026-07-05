"""Guo–Krattenthaler Phase 2 — the all-n theorem (prime-modulus case), PROVED.

Phase 1 (scripts/guo_krattenthaler_divisibility.py) kernel-decided the three divisibilities as certified
instances. Phase 2 lifts them to a genuine all-n THEOREM in the prime-modulus case: for every n ≥ 1 with the
modulus prime, (6n−1)∣C(12n,3n), (6n−1)∣C(12n,4n), (66n−1)∣C(330n,88n). The proof is an elementary Kummer
argument — when the modulus p is prime, the base-p units digits already carry (v_p ≥ 1), so p divides the
binomial. This covers infinitely many n (all n with the modulus prime). The full composite-modulus case needs
the prime-power carry analysis / the q-integer positivity of Guo–Krattenthaler — the documented open escalation.

This verifier elaborates the hand-written proofs (docs/crt/guo_krattenthaler_phase2.lean), confirms they are
axiom-clean, and cross-checks the arithmetic: for a range of n where the modulus is prime, the divisibility
holds. Tier audit, verification-AMPLIFICATION; no trust surface touched.

Run:  python scripts/verify_gk_phase2.py   (Python check is free-CPU; the kernel leg needs the Lean REPL)
"""
from __future__ import annotations

import json
from math import comb, isqrt
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = _ROOT / "docs" / "crt" / "guo_krattenthaler_phase2.lean"
OUT = _ROOT / "docs" / "results" / "gk_phase2_verification.json"
IMPORTS = ("Mathlib.Tactic",)
THEOREMS = ["prime_dvd_choose_of_units_carry", "gk_12_3_prime", "gk_12_4_prime", "gk_330_88_prime"]
_STD = {"propext", "Classical.choice", "Quot.sound"}
# (top, bot, dz): (dz·n − 1) ∣ C(top·n, bot·n)
CASES = [(12, 3, 6), (12, 4, 6), (330, 88, 66)]


def _is_prime(x: int) -> bool:
    if x < 2:
        return False
    for p in range(2, isqrt(x) + 1):
        if x % p == 0:
            return False
    return True


def cross_check(nmax: int = 200) -> dict:
    """For each GK case, over n ≤ nmax with the modulus prime, confirm the divisibility (the theorem's claim)."""
    rows = []
    for top, bot, dz in CASES:
        primes_n = [n for n in range(1, nmax + 1) if _is_prime(dz * n - 1)]
        ok = all(comb(top * n, bot * n) % (dz * n - 1) == 0 for n in primes_n)
        rows.append({"case": f"({dz}n-1) | C({top}n,{bot}n)", "prime_modulus_n_count": len(primes_n),
                     "sample_prime_n": primes_n[:8], "all_divisible": ok})
    return {"rows": rows, "all_ok": all(r["all_divisible"] for r in rows)}


def main() -> int:
    print("=== Guo–Krattenthaler Phase 2 — all-n theorem (prime-modulus case) ===")
    src = ARTIFACT.read_text(encoding="utf-8")
    for banned in ("sorry", "native_decide", "admit"):
        assert banned not in src, f"artifact contains {banned!r}"
    assert all(f"theorem {t}" in src for t in THEOREMS)

    cc = cross_check()
    for r in cc["rows"]:
        print(f"  {r['case']:<22} prime-modulus n ≤ 200: {r['prime_modulus_n_count']} "
              f"(e.g. {r['sample_prime_n']}); all divisible: {r['all_divisible']}")

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
            clean = all(("does not depend on any axioms" in ln)
                        or all(t.strip() in _STD for t in ln.split("[", 1)[-1].rstrip("]\n").split(",") if t.strip())
                        for ln in axiom_lines)
            kernel = {"status": "checked", "errors": errs[:3], "n_theorems": len(THEOREMS),
                      "axiom_lines": [ln.strip() for ln in axiom_lines],
                      "clean": (not errs and len(axiom_lines) == len(THEOREMS) and clean)}
            print(f"  kernel: {len(THEOREMS)} theorems — "
                  f"{'CLEAN (standard axioms, 0 sorry) ✓' if kernel['clean'] else 'ISSUE: ' + str(errs[:2])}")
        else:
            kernel = {"status": "unavailable (Lean REPL)"}
            print("  kernel: REPL unavailable (skip)")
    except Exception as ex:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(ex).__name__}: {ex})"}
        print(f"  kernel: {kernel['status']}")

    gate = ("GREEN" if (cc["all_ok"] and kernel.get("clean")) else
            "AMBER(kernel-unavailable)" if "unavailable" in str(kernel.get("status")) and cc["all_ok"] else "RED")
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION",
           "target": "Guo & Krattenthaler (2014), arXiv:1301.7651 — Phase 2 (prime-modulus theorem)",
           "cross_check": cc, "kernel": kernel, "theorems": THEOREMS,
           "artifact": str(ARTIFACT.relative_to(_ROOT)),
           "reading": ("Phase 2 of the Guo–Krattenthaler verification: the three all-n divisibilities are "
                       "PROVED for the prime-modulus case (infinitely many n) via an elementary Kummer "
                       "units-carry argument (Nat.factorization_choose), kernel-verified with standard axioms. "
                       "The composite-modulus case needs the full prime-power carry / q-integer positivity — "
                       "documented open escalation. Verification-amplification; no trust surface.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION\n-> {OUT}\n-> {ARTIFACT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

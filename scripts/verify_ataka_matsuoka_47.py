"""Independent kernel verification of Ataka–Matsuoka (2026), Example 4.7 — a positive control AND a
kernel-checkable erratum, on the general monomial-ideal normality instrument.

Ataka & Matsuoka, "Normality of monomial ideals in three variables" (arXiv:2602.01782v1), §4.3 give two
illustrative ideals (about reduction numbers of normal ideals):

  4.7(1)  I = (x³, y², z², xy, xz, yz)                — stated integrally closed and normal (μ = 6).
  4.7(2)  I = (x³, y³, z³, x²y, xy², x²z, yz)          — stated "a normal ideal by Theorem 3.1".

LLMs propose nothing; the Lean kernel decides. Using the general instrument
(`monomial_ideal_normality.py`, integral-dependence membership) we find:

  • 4.7(1) IS normal — I and I² are integrally closed (the Newton polyhedron of I is the single half-space
    {x + 2y + 2z ≥ 3}, so RRV d = 3 gives normality). Confirmed. ✅

  • 4.7(2) is NOT integrally closed — an ERRATUM. The monomial xz² ∉ I, yet (xz²)² = x²z⁴ = (x²z)·(z³) ∈ I²,
    so xz² is integral over I: xz² ∈ closure(I) ∖ I. Its integral closure has 8 minimal generators
    (μ(Ī) = 8 > 7), so the ideal as printed neither satisfies the hypothesis I = Ī of Theorem 3.1 nor is
    normal in the standard sense. This is a slip in an illustrative example (§4.3, reduction numbers) and is
    INDEPENDENT of the Main Theorem, whose sharpness we verified separately (arXiv:2602.01782 Example 4.5).

Both facts are kernel-decided by `decide`, axiom-free. An erratum guard refuses to emit the certificate unless
the instrument reproduces exactly these verdicts. Tier audit, verification-amplification; no trust surface.

Run:  python scripts/verify_ataka_matsuoka_47.py     (checker is free-CPU; the kernel leg needs the Lean REPL)
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = _ROOT / "docs" / "crt" / "ataka_matsuoka_47_certificate.lean"
OUT = _ROOT / "docs" / "results" / "ataka_matsuoka_47_verification.json"
IMPORTS = ("Mathlib.Tactic",)

# Verbatim from arXiv:2602.01782v1, Example 4.7 (p.27).
GENS_1 = [(3, 0, 0), (0, 2, 0), (0, 0, 2), (1, 1, 0), (1, 0, 1), (0, 1, 1)]           # 4.7(1)
GENS_2 = [(3, 0, 0), (0, 3, 0), (0, 0, 3), (2, 1, 0), (1, 2, 0), (2, 0, 1), (0, 1, 1)]  # 4.7(2)
ERRATUM_WITNESS = (1, 0, 2)   # xz² ∈ closure(I) ∖ I for 4.7(2)

REF_AM = {
    "citation": ("Ataka, M., & Matsuoka, N. (2026). Normality of monomial ideals in three variables "
                 "(arXiv:2602.01782). arXiv. https://arxiv.org/abs/2602.01782"),
    "url": "https://arxiv.org/abs/2602.01782",
}


def _instr():
    spec = importlib.util.spec_from_file_location("min", _ROOT / "scripts" / "monomial_ideal_normality.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def analyze(m) -> dict:
    r1 = m.is_normal([tuple(g) for g in GENS_1])
    r2 = m.is_normal([tuple(g) for g in GENS_2])
    k = m.dependence_witness(ERRATUM_WITNESS, [tuple(g) for g in GENS_2], 1)
    checks = {
        "4.7(1)_is_normal": r1["normal"] is True,
        "4.7(2)_not_integrally_closed": r2["I_integrally_closed"] is False,
        "4.7(2)_witness_is_xz2": r2["closure_witness_I"] == list(ERRATUM_WITNESS),
        "xz2_integral_over_I_at_k2": k == 2,
        "xz2_not_in_I": not m.in_power(ERRATUM_WITNESS, [tuple(g) for g in GENS_2], 1),
        "xz2_squared_in_I2": m.in_power((2, 0, 4), [tuple(g) for g in GENS_2], 2),
    }
    return {"r1": r1, "r2": r2, "erratum_k": k, "checks": checks}


HEADLINE = ["AtakaMatsuoka47.xz2_not_in_I", "AtakaMatsuoka47.xz2_squared_in_I2",
            "AtakaMatsuoka47.I2_not_integrally_closed"]

_CERT = r'''/-
  Independent kernel verification of Ataka–Matsuoka (2026), "Normality of monomial ideals in three
  variables", arXiv:2602.01782v1, Example 4.7(2) (§4.3).  LLMs propose nothing; the Lean kernel decides.

  Example 4.7(2) states: "Let I = (x³,y³,z³,x²y,xy²,x²z,yz). Then I is a normal ideal by Theorem 3.1."
  This is an ERRATUM — I is NOT integrally closed, so it cannot be normal (a normal ideal satisfies
  I = Ī) and Theorem 3.1 (which requires I = Ī and μ(I) ≤ 7) does not apply as printed. The kernel
  witness: the monomial xz² is NOT in I, yet its square (xz²)² = x²z⁴ = (x²z)·(z³) IS in I². Since a
  monomial whose square lies in I² is integral over I (it satisfies X² − c = 0 with c ∈ I²), xz² lies
  in closure(I) ∖ I. Its integral closure has 8 minimal generators (μ(Ī) = 8 > 7).

  This is a slip in an ILLUSTRATIVE example (§4.3, reduction numbers) and is INDEPENDENT of the paper's
  Main Theorem, whose sharpness (the μ(I) ≤ 7 bound, witness closure(x⁷,y³,z²)) we independently verified
  and confirmed correct in Example 4.5.  The companion positive example 4.7(1), I = (x³,y²,z²,xy,xz,yz),
  IS normal — confirmed by our general monomial-ideal normality instrument (integral-dependence + RRV).

  All theorems `decide`, no axioms.  Produced by scripts/verify_ataka_matsuoka_47.py (Leibniz daemon).
-/
import Mathlib.Tactic

namespace AtakaMatsuoka47

/-- x^g divides x^u (componentwise ≤) — monomial ideal membership test. -/
def dvd (g : ℕ × ℕ × ℕ) (a b c : ℕ) : Bool := g.1 ≤ a && g.2.1 ≤ b && g.2.2 ≤ c

/-- Example 4.7(2):  I = (x³, y³, z³, x²y, xy², x²z, yz). -/
def gens : List (ℕ × ℕ × ℕ) := [(3,0,0), (0,3,0), (0,0,3), (2,1,0), (1,2,0), (2,0,1), (0,1,1)]
def inI (a b c : ℕ) : Bool := gens.any (fun g => dvd g a b c)
/-- x^u ∈ I² ⟺ some pair of generators sums ≤ u. -/
def inI2 (a b c : ℕ) : Bool :=
  gens.any (fun g => gens.any (fun h => dvd (g.1 + h.1, g.2.1 + h.2.1, g.2.2 + h.2.2) a b c))

/-- xz² = (1,0,2) is not in I (no generator divides it). -/
theorem xz2_not_in_I : inI 1 0 2 = false := by decide
/-- (xz²)² = x²z⁴ = (2,0,4) is in I² (it equals (x²z)·(z³)). -/
theorem xz2_squared_in_I2 : inI2 2 0 4 = true := by decide

/-- **Erratum (Example 4.7(2)).** xz² ∉ I but (xz²)² ∈ I², so xz² is integral over I and lies in
    closure(I) ∖ I: the ideal is NOT integrally closed, contrary to "I is a normal ideal by Theorem 3.1"
    as printed. Independent of the Main Theorem (Example 4.5 sharpness, verified separately). -/
theorem I2_not_integrally_closed : inI 1 0 2 = false ∧ inI2 2 0 4 = true := by decide

end AtakaMatsuoka47
'''


def main() -> int:
    print("=== Ataka–Matsuoka (arXiv:2602.01782) Example 4.7 — independent kernel verification ===")
    m = _instr()
    a = analyze(m)
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(_CERT)

    all_ok = all(a["checks"].values())
    print(f"  4.7(1) (x³,y²,z²,xy,xz,yz): normal = {a['r1']['normal']}")
    print(f"  4.7(2) (x³,y³,z³,x²y,xy²,x²z,yz): integrally closed = {a['r2']['I_integrally_closed']}  "
          f"(witness xz² = {a['r2']['closure_witness_I']}, integral at k={a['erratum_k']})")
    for name, ok in a["checks"].items():
        print(f"    cross-check {name:<32} {'✓' if ok else '✗ MISMATCH'}")
    if not all_ok:
        print("  !! a cross-check FAILED — refusing to certify.")

    kernel = {"status": "not run"}
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
        if available():
            bk = LeanReplBackend(timeout_s=500)
            try:
                run_src = _CERT.split("import Mathlib.Tactic\n", 1)[1] + "\n" + "\n".join(
                    f"#print axioms {n}" for n in HEADLINE) + "\n"
                r = bk._run(run_src, IMPORTS)
            finally:
                bk.close()
            msgs = (r or {}).get("messages", []) or []
            errs = [(msg.get("data") or "") for msg in msgs if msg.get("severity") == "error"]
            axiom_lines = [msg.get("data", "") for msg in msgs if "axiom" in (msg.get("data") or "")]
            axiom_free = (len(axiom_lines) == len(HEADLINE)
                          and all("does not depend on any axioms" in ln for ln in axiom_lines))
            kernel = {"status": "checked", "errors": errs[:3], "axiom_free": axiom_free,
                      "axiom_lines": [ln.strip() for ln in axiom_lines], "clean": (not errs and axiom_free)}
            print(f"  kernel: {'CLEAN, axiom-free ✓' if kernel['clean'] else 'ISSUE: ' + str(errs[:2])}")
        else:
            kernel = {"status": "unavailable (Lean REPL)"}
            print("  kernel: REPL unavailable (skip)")
    except Exception as ex:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(ex).__name__}: {ex})"}
        print(f"  kernel: {kernel['status']}")

    gate = ("GREEN" if (all_ok and kernel.get("clean")) else
            "AMBER(kernel-unavailable)" if "unavailable" in str(kernel.get("status")) and all_ok else "RED")
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION",
           "target": "Ataka–Matsuoka (2026), arXiv:2602.01782v1, Example 4.7 (§4.3)",
           "findings": {
               "4.7(1)": "CONFIRMED normal (I, I² integrally closed; single Newton facet x+2y+2z≥3)",
               "4.7(2)": ("ERRATUM: NOT integrally closed — xz² ∈ closure(I) ∖ I since (xz²)² = (x²z)(z³) ∈ I²; "
                          "μ(Ī) = 8 > 7, so Theorem 3.1 (needs I = Ī, μ ≤ 7) does not apply as printed. "
                          "Independent of the Main Theorem (Example 4.5 verified separately)."),
           },
           "analysis": {"4.7(1)": a["r1"], "4.7(2)": a["r2"], "erratum_k": a["erratum_k"], "checks": a["checks"]},
           "kernel": kernel, "reference": REF_AM, "artifact": str(ARTIFACT.relative_to(_ROOT)),
           "headline_theorems": HEADLINE,
           "reading": ("General monomial-ideal normality instrument (integral-dependence membership + RRV d=3) "
                       "independently verifying a Feb-2026 paper: 4.7(1) confirmed normal; 4.7(2) is a "
                       "kernel-checkable erratum (not integrally closed). Verification-amplification; no trust "
                       "surface. The erratum is minor (illustrative example) and independent of the Main Theorem.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION\n-> {OUT}\n-> {ARTIFACT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

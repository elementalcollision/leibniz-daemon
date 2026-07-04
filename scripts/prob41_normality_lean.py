"""Problem 41 (Cahen–Fontana–Frisch–Glaz / Swanson) — monomial-ideal normality certificates.

Problem 41 asks to classify the triples (a,b,c) for which every power of I = closure(x^a, y^b, z^c) in k[x,y,z]
is integrally closed (I *normal*). The full classification is open, but two finite reductions make certifying
any *specific* triple a decidable kernel computation:

  * Newton polyhedron — for a monomial ideal, a monomial x^u is in the integral closure iff u lies in
    conv(exponents)+R≥0^n. For the pure-power ideal (x^a,y^b,z^c), that is exactly {u≥0 : u·(L/a,L/b,L/c) ≥ L},
    L = lcm(a,b,c); i.e. an exact integer inequality on the L-cleared weighted degree wt(u).
  * Reid–Roberts–Vitulli — in d=3 variables I is normal iff I and I^2 are integrally closed. I is closed by
    construction, so normality ⟺ I^2 integrally closed. And x^u ∈ I^2 collapses (I is an up-set, wt is linear)
    to: ∃ v ≤ u with L ≤ wt(v) ≤ wt(u) − L. So "x^u ∈ closure(I^2) ∖ I^2" is a finite, exact, kernel-decidable
    predicate — a self-contained NON-NORMALITY certificate for the triple.

This module ships a reusable `certify(a,b,c)` checker (exact integer arithmetic) and emits the Lean certificate
for a non-normal triple. The flagship is the Huneke–Swanson boundary point **(4,5,7)**: it is NOT normal,
witnessed by the monomial x^2 y^4 z^5 (weight 282 ≥ 280 = 2L, so in closure(I^2); but not in I^2). Both the
collapsed (90-case) and the direct product-definition (8100-case) Lean forms are kernel-decided by `decide`
with **no axiom dependencies at all** (a fully computational proof).

Honest scope: Leibniz cannot *classify* all triples (that is the open mathematics; cf. Ataka–Matsuoka
arXiv:2602.01782, Feb 2026, active on this family). It certifies specific triples on both sides of the boundary —
a verified, reusable "is (a,b,c) normal?" instrument. Tier audit, verification-AMPLIFICATION. No trust surface
touched; read-only.

Run:  python scripts/prob41_normality_lean.py   (the reusable checker is free-CPU; the kernel leg needs the REPL)
"""
from __future__ import annotations

import json
from math import gcd
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "prob41_normality.json"
ARTIFACT = _ROOT / "docs" / "crt" / "prob41_457_certificate.lean"
IMPORTS = ("Mathlib.Tactic",)


def _lcm3(a: int, b: int, c: int) -> int:
    ab = a * b // gcd(a, b)
    return ab * c // gcd(ab, c)


def certify(a: int, b: int, c: int) -> dict:
    """Is I = closure(x^a,y^b,z^c) normal? Exact finite check via RRV (d=3 ⟹ only I^2 matters) + Newton
    polyhedron. Returns normality and, if not normal, the lexicographically-first witness monomial exponent."""
    L = _lcm3(a, b, c)
    wa, wb, wc = L // a, L // b, L // c

    def wt(u):
        return wa * u[0] + wb * u[1] + wc * u[2]

    def in_I2(u) -> bool:
        # x^u ∈ I^2 ⟺ ∃ v ≤ u with L ≤ wt(v) ≤ wt(u) − L
        wu = wt(u)
        for v0 in range(u[0] + 1):
            for v1 in range(u[1] + 1):
                base = wa * v0 + wb * v1
                for v2 in range(u[2] + 1):
                    w = base + wc * v2
                    if L <= w <= wu - L:
                        return True
        return False

    # A minimal generator of closure(I^2) has each coord ≤ 2·(pure power); search that box.
    for u0 in range(2 * a + 1):
        for u1 in range(2 * b + 1):
            for u2 in range(2 * c + 1):
                u = (u0, u1, u2)
                if wt(u) >= 2 * L and not in_I2(u):
                    return {"triple": [a, b, c], "L": L, "weights": [wa, wb, wc],
                            "normal": False, "witness": list(u), "witness_wt": wt(u)}
    return {"triple": [a, b, c], "L": L, "weights": [wa, wb, wc], "normal": True, "witness": None}


def lean_cert(a: int, b: int, c: int, witness) -> str:
    """Emit the collapsed-form Lean non-normality certificate for a triple + witness (kernel-decidable)."""
    L = _lcm3(a, b, c)
    wa, wb, wc = L // a, L // b, L // c
    u1, u2, u3 = witness
    wu = wa * u1 + wb * u2 + wc * u3
    name = f"triple_{a}_{b}_{c}_not_normal"
    return (
        f"namespace Prob41_{a}_{b}_{c}\n"
        f"/-- L-cleared weighted degree wrt ({a},{b},{c}); L = lcm = {L}, weights = ({wa},{wb},{wc}). -/\n"
        f"def wt (a b c : ℕ) : ℕ := {wa}*a + {wb}*b + {wc}*c\n"
        f"/-- x^u ∈ I² collapses to ∃ v ≤ u with {L} ≤ wt v ≤ wt u − {L}. Here wt u = {wu}. -/\n"
        f"def inI2 : Bool :=\n"
        f"  (List.range {u1 + 1}).any fun a => (List.range {u2 + 1}).any fun b => "
        f"(List.range {u3 + 1}).any fun c =>\n"
        f"    {L} ≤ wt a b c && wt a b c ≤ {wu - L}\n"
        f"/-- ({a},{b},{c}) is NOT normal: x^{tuple(witness)} ∈ closure(I²) (wt={wu} ≥ {2 * L}) but ∉ I². -/\n"
        f"theorem {name} : {2 * L} ≤ wt {u1} {u2} {u3} ∧ inI2 = false := by decide\n"
        f"end Prob41_{a}_{b}_{c}\n"
    )


# The flagship (4,5,7) artifact carries BOTH the collapsed and the direct product-definition forms.
SRC_457 = r"""
namespace Prob41_457
def wt (a b c : ℕ) : ℕ := 35*a + 28*b + 20*c

/-- **Collapsed form.** x^(2,4,5) ∈ I² ⟺ ∃ v ≤ (2,4,5) with 140 ≤ wt v ≤ 282−140 = 142
    (I = {wt ≥ 140} is an up-set and wt is linear). No such v exists, and wt(2,4,5)=282 ≥ 280,
    so x^2y^4z^5 ∈ closure(I²) \ I² — hence I = closure(x⁴,y⁵,z⁷) is NOT normal. -/
def inI2_collapsed : Bool :=
  (List.range 3).any fun a => (List.range 5).any fun b => (List.range 6).any fun c =>
    140 ≤ wt a b c && wt a b c ≤ 142
theorem four_five_seven_not_normal_collapsed :
    280 ≤ wt 2 4 5 ∧ inI2_collapsed = false := by decide

/-- **Direct form** (no collapse — the product definition of I²): no two monomials v,w ∈ I with
    x^v·x^w ∣ x^(2,4,5). Equivalent, and manifestly the definition of I²-membership. -/
def inIb (a b c : ℕ) : Bool := 140 ≤ wt a b c
def box (u1 u2 u3 : ℕ) : List (ℕ × ℕ × ℕ) :=
  (List.range (u1+1)).flatMap fun a => (List.range (u2+1)).flatMap fun b =>
    (List.range (u3+1)).map fun c => (a, b, c)
def inI2_direct (u1 u2 u3 : ℕ) : Bool :=
  (box u1 u2 u3).any fun v => (box u1 u2 u3).any fun w =>
    inIb v.1 v.2.1 v.2.2 && inIb w.1 w.2.1 w.2.2
      && v.1 + w.1 ≤ u1 && v.2.1 + w.2.1 ≤ u2 && v.2.2 + w.2.2 ≤ u3
theorem four_five_seven_not_normal_direct :
    280 ≤ wt 2 4 5 ∧ inI2_direct 2 4 5 = false := by decide
end Prob41_457
"""
HEADLINE = ["Prob41_457.four_five_seven_not_normal_collapsed", "Prob41_457.four_five_seven_not_normal_direct"]

# A small registry exercising the reusable checker on both sides of the boundary.
REGISTRY = [(4, 5, 7), (3, 3, 3), (2, 3, 5), (1, 1, 1), (4, 5, 6)]


def write_artifact() -> None:
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    header = ("/-\n  Problem 41 (Cahen–Fontana–Frisch–Glaz / Swanson) — the triple (4,5,7) is NOT normal.\n"
              "  Kernel-decided (`decide`), NO axiom dependencies. I = closure(x⁴,y⁵,z⁷);\n"
              "  witness x²y⁴z⁵ ∈ closure(I²) \\ I². Both collapsed and direct forms; see"
              " scripts/prob41_normality_lean.py.\n-/\n")
    ARTIFACT.write_text(header + "".join(f"import {i}\n" for i in IMPORTS) + "\n" + SRC_457.lstrip() + "\n")


def main() -> int:
    print("=== Problem 41 monomial-normality certificates ===")
    write_artifact()
    # 1) reusable checker over the registry (free-CPU, exact).
    checked = [certify(*t) for t in REGISTRY]
    for r in checked:
        tag = "NOT normal" if not r["normal"] else "normal"
        w = f"  witness x^{tuple(r['witness'])} (wt={r['witness_wt']}≥{2 * r['L']})" if not r["normal"] else ""
        print(f"  {tuple(r['triple'])!s:<12} L={r['L']:<4} -> {tag}{w}")
    # sanity the checker's headline facts
    c457 = next(r for r in checked if r["triple"] == [4, 5, 7])
    checker_ok = (not c457["normal"] and c457["witness"] == [2, 4, 5]
                  and next(r for r in checked if r["triple"] == [3, 3, 3])["normal"])

    # 2) kernel leg: the (4,5,7) certificate elaborates + is axiom-free.
    kernel = {"status": "not run"}
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
        if available():
            bk = LeanReplBackend(timeout_s=400)
            try:
                src = SRC_457 + "\n" + "\n".join(f"#print axioms {n}" for n in HEADLINE) + "\n"
                r = bk._run(src, IMPORTS)
            finally:
                bk.close()
            msgs = (r or {}).get("messages", []) or []
            errs = [(m.get("data") or "") for m in msgs if m.get("severity") == "error"]
            axiom_lines = [m.get("data", "") for m in msgs if "axiom" in (m.get("data") or "")]
            axiom_free = all("does not depend on any axioms" in ln for ln in axiom_lines) and len(axiom_lines) == 2
            kernel = {"status": "checked", "errors": errs[:2], "axiom_free": axiom_free,
                      "axiom_lines": [ln.strip() for ln in axiom_lines], "clean": (not errs and axiom_free)}
            print(f"  kernel: {'CLEAN, axiom-free ✓' if kernel['clean'] else 'ISSUE'}")
        else:
            kernel = {"status": "unavailable (Lean REPL)"}
            print("  kernel: REPL unavailable (skip)")
    except Exception as ex:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(ex).__name__}: {ex})"}
        print(f"  kernel: {kernel['status']}")

    gate = ("GREEN" if (checker_ok and kernel.get("clean")) else
            "AMBER(kernel-unavailable)" if "unavailable" in str(kernel.get("status")) and checker_ok else "RED")
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION", "problem": "CFFG/Swanson Problem 41",
           "flagship": "(4,5,7) NOT normal; witness x^2 y^4 z^5 ∈ closure(I^2) \\ I^2; kernel-decided, axiom-free",
           "registry": checked, "checker_ok": checker_ok, "kernel": kernel,
           "artifact": str(ARTIFACT.relative_to(_ROOT)),
           "reading": ("Reusable monomial-normality checker (Newton polyhedron + Reid–Roberts–Vitulli d=3 "
                       "reduction) + the kernel-decided (4,5,7) non-normality certificate (axiom-free). CREATE "
                       "(a verified 'is (a,b,c) normal?' instrument) + PROVE (certify boundary triples of a still-"
                       "open classification). Verification-AMPLIFICATION; certified instances, not a classification.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION\n-> {OUT}\n-> {ARTIFACT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

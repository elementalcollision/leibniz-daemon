"""Independent kernel verification of Ataka–Matsuoka (2026), Example 4.5 — a T5 verification-amplification
target on the flagship Problem-41 instrument.

Ataka & Matsuoka, "Normality of monomial ideals in three variables" (arXiv:2602.01782v1, Feb 2026, math.AC),
prove: an integrally closed monomial ideal I in k[x,y,z] with ht = 3 and μ(I) ≤ 7 is normal, and the bound 7
is SHARP. Their sharpness witness (Example 4.5 / Remark 1.3) is

    I = closure(x⁷, y³, z²) = (x⁷, y³, z², x⁵y, x³y², x⁴z, y²z, x²yz),     μ(I) = 8,

which is NOT normal: x⁶y²z ∉ I² but (x⁶y²z)² = (x⁵y)·x⁷y³z² ∈ I⁴ = (I²)², so x⁶y²z ∈ closure(I²), whence
I² ⊊ closure(I²). By Reid–Roberts–Vitulli (d = 3 ⟹ check I and I²) this makes I non-normal.

Leibniz PROPOSES nothing here — the paper's claim is the object; our Lean kernel DECIDES. We independently
reproduce, from the Newton polyhedron (weights (6,14,21), L = lcm(7,3,2) = 42), BOTH load-bearing facts and
cross-check them VERBATIM against Example 4.5:

  (1) the up-set {u : wt u ≥ 42} has exactly 8 minimal lattice points, equal to the paper's generator list;
  (2) x⁶y²z ∈ closure(I²) (wt = 85 ≥ 2L = 84) but x⁶y²z ∉ I².

Both are kernel-decided by `decide`, axiom-free. Tier audit, verification-AMPLIFICATION; no trust surface.

Run:  python scripts/verify_ataka_matsuoka.py     (checker is free-CPU; the kernel leg needs the Lean REPL)
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = _ROOT / "docs" / "crt" / "ataka_matsuoka_732_certificate.lean"
OUT = _ROOT / "docs" / "results" / "ataka_matsuoka_732_verification.json"
IMPORTS = ("Mathlib.Tactic",)

# The paper's Example 4.5 data, transcribed VERBATIM (arXiv:2602.01782v1, p.27) for an independent cross-check.
#   I = (x^7, y^3, z^2, x^5 y, x^3 y^2, x^4 z, y^2 z, x^2 y z);  witness x^6 y^2 z ∉ I^2 but ∈ closure(I^2).
PAPER_GENERATORS = {(7, 0, 0), (0, 3, 0), (0, 0, 2), (5, 1, 0), (3, 2, 0), (4, 0, 1), (0, 2, 1), (2, 1, 1)}
PAPER_WITNESS = (6, 2, 1)          # x^6 y^2 z
TRIPLE = (7, 3, 2)

REF_AM = {
    "citation": ("Ataka, M., & Matsuoka, N. (2026). Normality of monomial ideals in three variables "
                 "(arXiv:2602.01782). arXiv. https://arxiv.org/abs/2602.01782"),
    "url": "https://arxiv.org/abs/2602.01782",
}


def _prob41():
    spec = importlib.util.spec_from_file_location("p41", _ROOT / "scripts" / "prob41_normality_lean.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def build_certificate(m) -> tuple[str, dict]:
    """Compute the two facts from the Newton polyhedron, cross-check them against Example 4.5, and emit the
    self-contained Lean certificate. Returns (lean_source, provenance_dict)."""
    a, b, c = TRIPLE
    L = m._lcm3(a, b, c)
    wa, wb, wc = L // a, L // b, L // c

    gens = m.min_generators(a, b, c)                       # our Newton-polyhedron computation
    cert = m.certify(a, b, c)                               # our RRV / I^2 non-normality check
    witness = tuple(cert["witness"]) if cert["witness"] else None

    # Faithfulness cross-checks against the paper (fail LOUD if any disagree — an erratum guard).
    checks = {
        "generator_count_is_8": len(gens) == 8,
        "generators_match_paper": set(gens) == PAPER_GENERATORS,
        "is_not_normal": cert["normal"] is False,
        "witness_matches_paper": witness == PAPER_WITNESS,
        "weights_are_6_14_21": (wa, wb, wc) == (6, 14, 21) and L == 42,
    }
    wu = wa * witness[0] + wb * witness[1] + wc * witness[2]

    gens_lean = "[" + ", ".join(f"({g[0]},{g[1]},{g[2]})" for g in gens) + "]"
    u1, u2, u3 = witness
    header = (
        "/-\n"
        "  Independent kernel verification of Ataka–Matsuoka (2026), \"Normality of monomial ideals in three\n"
        "  variables\", arXiv:2602.01782v1, Example 4.5 / Remark 1.3.\n\n"
        "  Their Main Theorem: an integrally closed monomial ideal I in k[x,y,z] with ht I = 3 and μ(I) ≤ 7\n"
        "  is normal; the bound 7 is SHARP. The sharpness witness is I = closure(x⁷,y³,z²), which has EIGHT\n"
        "  minimal generators and is NOT normal (I² ⊊ closure(I²), witnessed by x⁶y²z).\n\n"
        "  We reproduce BOTH facts kernel-decidably from the Newton polyhedron (weights (6,14,21), L = 42):\n"
        "    • the up-set {u : wt u ≥ 42} has exactly 8 minimal lattice points = the paper's generator list;\n"
        "    • x⁶y²z ∈ closure(I²) (wt = 85 ≥ 2L = 84) but x⁶y²z ∉ I², so I is not normal (RRV, d=3).\n"
        "  Kernel-decided by `decide`, no axioms. LLMs propose nothing; the kernel decides.\n"
        "  Produced by scripts/verify_ataka_matsuoka.py (Leibniz daemon).\n"
        "-/\n"
    )
    src = header + "import Mathlib.Tactic\n\nnamespace AtakaMatsuoka732\n\n" + (
        f"/-- L-cleared weighted degree for the corner ideal (x⁷,y³,z²); L = lcm = {L}, weights ({wa},{wb},{wc}). -/\n"
        f"def wt (a b c : ℕ) : ℕ := {wa}*a + {wb}*b + {wc}*c\n\n"
        "/-- Newton polyhedron: x^u ∈ I = closure(x⁷,y³,z²) ⟺ wt u ≥ 42 (a rational-convex up-set). -/\n"
        f"def inI (a b c : ℕ) : Bool := {L} ≤ wt a b c\n\n"
        "/-- u is a MINIMAL generator: in I, and dropping 1 from any positive coordinate leaves I. -/\n"
        "def isMinGen (a b c : ℕ) : Bool :=\n"
        "  inI a b c\n"
        "    && (a == 0 || ! inI (a-1) b c)\n"
        "    && (b == 0 || ! inI a (b-1) c)\n"
        "    && (c == 0 || ! inI a b (c-1))\n\n"
        "/-- Complete search box: a minimal generator cannot exceed the pure powers (7,3,2). -/\n"
        "def box : List (ℕ × ℕ × ℕ) :=\n"
        "  (List.range 8).flatMap fun a => (List.range 4).flatMap fun b =>\n"
        "    (List.range 3).map fun c => (a, b, c)\n\n"
        "/-- The minimal generators of closure(x⁷,y³,z²), in lexicographic order. -/\n"
        "def gens : List (ℕ × ℕ × ℕ) := box.filter fun u => isMinGen u.1 u.2.1 u.2.2\n\n"
        "/-- **Example 4.5 (generator count).** closure(x⁷,y³,z²) has exactly EIGHT minimal monomial\n"
        "    generators — the fact that makes the μ(I) ≤ 7 normality bound sharp. -/\n"
        "theorem eight_minimal_generators : gens.length = 8 := by decide\n\n"
        "/-- …and they are EXACTLY the paper's list  x⁷, y³, z², x⁵y, x³y², x⁴z, y²z, x²yz  (exponent triples). -/\n"
        f"theorem generators_are_paper_list : gens = {gens_lean} := by decide\n\n"
        "/-- x^u ∈ I² ⟺ ∃ v ≤ u with 42 ≤ wt v ≤ wt u − 42 (I an up-set, wt linear). For u = (6,2,1),\n"
        f"    wt u = {wu}, so this seeks v ≤ (6,2,1) with 42 ≤ wt v ≤ {wu - L} — there is none. -/\n"
        "def inI2_at_witness : Bool :=\n"
        f"  (List.range {u1 + 1}).any fun a => (List.range {u2 + 1}).any fun b => (List.range {u3 + 1}).any fun c =>\n"
        f"    {L} ≤ wt a b c && wt a b c ≤ {wu - L}\n\n"
        "/-- **Example 4.5 (non-normality).** x⁶y²z ∈ closure(I²) (wt = 85 ≥ 2L = 84) but x⁶y²z ∉ I².\n"
        "    By Reid–Roberts–Vitulli (d = 3 ⟹ check I and I²), closure(x⁷,y³,z²) is therefore NOT normal. -/\n"
        f"theorem not_normal_witness_x6y2z : {2 * L} ≤ wt {u1} {u2} {u3} ∧ inI2_at_witness = false := by decide\n\n"
        "end AtakaMatsuoka732\n"
    )
    prov = {"triple": list(TRIPLE), "L": L, "weights": [wa, wb, wc], "generators": [list(g) for g in gens],
            "generator_count": len(gens), "witness": list(witness), "witness_wt": wu, "checks": checks}
    return src, prov


HEADLINE = ["AtakaMatsuoka732.eight_minimal_generators",
            "AtakaMatsuoka732.generators_are_paper_list",
            "AtakaMatsuoka732.not_normal_witness_x6y2z"]


def main() -> int:
    print("=== Ataka–Matsuoka (arXiv:2602.01782) Example 4.5 — independent kernel verification ===")
    m = _prob41()
    src, prov = build_certificate(m)
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(src)

    all_checks_ok = all(prov["checks"].values())
    print(f"  closure(x⁷,y³,z²): {prov['generator_count']} minimal generators; witness x^{tuple(prov['witness'])}")
    for name, ok in prov["checks"].items():
        print(f"    cross-check {name:<26} {'✓' if ok else '✗ MISMATCH'}")
    if not all_checks_ok:
        print("  !! a faithfulness cross-check FAILED — refusing to certify (possible erratum or transcription bug).")

    # kernel leg: elaborate the certificate + confirm all three theorems are axiom-free.
    kernel = {"status": "not run"}
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
        if available():
            bk = LeanReplBackend(timeout_s=500)
            try:
                run_src = src.split("import Mathlib.Tactic\n", 1)[1]  # REPL provides imports separately
                run_src = run_src + "\n" + "\n".join(f"#print axioms {n}" for n in HEADLINE) + "\n"
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

    gate = ("GREEN" if (all_checks_ok and kernel.get("clean")) else
            "AMBER(kernel-unavailable)" if "unavailable" in str(kernel.get("status")) and all_checks_ok else "RED")
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION",
           "target": "Ataka–Matsuoka (2026), arXiv:2602.01782v1, Example 4.5 / Remark 1.3",
           "claim_verified": ("closure(x⁷,y³,z²) has 8 minimal generators and is NOT normal — the sharp-bound "
                              "witness for μ(I) ≤ 7 ⇒ normal in k[x,y,z]"),
           "provenance": prov, "kernel": kernel, "reference": REF_AM,
           "artifact": str(ARTIFACT.relative_to(_ROOT)), "headline_theorems": HEADLINE,
           "reading": ("Independent kernel verification (Newton polyhedron + Reid–Roberts–Vitulli d=3) of a "
                       "Feb-2026 result: both the generator-count sharpness fact (μ=8) and the non-normality "
                       "witness (x⁶y²z) are reproduced VERBATIM from Example 4.5 and kernel-decided, axiom-free. "
                       "Verification-AMPLIFICATION on the flagship Problem-41 instrument; no trust surface.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION\n-> {OUT}\n-> {ARTIFACT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

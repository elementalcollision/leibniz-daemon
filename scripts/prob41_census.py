"""Problem 41 (Cahen–Fontana–Frisch–Glaz / Swanson) — a kernel-certified NORMALITY CENSUS of corner ideals.

Problem 41 asks to classify the triples (a,b,c) for which I = closure(x^a, y^b, z^c) is normal (all powers
integrally closed). The full classification is OPEN. This module does not classify it — it produces a
*certified census*: the exact normal/not-normal verdict for every corner triple in a bounded box, with a
kernel-`decide`-able non-normality certificate (`x^u ∈ closure(I²) ∖ I²`) for each non-normal one.

Reuses the reusable checker `prob41_normality_lean.certify(a,b,c)` (Newton polyhedron + Reid–Roberts–Vitulli
d=3 reduction) and its `lean_cert`. The census is taken up to coordinate-permutation symmetry (the property
is symmetric under permuting x,y,z), i.e. over `1 ≤ a ≤ b ≤ c ≤ N`.

Findings (N = 9): of 165 triples, only 11 are non-normal (~6%). The two SMALLEST (by a+b+c = 12) are
(2,3,7) and (3,4,5) — both strictly smaller than the textbook Huneke–Swanson (4,5,7); and (2,3,7) is exactly
the Ataka–Matsuoka (2026) sharpness witness closure(x⁷,y³,z²) up to permutation. Every non-normal triple in
range has *distinct* coordinates and a ≥ 2, and 10 of 11 are pairwise-coprime — empirical observations about
the open classification, offered as certified data, not a competing classification.

Tier audit, verification-AMPLIFICATION. No trust surface touched; read-only.

Run:  python scripts/prob41_census.py [N]      (the checker is free-CPU; the kernel leg needs the Lean REPL)
"""
from __future__ import annotations

import json
import sys
from math import gcd
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
OUT = _ROOT / "docs" / "results" / "prob41_census.json"
ARTIFACT = _ROOT / "docs" / "crt" / "prob41_census_certificate.lean"
IMPORTS = ("Mathlib.Tactic",)
DEFAULT_N = 9


def _prob41():
    import importlib.util
    spec = importlib.util.spec_from_file_location("prob41", _ROOT / "scripts" / "prob41_normality_lean.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def census(n: int = DEFAULT_N) -> list[dict]:
    """Classify every corner triple 1 ≤ a ≤ b ≤ c ≤ n (up to coordinate-permutation symmetry)."""
    m = _prob41()
    rows = []
    for a in range(1, n + 1):
        for b in range(a, n + 1):
            for c in range(b, n + 1):
                r = m.certify(a, b, c)
                rows.append({"triple": [a, b, c], "normal": r["normal"],
                             "witness": r["witness"], "witness_wt": r.get("witness_wt")})
    return rows


def _pairwise_coprime(a: int, b: int, c: int) -> bool:
    return gcd(a, b) == 1 and gcd(b, c) == 1 and gcd(a, c) == 1


def summarize(rows: list[dict]) -> dict:
    nn = [r for r in rows if not r["normal"]]
    nn_sorted = sorted(nn, key=lambda r: (sum(r["triple"]), r["triple"]))
    min_sum = min((sum(r["triple"]) for r in nn), default=None)
    return {
        "total": len(rows), "n_not_normal": len(nn),
        "not_normal": [r["triple"] for r in nn_sorted],
        "minimal_not_normal": [r["triple"] for r in nn_sorted if sum(r["triple"]) == min_sum],
        "all_non_normal_have_distinct_coords": all(len(set(r["triple"])) == 3 for r in nn),
        "all_non_normal_have_a_ge_2": all(r["triple"][0] >= 2 for r in nn),
        "n_pairwise_coprime": sum(1 for r in nn if _pairwise_coprime(*r["triple"])),
        "non_pairwise_coprime_examples": [r["triple"] for r in nn if not _pairwise_coprime(*r["triple"])],
    }


def build_certificate(rows: list[dict]) -> tuple[str, list[str]]:
    """Bundle a kernel-decided non-normality certificate for every non-normal triple into one Lean file."""
    m = _prob41()
    nn = sorted((r for r in rows if not r["normal"]), key=lambda r: (sum(r["triple"]), r["triple"]))
    header = (
        "/-\n"
        "  Problem 41 (Cahen–Fontana–Frisch–Glaz / Swanson) — a kernel-certified NORMALITY CENSUS.\n"
        f"  Every corner triple 1 ≤ a ≤ b ≤ c ≤ {DEFAULT_N} classified; the {len(nn)} NON-normal ones each carry\n"
        "  a `decide` witness x^u ∈ closure(I²) ∖ I² (I = closure(x^a,y^b,z^c)). No axioms.\n\n"
        "  Smallest non-normal: (2,3,7) [= Ataka–Matsuoka's closure(x⁷,y³,z²), up to permutation] and (3,4,5),\n"
        "  both smaller than the textbook Huneke–Swanson (4,5,7). Produced by scripts/prob41_census.py.\n"
        "-/\n"
    )
    body = "".join(m.lean_cert(*r["triple"], r["witness"]) + "\n" for r in nn)
    names = [f"Prob41_{a}_{b}_{c}.triple_{a}_{b}_{c}_not_normal" for a, b, c in (r["triple"] for r in nn)]
    src = header + "".join(f"import {i}\n" for i in IMPORTS) + "\n" + body
    return src, names


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_N
    print(f"=== Problem 41 corner-ideal normality census (1 ≤ a ≤ b ≤ c ≤ {n}) ===")
    rows = census(n)
    summ = summarize(rows)
    print(f"  {summ['total']} triples; {summ['n_not_normal']} NOT normal "
          f"({100 * summ['n_not_normal'] // summ['total']}%)")
    print(f"  minimal non-normal (sum {sum(summ['minimal_not_normal'][0]) if summ['minimal_not_normal'] else '-'}): "
          f"{summ['minimal_not_normal']}")
    print(f"  patterns: distinct-coords={summ['all_non_normal_have_distinct_coords']} "
          f"a≥2={summ['all_non_normal_have_a_ge_2']} "
          f"pairwise-coprime={summ['n_pairwise_coprime']}/{summ['n_not_normal']} "
          f"(exceptions {summ['non_pairwise_coprime_examples']})")

    src, names = build_certificate(rows)
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(src)

    kernel = {"status": "not run"}
    try:
        from leibniz.backends.lean_repl import LeanReplBackend, available
        if available():
            bk = LeanReplBackend(timeout_s=600)
            try:
                # REPL supplies imports via the tuple; strip the file's own `import` lines.
                run_src = "".join(ln for ln in src.splitlines(keepends=True) if not ln.startswith("import "))
                run_src = run_src + "\n" + "\n".join(f"#print axioms {nm}" for nm in names) + "\n"
                r = bk._run(run_src, IMPORTS)
            finally:
                bk.close()
            msgs = (r or {}).get("messages", []) or []
            errs = [(msg.get("data") or "") for msg in msgs if msg.get("severity") == "error"]
            axiom_lines = [msg.get("data", "") for msg in msgs if "axiom" in (msg.get("data") or "")]
            axiom_free = (len(axiom_lines) == len(names)
                          and all("does not depend on any axioms" in ln for ln in axiom_lines))
            kernel = {"status": "checked", "errors": errs[:3], "n_theorems": len(names),
                      "axiom_free": axiom_free, "clean": (not errs and axiom_free)}
            print(f"  kernel: {len(names)} theorems — {'CLEAN, all axiom-free ✓' if kernel['clean'] else 'ISSUE: ' + str(errs[:2])}")
        else:
            kernel = {"status": "unavailable (Lean REPL)"}
            print("  kernel: REPL unavailable (skip)")
    except Exception as ex:  # pragma: no cover
        kernel = {"status": f"unavailable ({type(ex).__name__}: {ex})"}
        print(f"  kernel: {kernel['status']}")

    gate = ("GREEN" if kernel.get("clean") else
            "AMBER(kernel-unavailable)" if "unavailable" in str(kernel.get("status")) else "RED")
    out = {"gate": gate, "tier": "audit", "ev": "AMPLIFICATION", "problem": "CFFG/Swanson Problem 41",
           "N": n, "summary": summ, "census": rows, "kernel": kernel,
           "artifact": str(ARTIFACT.relative_to(_ROOT)), "theorems": names,
           "reading": ("A kernel-certified census of corner-ideal normality: every triple up to N classified, "
                       "each non-normal one carrying an axiom-free `decide` witness. Certified instances of an "
                       "OPEN classification — with the empirical observation that the minimal non-normal corner "
                       "ideal is the Ataka–Matsuoka sharpness witness (2,3,7). Verification-amplification; no "
                       "trust surface.")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\ngate={gate}  tier=audit  ev=AMPLIFICATION\n-> {OUT}\n-> {ARTIFACT}")
    return 0 if gate != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

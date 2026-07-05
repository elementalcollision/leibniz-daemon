"""Emit the kernel-attested confirmation of Kaibel & Pokutta's (2026) counterexample to Ziegler's cross-polytope
conjecture as a Codex Calculemus cycle (ADR 0017). New domain: polytope theory / discrete geometry.
Producer only.

Run:  python scripts/export_ziegler_counterexample_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "ziegler_counterexample.lean"

_SUMMARY = (
    "A fresh 2026 result in a domain new to the ledger — polytope theory / discrete geometry — independently "
    "confirmed and re-decided by the Lean kernel. Ziegler proved every simplicial d-dimensional 0/1-polytope "
    "has at most 2d vertices and asked (Question 1.1) whether equality forces central symmetry, i.e. a "
    "0/1-realization of the d-dimensional cross polytope. Kaibel & Pokutta (arXiv:2606.31640) answer NO with an "
    "explicit 14 = 2·7 vertices in {0,1}^7 whose convex hull is a simplicial 7-polytope that is not centrally "
    "symmetric (d=7 is the first dimension where this can occur). Leibniz re-decides the counterexample from "
    "the 14 vertices by exact rational linear algebra — the paper's own method (\"carried out exactly over ℚ\"): "
    "dim P = 7 (rank[1|V]=8); exact facet enumeration finds exactly 136 supporting facets, each an "
    "affinely-independent 6-simplex on 7 of the 14 vertices; the 136 facets form a CLOSED pseudomanifold — "
    "every one of the 476 ridges lies in exactly 2 facets, so (since ∂P is a connected pseudomanifold) the "
    "enumeration is complete and P is simplicial; and P is not centrally symmetric — V is balanced (each "
    "coordinate sums to 7, so the only possible centre is (½,…,½)), yet four vertices lack their cube antipode "
    "1−v. The Lean 4.31 kernel then independently re-decides (plain decide, report-only) the dimension, the "
    "supporting-hyperplane structure (each facet cut out by a hyperplane touching exactly 7 vertices), the "
    "closed-pseudomanifold completeness, and the non-central-symmetry; affine-independence of the 136 facets "
    "(136 nonzero determinants) is carried by the exact-rational leg, exceeding the kernel's decide budget. "
    "Report-only, audit tier — the kernel observes; nothing sets kernel_verified. LLMs propose nothing; exact "
    "linear algebra and the kernel decide."
)

_FINDINGS = [
    {"id": "counterexample",
     "claim": "Ziegler's cross-polytope conjecture (Question 1.1) is FALSE: a simplicial 7-polytope with 14 "
              "vertices that is not centrally symmetric",
     "verdict": "REFUTED",
     "note": "conv of 14 vertices in {0,1}^7: dim 7, exactly 136 facets each a 6-simplex, not centrally "
             "symmetric (balanced but four cube-antipodes absent). d=7 is the first dimension with such an example."},
    {"id": "simplicial-complete",
     "claim": "Simpliciality is certified completely: 136 simplex facets forming a closed pseudomanifold",
     "verdict": "CERTIFIED",
     "note": "Every one of the 476 ridges lies in exactly 2 facets ⇒ the enumeration is complete (∂P connected "
             "pseudomanifold); each facet is affinely independent (nonzero minor). Exact over ℚ."},
    {"id": "kernel-redecided",
     "claim": "The Lean 4.31 kernel independently re-decides the dimension, supporting hyperplanes, "
              "completeness, and non-central-symmetry",
     "verdict": "CERTIFIED",
     "note": "Three plain-decide theorems (no native_decide, no sorry). Affine-independence of the 136 facets "
             "is carried by exact rational arithmetic (exceeds the kernel decide budget)."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000022", kind="lean-proof",
                          checker="Lean 4.31 kernel (plain decide, 3 theorems) + exact-ℚ facet enumeration",
                          result="ziegler_dim_notsym, ziegler_supporting, ziegler_closed accepted; exact-ℚ: dim "
                                 "7, 136 simplex facets, 476 ridges each in 2 facets, not centrally symmetric"),
]

_REFERENCES = [
    {"citation": ("Kaibel, V., & Pokutta, S. (2026). A counterexample to Ziegler's cross-polytope conjecture "
                  "for simplicial 0/1-polytopes (arXiv:2606.31640). arXiv."),
     "url": "https://arxiv.org/abs/2606.31640"},
    {"citation": ("Ziegler, G. M. (2000). Lectures on 0/1-polytopes. In Polytopes — Combinatorics and "
                  "Computation (DMV Seminar, Vol. 29, pp. 1–41). Birkhäuser Basel."),
     "url": "https://doi.org/10.1007/978-3-0348-8438-9_1"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (Ziegler counterexample)",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/ziegler_counterexample.lean + scripts/verify_ziegler_counterexample.py (exact-ℚ facet "
             "enumeration + closed-pseudomanifold completeness + Lean 4.31 decide)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=22, date="2026-07-05", domain="Discrete geometry", kind="refutation",
        title="Kernel-attested counterexample to Ziegler's cross-polytope conjecture for simplicial 0/1-polytopes (Kaibel–Pokutta 2026)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_ziegler_counterexample_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/ziegler_counterexample.lean to public/artifacts/cycle_000022/."},
            "cycles": [build_cycle()]}


def main(argv: list[str]) -> int:
    stamp = (argv[argv.index("--generated-at") + 1] if "--generated-at" in argv
             else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    text = json.dumps(build_fragment(generated_at=stamp), indent=2, ensure_ascii=False) + "\n"
    if "-o" in argv:
        Path(argv[argv.index("-o") + 1]).write_text(text)
        print(f"wrote (target: {_TARGET})")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

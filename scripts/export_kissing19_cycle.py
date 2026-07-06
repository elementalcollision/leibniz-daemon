"""Emit the kernel-attested record kissing bound k(19) >= 11948 (Boon Suan Ho 2026) as a Codex Calculemus cycle
(ADR 0017). New domain: sphere packing / kissing numbers. Producer only.

Run:  python scripts/export_kissing19_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "kissing19.lean"

_SUMMARY = (
    "A current record in a domain new to the ledger — sphere packing / kissing numbers — independently "
    "reconstructed and kernel-attested. The kissing number k(n) is the maximum number of unit spheres touching a "
    "central one in n dimensions. Boon Suan Ho (arXiv:2603.10425, 2026) proves k(19) >= 11948, improving the "
    "Cohn-Li bound k(19) >= 11692 by 256 — the best known. By the Cohn-Li odd-sign construction, k(19) >= 10668 "
    "+ |A| for any length-19 binary code A of minimum distance >= 5 inside a fixed 5-punctured extended binary "
    "Golay code D; Cohn-Li used |A|=1024, Ho constructs a nonlinear |A|=1280. The construction is fully explicit: "
    "with coordinates as 19-bit masks (addition = symmetric difference), D = span(m1..m6,s1..s4,r1,r2) (dim 12, "
    "|D|=4096), M = span(m1..m6) (dim 6), K = span(M,s1..s4) (dim 10), B = (s1+M)∪..∪(s5+M) (|B|=320), and "
    "A = B∪(B+r1)∪(B+r2)∪(B+r1+r2) (|A|=1280). Leibniz reconstructs A from these generators (no 726KB data file) "
    "and verifies by exact bit arithmetic: dim M/K/D = 6/10/12, |A|=1280, A ⊆ D, the identity "
    "s5=s1+s2+s3+s4+m4+m6, that D has minimum weight 3 and its 21 weight-3/4 words are exactly the paper's "
    "Table 1 (a faithfulness anchor that caught one transcription error in reading the table), and that A has "
    "minimum distance exactly 5 — two independent ways: the full 818560-pair census and the forbidden-difference "
    "test — hence k(19) >= 10668 + 1280 = 11948. The Lean 4.31 kernel re-decides the finite core with everything "
    "rebuilt inside the kernel (D regenerated from the 12 generators by subset-XOR; A-membership via a balanced "
    "binary search tree): the bound, |A|=1280 distinct, A ⊆ D by parity check, the forbidden set complete "
    "(weight-3/4 words of the rebuilt D), the minimum-distance test, and a discriminating negative control — all "
    "plain decide; #print axioms at most [propext]; no native_decide, no sorry. Report-only, audit tier — the "
    "kernel observes; nothing sets kernel_verified. LLMs propose nothing; exact bit arithmetic and the kernel decide."
)

_FINDINGS = [
    {"id": "record-bound", "claim": "k(19) >= 11948 — the current record kissing number lower bound in 19 "
                                    "dimensions (improving Cohn-Li by 256)",
     "verdict": "CERTIFIED",
     "note": "By the Cohn-Li odd-sign construction k(19) >= 10668 + |A|; the explicit code A has |A| = 1280 and "
             "minimum distance 5 inside a 5-punctured extended Golay code, giving 10668 + 1280 = 11948."},
    {"id": "code-min-dist-5", "claim": "The 1280-word code A is contained in D and has minimum distance 5",
     "verdict": "CERTIFIED",
     "note": "Reconstructed from the generators; A ⊆ D (parity check) and minimum distance is exactly 5 — the "
             "full 818560-pair census and the forbidden-difference test (no two codewords differ by a weight-3/4 "
             "word of D) agree. The 21 forbidden words are certified to be all weight-3/4 words of the rebuilt D."},
    {"id": "table1-faithful", "claim": "The paper's Table 1 (21 weight-3/4 words) matches the exact set",
     "verdict": "CERTIFIED",
     "note": "The weight-3/4 words of D computed from the generators equal the paper's Table 1 — the exact "
             "computation caught and corrected one transcription error (a coordinate 19 that should be 15)."},
    {"id": "kernel", "claim": "Lean 4.31 re-decides the finite core (bound, subset, distinctness, forbidden "
                              "completeness, minimum distance, negative control)",
     "verdict": "CERTIFIED",
     "note": "Everything rebuilt inside the kernel (D by subset-XOR; A-membership via a balanced BST). Six "
             "plain-decide theorems; #print axioms at most [propext] — no native_decide, no sorry, no sorryAx."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000031", kind="lean-proof",
                          checker="Lean 4.31 kernel (plain decide, 6 theorems) + exact bit arithmetic",
                          result="kissing_bound / distinct / subset_D / forbidden_complete / mindist / negcontrol "
                                 "accepted: A ⊆ D, |A|=1280, min distance >= 5 => k(19) >= 11948; #print axioms "
                                 "at most [propext]"),
]

_REFERENCES = [
    {"citation": ("Ho, B. S. (2026). A new lower bound for the kissing number in 19 dimensions "
                  "(arXiv:2603.10425)."),
     "url": "https://arxiv.org/abs/2603.10425"},
    {"citation": ("Cohn, H., & Li, Y. (2024). Kissing numbers and error-correcting codes (the odd-sign "
                  "construction; the k(19) >= 11692 bound improved here)."),
     "url": ""},
    {"citation": ("Conway, J. H., & Sloane, N. J. A. (1999). Sphere Packings, Lattices and Groups (3rd ed.). "
                  "Springer."),
     "url": "https://doi.org/10.1007/978-1-4757-6568-7"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (kissing k(19) >= 11948)",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/kissing19.lean + scripts/verify_kissing19.py (reconstruct the 1280-word min-distance-5 "
             "code from generators; exact bit arithmetic + Lean 4.31 decide, balanced-BST minimum distance)"},
    {"name": "boonsuan/kissing",
     "url": "https://github.com/boonsuan/kissing",
     "role": "source",
     "note": "the author's data (data/dimension19_11948.txt, data/paper_construction.json) and verification "
             "scripts; Leibniz reconstructs the code independently from the paper's generators."},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=31, date="2026-07-06", domain="Sphere packing (kissing numbers)", kind="verification",
        title="Kernel-attested record kissing-number bound k(19) ≥ 11948 (Boon Suan Ho 2026)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_kissing19_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/kissing19.lean to public/artifacts/cycle_000031/."},
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

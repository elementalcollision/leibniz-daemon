"""Emit the kernel-attested complex Hadamard matrix of order 94 (Szollosi 2026) as a Codex Calculemus cycle
(ADR 0017). New domain: complex Hadamard matrices / combinatorial designs. Producer only.

Run:  python scripts/export_hadamard94_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "hadamard94.lean"

_SUMMARY = (
    "A 2026 existence resolution in a domain new to the ledger — complex Hadamard matrices — independently "
    "reconstructed and kernel-attested. A complex Hadamard matrix of order n is an n x n matrix with entries in "
    "{1,-1,i,-i} and H H* = n I; whether one exists in order 94 was open. Szollosi (arXiv:2603.09572) settles it "
    "(Theorem 1) by a Goethals-Seidel-style construction: four circulant {-1,1}-matrices A,B,C,D of order 47, "
    "with A,B symmetric and A A^T+B B^T+C C^T+D D^T = 188 I, assemble (with R the back-diagonal) into a complex "
    "Hadamard matrix of order 94. The hard part is the computer search for the four sequences; verification is "
    "exact and self-certifying (the search is not part of the certificate). Leibniz reconstructs A,B,C,D from the "
    "length-47 rows printed in the paper — both Example 1 and, independently, Example 2 — and verifies by exact "
    "integer arithmetic: the published anchors (row sums 3,7,7,9 / -1,-5,9,9 and summed autocorrelation norm 796 "
    "/ 1116, peaks 14 / 18), that A,B are symmetric, that A A^T+B B^T+C C^T+D D^T = 188 I, and that the assembled "
    "94x94 matrix is unimodular in {1,-1,i,-i} and satisfies H H* = 94 I — i.e. a complex Hadamard matrix of "
    "order 94 (both examples). The Lean 4.31 kernel re-decides the finite structural core by plain decide: eq (1) "
    "written as the vanishing of the summed periodic autocorrelations at every nonzero shift (equivalent, since "
    "the four Gram matrices are circulant, and far cheaper than the dense 188x188 product) plus the symmetry of "
    "A,B — exactly the hypotheses Theorem 4 turns into the order-94 matrix — for both examples, with a negative "
    "control (one flipped sign breaks eq (1)); every theorem depends on at most [propext]. The dense 94x94 "
    "H H* = 94 I is carried by the exact integer procedure. Report-only, audit tier — the kernel observes; "
    "nothing sets kernel_verified. LLMs propose nothing; exact integer arithmetic and the kernel decide."
)

_FINDINGS = [
    {"id": "exists-order-94", "claim": "A complex Hadamard matrix of order 94 exists (previously open)",
     "verdict": "CERTIFIED",
     "note": "Reconstructed from the paper's length-47 sequences; the assembled 94x94 matrix is unimodular in "
             "{1,-1,i,-i} and satisfies H H* = 94 I, verified directly by exact integer arithmetic for both of "
             "the paper's examples."},
    {"id": "eq1", "claim": "The four circulant {-1,1}-matrices satisfy A A^T+B B^T+C C^T+D D^T = 188 I",
     "verdict": "CERTIFIED",
     "note": "Verified as the vanishing of the summed periodic autocorrelations of A,B,C,D at every nonzero shift "
             "(equal to 188 at shift 0) — equivalent to eq (1) because each Gram matrix is circulant. A,B are "
             "symmetric, as Theorem 4 requires."},
    {"id": "faithful", "claim": "The transcription matches the paper's published invariants",
     "verdict": "CERTIFIED",
     "note": "Row sums (3,7,7,9 / -1,-5,9,9) and the summed autocorrelation norm ||Sigma|| (796 / 1116, peaks 14 "
             "/ 18) reproduce the paper exactly, for both examples — a faithfulness anchor on the reconstruction."},
    {"id": "kernel", "claim": "Lean 4.31 re-decides eq (1) + symmetry for both examples, plus a negative control",
     "verdict": "CERTIFIED",
     "note": "had94_eq1_{example1,example2} (autocorrelations vanish), had94_sym_{example1,example2} (A,B "
             "symmetric), had94_control (a flipped sign makes eq (1) false). #print axioms: at most [propext]; no "
             "native_decide, no sorry."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000032", kind="lean-proof",
                          checker="Lean 4.31 kernel (plain decide, 5 theorems) + exact integer arithmetic",
                          result="had94_eq1/sym accepted for both examples (eq (1) = 188 I via vanishing "
                                 "autocorrelations; A,B symmetric), control rejects a flipped sign; assembled "
                                 "H H* = 94 I confirmed by exact procedure; #print axioms at most [propext]"),
]

_REFERENCES = [
    {"citation": ("Szollosi, F. (2026). A complex Hadamard matrix of order 94 (arXiv:2603.09572)."),
     "url": "https://arxiv.org/abs/2603.09572"},
    {"citation": ("Goethals, J. M., & Seidel, J. J. (1970). A skew Hadamard matrix of order 36. Journal of the "
                  "Australian Mathematical Society, 11, 343-344."),
     "url": "https://doi.org/10.1017/S1446788700006674"},
    {"citation": ("Kharaghani, H., & Seberry, J. (1993). The excess of complex Hadamard matrices. Graphs and "
                  "Combinatorics, 9, 47-56."),
     "url": "https://doi.org/10.1007/BF01195325"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (complex Hadamard matrix of order 94)",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/hadamard94.lean + scripts/verify_hadamard94.py (reconstruct the four circulants; exact "
             "integer eq (1) = 188 I + assembled H H* = 94 I; Lean 4.31 decide of eq (1) via autocorrelations)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=32, date="2026-07-06", domain="Complex Hadamard matrices", kind="verification",
        title="Kernel-attested complex Hadamard matrix of order 94 (Szöllősi 2026)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_hadamard94_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/hadamard94.lean to public/artifacts/cycle_000032/."},
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

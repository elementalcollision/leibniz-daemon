"""Emit the order-1252 skew-Hadamard difference-family verification (Karoui 2026) as a Codex Calculemus cycle
(ADR 0017). A verification cycle: Leibniz independently confirms, by exact finite-field arithmetic, the
difference-family prerequisites behind a freshly-published Hadamard-table gap-filler. Producer only.

Run:  python scripts/export_skew_hadamard_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_VERIFIER = _ROOT / "scripts" / "verify_skew_hadamard_1252.py"

_SUMMARY = (
    "An independent, exact verification of the core of a Feb-2026 construction that fills a reported-missing "
    "Hadamard order. Karoui (2026, 'An explicit skew-Hadamard matrix of order 1252 via cyclotomic unions', "
    "arXiv:2602.16089, submitted to the Journal of Combinatorial Designs) constructs a skew-Hadamard matrix of "
    "order 1252 = 2(5⁴+1) — an order reported missing in widely-used open-source Hadamard tables — by a "
    "bordered Goethals–Seidel array over a bordered skew-Hadamard difference family (SHDF) {D₀,D₁} in the "
    "additive group of GF(5⁴), whose blocks are unions of cyclotomic classes of order 16. The paper reduces "
    "'the array is skew-Hadamard' to two structural prerequisites on {D₀,D₁} (its Lemma 1, after Colbourn & "
    "Dinitz 2006 and Momihara & Xiang 2018). Leibniz builds GF(5⁴) from scratch — an irreducible primitive "
    "quartic over GF(5), so x is a primitive element — forms the order-16 cyclotomic classes, and checks BOTH "
    "prerequisites exactly: (S) D₀ is skew (for every x≠0 exactly one of x, −x lies in D₀, so |D₀|=|D₁|=312), "
    "forced because −1 = g³¹² ∈ C₈; and (A) the ±1 autocorrelations sum to a constant, A_{D₀}(w)+A_{D₁}(w) = "
    "−2 for ALL 624 nonzero w. Given (S)+(A) a skew-Hadamard matrix of order 1252 EXISTS by Goethals–Seidel — "
    "the paper's headline claim, independently confirmed. Our fresh primitive element realizes the paper's "
    "exact index sets I₀={4..11}, I₁={0..7} at cyclic offset 0. All arithmetic is exact (finite-field, no "
    "floating point); LLMs propose nothing, the exact procedure decides. Honest scope: this certifies the "
    "difference-family prerequisites the paper proves — the mathematically load-bearing core — not the explicit "
    "1252×1252 matrix or its GF(2)/GF(3)/GF(5) rank invariants, which need the paper's array / artifact bundle."
)

_FINDINGS = [
    {"id": "shdf", "claim": "The bordered skew-Hadamard difference family {D₀,D₁} over GF(5⁴) is valid",
     "verdict": "CERTIFIED",
     "note": "Exactly, over a from-scratch GF(5⁴): (S) D₀ skew, |D₀|=|D₁|=312; (A) A_{D₀}(w)+A_{D₁}(w) = −2 "
             "for all 624 nonzero w. So a skew-Hadamard matrix of order 1252 exists by Goethals–Seidel."},
    {"id": "match", "claim": "The independent build matches the paper's exact cyclotomic index sets",
     "verdict": "CERTIFIED",
     "note": "Our fresh primitive element realizes I₀={4,5,6,7,8,9,10,11}, I₁={0,1,2,3,4,5,6,7} at cyclic "
             "offset 0 — the paper's construction, reproduced."},
    {"id": "scope", "claim": "The difference-family core, not the explicit matrix or rank invariants",
     "verdict": "NOTED",
     "note": "The paper's Lemma-1 prerequisites (from which the order-1252 matrix follows) are certified; the "
             "explicit 1252×1252 matrix and its finite-field ranks need the paper's array / artifact bundle."},
]

_ARTIFACTS = [
    downloadable_artifact(_VERIFIER, cycle_id="cycle_000018", kind="exact-verifier",
                          checker="exact GF(5⁴) finite-field arithmetic (Python stdlib, no floating point)",
                          result="SHDF prerequisites (S) skew + (A) autocorrelation-sum −2 over all 624 nonzero "
                                 "w verified; index sets match the paper at offset 0"),
]

_REFERENCES = [
    {"citation": ("Karoui, A. (2026). An explicit skew-Hadamard matrix of order 1252 via cyclotomic unions "
                  "(arXiv:2602.16089). arXiv. [Submitted to the Journal of Combinatorial Designs.]"),
     "url": "https://arxiv.org/abs/2602.16089"},
    {"citation": ("Colbourn, C. J., & Dinitz, J. H. (Eds.). (2006). Handbook of Combinatorial Designs "
                  "(2nd ed.). Chapman & Hall/CRC."), "url": ""},
    {"citation": ("Momihara, K., & Xiang, Q. (2018). Skew Hadamard difference sets and related combinatorial "
                  "objects. In Combinatorics and Finite Fields. De Gruyter."), "url": ""},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon #300",
     "url": "https://github.com/elementalcollision/leibniz-daemon/pull/300",
     "role": "produced",
     "note": "scripts/verify_skew_hadamard_1252.py + tests/test_skew_hadamard_1252.py (exact GF(5⁴) instrument)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=18, date="2026-07-05", domain="Combinatorial design theory", kind="verification",
        title="Independent verification of the skew-Hadamard difference family behind the order-1252 matrix (Karoui 2026)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_skew_hadamard_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy scripts/verify_skew_hadamard_1252.py to public/artifacts/cycle_000018/."},
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

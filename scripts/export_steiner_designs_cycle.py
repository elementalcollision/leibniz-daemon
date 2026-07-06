"""Emit the kernel-attested existence of Steiner systems S(2,8,225) and S(2,9,289) (Hetman 2026) as a Codex
Calculemus cycle (ADR 0017). New domain: design theory. Producer only.

Run:  python scripts/export_steiner_designs_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "steiner_designs.lean"

_SUMMARY = (
    "A fresh 2026 result in a domain new to the ledger — design theory / explicit incidence structures — "
    "independently confirmed and kernel-decided. A Steiner system S(2,k,v) is a set of v points with a family "
    "of k-blocks such that every pair of points lies in exactly one block; the Handbook of Combinatorial "
    "Designs lists 129 undecided existence cases for block lengths 8 and 9. Hetman (arXiv:2509.10673, accepted "
    "J. Combinatorial Designs) resolves two of them — S(2,8,225) and S(2,9,289) exist — by exhibiting explicit "
    "difference families: six S(2,8,225) (two in ℤ₃×ℤ₃×ℤ₅×ℤ₅, four in ℤ₅×ℤ₅×ℤ₉) and four S(2,9,289) in "
    "ℤ₁₇×ℤ₁₇. Leibniz re-decides existence from the base blocks (read directly from the paper) by exact "
    "finite-group arithmetic, with two independent complete checks. (1) DIFFERENCE FAMILY: for all ten systems, "
    "the nonzero differences b−b′ within the base blocks hit every nonzero group element exactly once "
    "(224 = 225−1 differences for the size-8 systems; 288 = 289−1 for the size-9 ones) — a (v,k,1)-difference "
    "family, the standard sufficient condition for the development to be a Steiner 2-design, and self-validating "
    "against transcription since one wrong point breaks the exact cover. (2) DIRECT DEVELOPMENT: for a "
    "representative of each parameter set, translating each base block by every group element yields v·4 blocks "
    "(900 / 1156) and Leibniz checks directly that every one of the C(225,2)=25200 / C(289,2)=41616 pairs lies "
    "in exactly one block — the definition of a Steiner system, no theorem cited. The Lean 4.31 kernel then "
    "independently decides the difference-family property (differences pairwise distinct, all nonzero, count "
    "v−1) for one marquee system of each parameter set (plain decide; #print axioms = propext only; no "
    "native_decide, no sorry). Report-only, audit tier — the kernel observes; nothing sets kernel_verified. "
    "LLMs propose nothing; exact finite-group arithmetic and the kernel decide."
)

_FINDINGS = [
    {"id": "s8-225", "claim": "Steiner systems S(2,8,225) exist (resolving an undecided Handbook case)",
     "verdict": "CERTIFIED",
     "note": "Six explicit difference families (two in ℤ₃×ℤ₃×ℤ₅×ℤ₅, four in ℤ₅×ℤ₅×ℤ₉); each 4 base blocks of "
             "size 8 with 224 differences covering every nonzero group element once, developing to a 2-(225,8,1) "
             "design (25200 pairs each once)."},
    {"id": "s9-289", "claim": "Steiner systems S(2,9,289) exist (resolving an undecided Handbook case)",
     "verdict": "CERTIFIED",
     "note": "Four explicit difference families in ℤ₁₇×ℤ₁₇; each 4 base blocks of size 9 with 288 differences "
             "covering every nonzero element once, developing to a 2-(289,9,1) design (41616 pairs each once)."},
    {"id": "two-checks", "claim": "Verified two independent ways: difference family + direct pair-coverage",
     "verdict": "CERTIFIED",
     "note": "All ten families pass the (v,k,1)-difference test (self-validating vs transcription); a "
             "representative of each parameter set is confirmed Steiner by developing all v·4 blocks and "
             "checking every pair is covered exactly once."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000026", kind="lean-proof",
                          checker="Lean 4.31 kernel (plain decide, 2 theorems) + exact finite-group arithmetic",
                          result="steiner_S8_225 + steiner_S9_289 accepted: 224 / 288 base-block differences "
                                 "distinct, nonzero, and = v−1 (hence all nonzero elements once); #print axioms "
                                 "= [propext]"),
]

_REFERENCES = [
    {"citation": ("Hetman, I. (2026). There exist Steiner systems S(2,8,225) and S(2,9,289) (arXiv:2509.10673). "
                  "arXiv / Journal of Combinatorial Designs."),
     "url": "https://arxiv.org/abs/2509.10673"},
    {"citation": ("Colbourn, C. J., & Dinitz, J. H. (Eds.). (2007). Handbook of Combinatorial Designs (2nd ed.). "
                  "CRC Press."),
     "url": "https://www.routledge.com/9781584885061"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (Steiner S(2,8,225) & S(2,9,289))",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/steiner_designs.lean + scripts/verify_steiner_designs.py (exact finite-group "
             "difference-family + direct pair-coverage + Lean 4.31 decide)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=26, date="2026-07-05", domain="Design theory", kind="verification",
        title="Kernel-attested existence of Steiner systems S(2,8,225) and S(2,9,289) (two undecided Handbook cases; Hetman 2026)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_steiner_designs_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/steiner_designs.lean to public/artifacts/cycle_000026/."},
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

"""Emit the Problem 41 normality-census cycle for Codex Calculemus (ADR 0017).

A certification cycle: a kernel-certified census of corner-ideal normality (CFFG/Swanson Problem 41). Carries
no `kernel_verified` edge, mints nothing, promulgates nothing — the `decide` results are *reported* checks by
the Lean 4.31 kernel. Producer only; the operator commits the fragment to `elementalcollision/codex-calculemus`
and copies the `.lean` cert to `public/artifacts/`.

Run:  python scripts/export_prob41_census_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "prob41_census_certificate.lean"

_SUMMARY = (
    "Cahen–Fontana–Frisch–Glaz Problem 41 (Swanson) asks to classify the triples (a,b,c) for which "
    "I = the integral closure of (x^a,y^b,z^c) in k[x,y,z] is normal (every power integrally closed). The full "
    "classification is open. This is not a classification — it is a certified census: the exact normal / "
    "not-normal verdict for every corner triple with 1 ≤ a ≤ b ≤ c ≤ 9 (taken up to coordinate-permutation "
    "symmetry), each non-normal one carrying an axiom-free Lean `decide` witness x^u in closure(I²) minus I². "
    "Of 165 triples, 11 are not normal; all 11 non-normality certificates are kernel-verified with no axiom "
    "dependencies at all. The headline observation: the two smallest non-normal corner ideals, by a+b+c = 12, "
    "are (2,3,7) and (3,4,5) — both strictly smaller than the textbook Huneke–Swanson (4,5,7); and (2,3,7) is "
    "exactly the Ataka–Matsuoka (2026) sharpness witness, the integral closure of (x⁷,y³,z²), up to "
    "permutation. So the sharpest generator-count counterexample in their paper is simultaneously the minimal "
    "non-normal corner ideal — two extremal characterizations meeting at one ideal. Within the census range "
    "every non-normal triple has distinct coordinates and a ≥ 2, and 10 of the 11 are pairwise-coprime (the "
    "sole exception is (5,6,8)); these are honest observations about the open classification, offered as "
    "certified data, not a competing classification. LLMs propose nothing; the Lean kernel decides."
)

_FINDINGS = [
    {"id": "census", "claim": "Every corner triple 1 ≤ a ≤ b ≤ c ≤ 9 classified; 11 of 165 are not normal",
     "verdict": "CERTIFIED",
     "note": "Non-normal: (2,3,7) (3,4,5) (2,5,7) (3,5,8) (4,5,7) (3,7,8) (5,6,7) (5,6,8) (5,7,9) (5,8,9) "
             "(7,8,9). All 11 kernel-decided (x^u ∈ closure(I²) ∖ I²), #print axioms = does not depend on any "
             "axioms."},
    {"id": "minimal", "claim": "The minimal non-normal corner ideal is the Ataka–Matsuoka sharpness witness",
     "verdict": "OBSERVED",
     "note": "The two smallest non-normal triples (a+b+c=12) are (2,3,7) and (3,4,5), both smaller than "
             "(4,5,7); (2,3,7) = closure(x⁷,y³,z²) up to permutation, the sharp μ(I) ≤ 7 witness (Cycle 8)."},
    {"id": "patterns", "claim": "Empirical structure of the non-normal set (in range)", "verdict": "OBSERVED",
     "note": "Every non-normal triple has distinct coordinates and a ≥ 2; 10 of 11 are pairwise-coprime "
             "(exception (5,6,8)). Certified data about the open classification, not theorems."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000010", kind="lean-proof",
                          checker="Lean 4.31 kernel (decide)",
                          result="11 non-normality theorems decided; #print axioms = does not depend on any axioms"),
]

_REFERENCES = [
    {"citation": ("Cahen, P.-J., Fontana, M., Frisch, S., & Glaz, S. (2014). Open problems in commutative "
                  "ring theory. In M. Fontana, S. Frisch, & S. Glaz (Eds.), Commutative algebra (pp. "
                  "353–375). Springer."), "url": ""},
    {"citation": ("Huneke, C., & Swanson, I. (2006). Integral closure of ideals, rings, and modules "
                  "(London Mathematical Society Lecture Note Series No. 336). Cambridge University Press."),
     "url": ""},
    {"citation": ("Reid, L., Roberts, L. G., & Vitulli, M. A. (2003). Some results on normal homogeneous "
                  "ideals. Communications in Algebra, 31(9), 4485–4506."), "url": ""},
    {"citation": ("Ataka, M., & Matsuoka, N. (2026). Normality of monomial ideals in three variables "
                  "(arXiv:2602.01782). arXiv."), "url": "https://arxiv.org/abs/2602.01782"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon #289",
     "url": "https://github.com/elementalcollision/leibniz-daemon/pull/289",
     "role": "produced",
     "note": "scripts/prob41_census.py + docs/crt/prob41_census_certificate.lean"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=10,
        date="2026-07-04",
        domain="Commutative ring theory",
        kind="certification",
        title=("A kernel-certified normality census of corner ideals (Problem 41) — the minimal non-normal "
               "triple is the Ataka–Matsuoka witness"),
        summary=_SUMMARY,
        findings=_FINDINGS,
        artifacts=_ARTIFACTS,
        references=_REFERENCES,
        repositories=_REPOSITORIES,
    )


def build_fragment(*, generated_at: str = "") -> dict:
    return {
        "meta": {
            "generated_at": generated_at,
            "producer": "scripts/export_prob41_census_cycle.py",
            "target": _TARGET,
            "merge": "append the object in `cycles` to the site ledger's top-level `cycles` array; also copy "
                     "docs/crt/prob41_census_certificate.lean to public/artifacts/cycle_000010/.",
        },
        "cycles": [build_cycle()],
    }


def main(argv: list[str]) -> int:
    stamp = (argv[argv.index("--generated-at") + 1] if "--generated-at" in argv
             else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    fragment = build_fragment(generated_at=stamp)
    text = json.dumps(fragment, indent=2, ensure_ascii=False) + "\n"
    if "-o" in argv:
        out = Path(argv[argv.index("-o") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        print(f"wrote {out}  (target: {_TARGET})")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

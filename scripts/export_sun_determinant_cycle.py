"""Emit the kernel-attested confirmation of Zhang & Yang's (2026) proof of Sun's determinant congruence as a
Codex Calculemus cycle (ADR 0017). New domain: determinantal number theory. Producer only.

Run:  python scripts/export_sun_determinant_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "sun_determinant.lean"

_SUMMARY = (
    "A fresh 2026 result in a domain new to the ledger — determinantal number theory / binary quadratic forms "
    "— independently confirmed and kernel-decided. For c,d ∈ ℤ and n ≥ 2 let Dₙ(c,d) = "
    "det[(i²+cij+dj²)^{n−2}]₀≤i,j≤n−1, an n×n integer determinant. Zhang & Yang (arXiv:2605.19486, accepted "
    "Bull. Aust. Math. Soc.) prove, in strengthened form, a conjecture of Zhi-Wei Sun: for composite n, "
    "n² | Dₙ(c,d) for ALL c,d; for prime n=p, p² | Dₚ(c,d) whenever the Legendre symbol (d/p) = −1. Leibniz "
    "re-decides this on a census of instances by EXACT integer linear algebra (the matrix reconstructed "
    "directly from the formula, no external data). It forms the exact integer determinant (fraction-free "
    "Bareiss) and confirms: n² | Dₙ for every composite n in {4,6,8,9,10,12} and all small c,d; and prime "
    "sufficiency — for p in {5,7,11,13}, p² | Dₚ at every quadratic non-residue d (all c). It also records a "
    "SHARPNESS witness: for each prime there is a quadratic residue d "
    "with p² ∤ Dₚ (e.g. p=5, d=1), so the Legendre condition is not vacuous. The Lean 4.31 kernel then "
    "independently re-decides several small instances (plain decide, report-only): from the explicit integer "
    "matrix it computes the determinant by cofactor expansion and checks divisibility by n² — for D₄(1,2), "
    "D₆(1,2), D₅(1,2) with (2/5)=−1, and D₇(1,3) with (3/7)=−1; #print axioms = propext only, no native_decide, "
    "no sorry. Report-only, audit tier — the kernel observes; nothing sets kernel_verified. LLMs propose "
    "nothing; exact integer arithmetic and the kernel decide."
)

_FINDINGS = [
    {"id": "composite", "claim": "n² | Dₙ(c,d) for composite n (Sun's congruence, composite case)",
     "verdict": "CERTIFIED",
     "note": "Verified for every composite n in {4,6,8,9,10,12} and all c in {−2..2}, d in {1..6} by exact "
             "integer determinant + divisibility."},
    {"id": "prime", "claim": "p² | Dₚ(c,d) when (d/p) = −1 (prime case, sufficiency)", "verdict": "CERTIFIED",
     "note": "Verified for p in {5,7,11,13} at every quadratic non-residue d and all c in {−2..2}."},
    {"id": "sharpness", "claim": "The Legendre condition is sharp: p² can fail to divide Dₚ at residues",
     "verdict": "NOTED",
     "note": "For each tested prime a quadratic residue d exists with p² ∤ Dₚ (e.g. p=5, d=1 gives v_p=1), so "
             "the (d/p)=−1 hypothesis is not vacuous."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000027", kind="lean-proof",
                          checker="Lean 4.31 kernel (plain decide, 4 theorems) + exact integer determinant",
                          result="sun_comp_n4_c1_d2 (16|D₄), sun_comp_n6_c1_d2 (36|D₆), sun_prime_p5_c1_d2 "
                                 "(25|D₅), sun_prime_p7_c1_d3 (49|D₇) accepted; #print axioms = [propext]"),
]

_REFERENCES = [
    {"citation": ("Zhang, Y., & Yang, Y. (2026). A determinant congruence conjectured by Sun (arXiv:2605.19486). "
                  "arXiv / Bulletin of the Australian Mathematical Society."),
     "url": "https://arxiv.org/abs/2605.19486"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (Sun determinant congruence)",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/sun_determinant.lean + scripts/verify_sun_determinant.py (exact integer determinant "
             "census + Lean 4.31 decide)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=27, date="2026-07-05", domain="Number theory", kind="verification",
        title="Kernel-attested confirmation of Sun's determinant congruence for binary quadratic forms (Zhang–Yang 2026)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_sun_determinant_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/sun_determinant.lean to public/artifacts/cycle_000027/."},
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

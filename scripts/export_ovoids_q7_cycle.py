"""Emit the kernel-attested low-degree ovoids of Q+(7,q) (Bartoli-Durante-Grimaldi-Timpanella 2025) as a Codex
Calculemus cycle (ADR 0017). New domain: finite geometry / ovoids of polar spaces. Producer only.

Run:  python scripts/export_ovoids_q7_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "ovoids_q7.lean"

_SUMMARY = (
    "A 2025 finite-geometry result in a domain new to the ledger — ovoids of polar spaces — independently "
    "re-decided with a positive AND a printed negative from the same source. An ovoid of the hyperbolic quadric "
    "Q+(7,q) is a set of q^3+1 pairwise non-collinear points, parametrized by three functions f1,f2,f3 in "
    "F_q[x,y,z]. Bartoli, Durante, Grimaldi & Timpanella (arXiv:2502.02219) study the low-degree case: the Kantor "
    "ovoid (q=2^h) is given, for q in {2,4,16}, by f1=xy+z^2, f2=xz+y^2+z^2, f3=yz+x^2+y^2+z^2, and at q=8 these "
    "same functions do NOT define an ovoid. O7(f1,f2,f3) is an ovoid iff Condition (3): for all distinct P1,P2 in "
    "F_q^3, F=(x1-x2)(f3(P2)-f3(P1))+(y1-y2)(f2(P2)-f2(P1))+(z1-z2)(f1(P2)-f1(P1)) != 0. Leibniz re-decides "
    "Condition (3) by exact GF(2^h) arithmetic (field F_2[X]/(irreducible); char 2 so add=sub=XOR): q=2 and q=4 "
    "are ovoids (all distinct pairs F!=0; 4032 ordered pairs for q=4), q=16 likewise (16.7M-pair census), and "
    "q=8 is NOT an ovoid — the explicit distinct pair (0,0,0),(0,1,3) has F=0. The Lean 4.31 kernel re-decides "
    "Condition (3) for q=2 and q=4 and the q=8 witness, with GF(2^h) multiplication computed in-kernel from the "
    "irreducible polynomial; #print axioms at most [propext]; no native_decide, no sorry. Report-only, audit tier "
    "— the kernel observes; nothing sets kernel_verified. LLMs propose nothing; exact finite-field arithmetic and "
    "the kernel decide."
)

_FINDINGS = [
    {"id": "ovoid-q4", "claim": "The Kantor functions define an ovoid of Q+(7,4) (and Q+(7,2), Q+(7,16))",
     "verdict": "CERTIFIED",
     "note": "Condition (3) holds: every one of the 4032 ordered distinct pairs of F_4^3 has F != 0 (and "
             "similarly for q=2 and q=16), by exact GF(2^h) arithmetic."},
    {"id": "not-ovoid-q8", "claim": "At q=8 the same functions do NOT define an ovoid",
     "verdict": "CERTIFIED",
     "note": "The explicit distinct pair (0,0,0),(0,1,3) in F_8^3 has F=0, so Condition (3) fails — a printed "
             "negative from the same source, a built-in cross-check on the encoding."},
    {"id": "gf-field", "claim": "The GF(2^h) arithmetic used is a genuine field",
     "verdict": "CERTIFIED",
     "note": "Associativity, distributivity, and the multiplicative identity hold for the in-kernel carryless "
             "GF(2^h) multiplication (F_4 = F_2[X]/(X^2+X+1), F_8 = F_2[X]/(X^3+X+1))."},
    {"id": "kernel", "claim": "Lean 4.31 re-decides Condition (3) for q=2,4 and the q=8 witness",
     "verdict": "CERTIFIED",
     "note": "ovoid_q2, ovoid_q4 (the census over F_q^3), ovoid_q8_fails (the witness has F=0); GF(2^h) "
             "multiplication computed in-kernel from the irreducible. #print axioms: at most [propext]."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000033", kind="lean-proof",
                          checker="Lean 4.31 kernel (plain decide, 3 theorems) + exact GF(2^h) arithmetic",
                          result="ovoid_q2 / ovoid_q4 accepted (Condition (3) holds -> ovoid of Q+(7,q)); "
                                 "ovoid_q8_fails accepted (the (0,0,0),(0,1,3) pair has F=0 -> not an ovoid); "
                                 "#print axioms at most [propext]"),
]

_REFERENCES = [
    {"citation": ("Bartoli, D., Durante, N., Grimaldi, G. G., & Timpanella, M. (2025). Ovoids of Q+(7,q) of "
                  "low-degree (arXiv:2502.02219)."),
     "url": "https://arxiv.org/abs/2502.02219"},
    {"citation": ("Kantor, W. M. (1982). Ovoids and translation planes. Canadian Journal of Mathematics, 34(5), "
                  "1195-1207."),
     "url": "https://doi.org/10.4153/CJM-1982-082-8"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (low-degree ovoids of Q+(7,q))",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/ovoids_q7.lean + scripts/verify_ovoids_q7.py (exact GF(2^h) Condition (3) census; "
             "Kantor ovoid at q=2,4,16, failure at q=8; Lean 4.31 decide with in-kernel GF(2^h) multiplication)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=33, date="2026-07-06", domain="Finite geometry (ovoids)", kind="verification",
        title="Kernel-attested low-degree ovoids of Q⁺(7,q): Kantor ovoid at q=4, failure at q=8 (Bartoli–Durante–Grimaldi–Timpanella 2025)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_ovoids_q7_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/ovoids_q7.lean to public/artifacts/cycle_000033/."},
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

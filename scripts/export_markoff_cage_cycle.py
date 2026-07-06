"""Emit the kernel-attested Markoff (1,1,1) cage 2-adic divisibility (Bellah–Dunn–Naidu–Wells 2025) as a Codex
Calculemus cycle (ADR 0017). New domain: Diophantine / arithmetic geometry (Markoff triples). Producer only.

Run:  python scripts/export_markoff_cage_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "markoff_cage.lean"

_SUMMARY = (
    "A 2025 result in a domain new to the ledger — Diophantine / arithmetic geometry, the Markoff triples — with "
    "its arithmetic core independently re-decided and kernel-attested by two independent routes. The Markoff "
    "surface is X₁²+X₂²+X₃²=3X₁X₂X₃; the Markoff mod p graph 𝒢_p has the nonzero mod p solutions as vertices and "
    "the Vieta rotations as edges, and Strong Approximation (Bourgain–Gamburd–Sarnak) hinges on connecting the "
    "reduction-fixed special point (1,1,1) to the provably connected cage. Bellah, Dunn, Naidu & Wells "
    "(arXiv:2511.23401) reduce this to a 2-adic property: the rotation order ord_p(1,1,1) is the order of "
    "A=[[0,1],[-1,3]] in GL₂(F_p) (companion matrix of T²−3T+1, discriminant 5), and Theorem 2.10 gives "
    "2^{ν₂(p+1)} | ord_p(1,1,1) whenever p ≡ ±2 (mod 5) (so x=1 is elliptic and (5/p)=−1), while Proposition 3.3 "
    "gives ord_p(1,1,1) = π(p)/2 (half the Fibonacci Pisano period). Leibniz re-decides by exact integer "
    "arithmetic over the primes p ≡ ±2 (mod 5), including the Mersenne primes 7, 127, 524287, 2147483647 "
    "(=2³¹−1), where p+1=2ⁿ so ord = p+1 exactly. Two independent routes agree throughout: a self-contained "
    "matrix certificate (A^{p+1}=I forces ord | p+1, and A^{(p+1)/2}≠I then forces 2^{ν₂(p+1)} | ord — no exact "
    "order or external lemma needed), and the Pisano identity ord(A) = π(p)/2. A prime p ≡ ±1 (mod 5) makes x=1 "
    "hyperbolic and gives A^{p+1}≠I (the order does not divide p+1), confirming the hypothesis is load-bearing. "
    "The Lean 4.31 kernel re-decides the divisibility for a spread of primes and for the Mersenne primes up to "
    "2³¹−1, the two-route agreement for p ∈ {7,127}, and the negative control — all plain decide, every theorem "
    "depending on no axioms; no native_decide, no sorry. Report-only, audit tier — the kernel observes; nothing "
    "sets kernel_verified. LLMs propose nothing; exact arithmetic and the kernel decide."
)

_FINDINGS = [
    {"id": "thm-2-10", "claim": "2^{ν₂(p+1)} | ord_p(1,1,1) for primes p ≡ ±2 (mod 5) (Theorem 2.10 at (1,1,1))",
     "verdict": "CERTIFIED",
     "note": "Verified for 15 primes (7–113) plus the Mersenne primes; a self-contained certificate A^{p+1}=I "
             "(ord | p+1) with A^{(p+1)/2}≠I (2^{ν₂(p+1)} | ord) proves the divisibility with no exact order."},
    {"id": "prop-3-3", "claim": "ord_p(1,1,1) = π(p)/2 — the Fibonacci Pisano-period route (Proposition 3.3)",
     "verdict": "CERTIFIED",
     "note": "The matrix order and the directly-computed Fibonacci Pisano period agree on every prime up to "
             "524287 — an independent second route to the same rotation order."},
    {"id": "mersenne", "claim": "For the Mersenne primes 7, 127, 524287, 2147483647 the order equals p+1 exactly",
     "verdict": "CERTIFIED",
     "note": "p+1 = 2ⁿ ⇒ ν₂(p+1) = n and ord = 2ⁿ; e.g. p = 2³¹−1 gives ord = 2³¹ = 2147483648. Kernel-checked "
             "by fast exponentiation up to 2³¹−1."},
    {"id": "control", "claim": "The ellipticity hypothesis is load-bearing (negative control)",
     "verdict": "CERTIFIED",
     "note": "A prime p ≡ ±1 (mod 5) makes x=1 hyperbolic; there A^{p+1}≠I — the order does not divide p+1 — for "
             "all eight control primes, so Theorem 2.10's hypothesis cannot be dropped. Kernel-checked for p=11."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000030", kind="lean-proof",
                          checker="Lean 4.31 kernel (plain decide, 4 theorems) + exact integer arithmetic",
                          result="markoff_div_small / markoff_div_mersenne (2-adic divisibility up to 2³¹−1) + "
                                 "markoff_pisano (ord = π(p)/2) + markoff_control accepted; #print axioms = no "
                                 "axioms for all four theorems"),
]

_REFERENCES = [
    {"citation": ("Bellah, E., Dunn, C., Naidu, V., & Wells, A. (2025). Connectedness of Special Points in the "
                  "Markoff mod p Graphs (arXiv:2511.23401)."),
     "url": "https://arxiv.org/abs/2511.23401"},
    {"citation": ("Bourgain, J., Gamburd, A., & Sarnak, P. (2016). Markoff triples and strong approximation. "
                  "Comptes Rendus Mathématique, 354(2), 131–135."),
     "url": "https://doi.org/10.1016/j.crma.2015.12.006"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (Markoff (1,1,1) cage 2-adic divisibility)",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/markoff_cage.lean + scripts/verify_markoff_cage.py (exact GL₂(F_p) order + Fibonacci "
             "Pisano period; 2^{ν₂(p+1)} | ord_p(1,1,1) = π(p)/2 + Lean 4.31 decide, Mersenne primes to 2³¹−1)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=30, date="2026-07-06", domain="Arithmetic geometry (Markoff triples)", kind="verification",
        title="Kernel-attested 2-adic divisibility placing the Markoff point (1,1,1) in the connected cage (Bellah–Dunn–Naidu–Wells 2025)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_markoff_cage_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/markoff_cage.lean to public/artifacts/cycle_000030/."},
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

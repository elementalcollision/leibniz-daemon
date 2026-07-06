"""Emit the kernel-attested minimal double blocking sets of size 3q−1 in PG(2,q) (Csajbók–Héger 2019) as a Codex
Calculemus cycle (ADR 0017). New domain: finite geometry / blocking sets. Producer only.

Run:  python scripts/export_double_blocking_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "double_blocking.lean"

_SUMMARY = (
    "A published finite-geometry result in a domain new to the ledger — blocking sets in projective planes — "
    "independently re-decided and kernel-attested. A double blocking set of PG(2,q) is a set of points meeting "
    "every line in at least two points; it is minimal if no proper subset does. The trivial one (three sides of "
    "a triangle) has size 3q, and Ball–Blokhuis (1996) proved 3q is the minimum for q ≤ 8. Csajbók & Héger "
    "(European J. Combin. 78 (2019), 655–678; arXiv:1805.01267) refute R. Hill's cautiously-stated 1984 "
    "expectation that no size-(3q−1) double blocking set with two (q−1)-secants exists: by a MIP search they "
    "exhibit explicit minimal double blocking sets of size 3q−1 admitting two (q−1)-secants for q ∈ "
    "{13,16,19,25,27,31,37,43}, the first sets of size below 3q for prime q > 13. Together with their Section-3 "
    "non-existence theorem this resolves two 1984 Hill conjectures. Leibniz amplifies the constructive half "
    "(existence). From the points printed in the paper, over the five PRIME cases q ∈ {13,19,31,37,43} (finite "
    "field ℤ/qℤ), it reconstructs each set B — both coordinate axes minus four holes, plus the printed points — "
    "and verifies by exact GF(q) incidence arithmetic, two independent ways: (1) DOUBLE BLOCKING — every one of "
    "the q²+q+1 lines meets B in at least two points (no 0- or 1-secant); (2) MINIMALITY — every point of B "
    "lies on a 2-secant, so deleting it leaves a 1-secant. As a faithfulness anchor it reproduces the paper's "
    "published secant distribution nₜ (t ≥ 3) exactly in every case (a single mis-transcribed point would shift "
    "it), with the two nₜ=2 long secants being exactly the two (q−1)-secants Hill's conjecture forbade. The Lean "
    "4.31 kernel then re-decides both properties, plus a discriminating negative control (B minus one point is "
    "NOT double blocking), for the flagships q = 13 (the unique example with two (q−1)-secants up to "
    "equivalence) and q = 19 (the first prime q > 13), by plain decide — every theorem depends on no axioms; no "
    "native_decide, no sorry. Report-only, audit tier — the kernel observes; nothing sets kernel_verified. LLMs "
    "propose nothing; exact finite-field arithmetic and the kernel decide."
)

_FINDINGS = [
    {"id": "exists-3q-1", "claim": "Minimal double blocking sets of size 3q−1 exist in PG(2,q) for prime "
                                   "q ∈ {13,19,31,37,43} — smaller than the trivial 3q triangle",
     "verdict": "CERTIFIED",
     "note": "Reconstructed from the paper's points; each has |B| = 3q−1 (38, 56, 92, 110, 128) and every one "
             "of the q²+q+1 lines meets it in ≥ 2 points, verified by exact GF(q) incidence arithmetic."},
    {"id": "minimal", "claim": "Each set is minimal: every point lies on a 2-secant",
     "verdict": "CERTIFIED",
     "note": "For every point p of B there is a bisecant (a line meeting B in exactly two points) through p, so "
             "B∖{p} has a 1-secant and is not double blocking. Verified exactly for all five prime cases."},
    {"id": "refutes-hill", "claim": "The two (q−1)-secants coexist — refuting Hill's 1984 conjecture",
     "verdict": "CERTIFIED",
     "note": "The published secant distribution nₜ (t ≥ 3) is reproduced exactly in every case; its two "
             "n_{q−1}=2 long secants are the two (q−1)-secants Hill (1984) expected could not both occur."},
    {"id": "kernel", "claim": "Lean 4.31 re-decides blocking + minimality + a negative control for q = 13, 19",
     "verdict": "CERTIFIED",
     "note": "Six plain-decide theorems (db{13,19}_{blocking,minimal,control}); the controls prove a "
             "point-deleted set is NOT double blocking (= false). #print axioms: every theorem depends on no "
             "axioms — no native_decide, no sorry."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000028", kind="lean-proof",
                          checker="Lean 4.31 kernel (plain decide, 6 theorems) + exact GF(q) incidence arithmetic",
                          result="db13/db19 blocking + minimal accepted, controls reject (= false); #print axioms "
                                 "= no axioms for all six theorems"),
]

_REFERENCES = [
    {"citation": ("Csajbók, B., & Héger, T. (2019). Double blocking sets of size 3q−1 in PG(2,q). European "
                  "Journal of Combinatorics, 78, 655–678 (arXiv:1805.01267)."),
     "url": "https://arxiv.org/abs/1805.01267"},
    {"citation": ("Ball, S., & Blokhuis, A. (1996). On the size of a double blocking set in PG(2,q). Finite "
                  "Fields and Their Applications, 2(2), 125–137."),
     "url": "https://doi.org/10.1006/ffta.1996.0009"},
    {"citation": ("Hill, R. (1984). Some problems concerning (k,n)-arcs in finite projective planes. Rendiconti "
                  "del Seminario Matematico di Brescia, 7, 367–383."),
     "url": ""},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (double blocking sets 3q−1 in PG(2,q))",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/double_blocking.lean + scripts/verify_double_blocking.py (exact GF(q) incidence: double "
             "blocking + minimality + published secant distribution + Lean 4.31 decide, q ∈ {13,19})"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=28, date="2026-07-06", domain="Finite geometry", kind="verification",
        title="Kernel-attested minimal double blocking sets of size 3q−1 in PG(2,q), refuting a 1984 Hill conjecture (Csajbók–Héger 2019)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_double_blocking_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/double_blocking.lean to public/artifacts/cycle_000028/."},
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

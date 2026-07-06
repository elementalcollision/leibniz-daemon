"""Emit the kernel-attested simplest Kochen-Specker set (Cabello 2025) as a Codex Calculemus cycle (ADR 0017).
New domain: quantum contextuality / Kochen-Specker sets. Producer only.

Run:  python scripts/export_cabello_ks_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "cabello_ks.lean"

_SUMMARY = (
    "A 2025 disproof of a published conjecture in a domain new to the ledger — quantum contextuality / "
    "Kochen-Specker sets — independently re-decided and fully kernel-attested. A Kochen-Specker (KS) set is a "
    "finite set of vectors admitting no {0,1}-assignment f with f(u)+f(v)<=1 for orthogonal u,v and sum=1 over "
    "each orthonormal basis. Cabello (PRL 135, 190203, 2025; arXiv:2508.07335) exhibits a KS set of 33 qutrit "
    "vectors using only 14 orthogonal bases -- a record-low number of bases (previous record 16, Peres) -- "
    "refuting Conjecture 2 of PRL 134, 010201 (2025) on the minimum number of inputs. The vectors have "
    "Eisenstein-integer components (w=e^{2 pi i/3}, w^2=-1-w); the 14 bases are Eqs (1a)-(1e), (2a)-(2i). Leibniz "
    "re-decides both halves by exact arithmetic over Z[w]: each of the 14 printed bases is mutually orthogonal "
    "(Hermitian inner product 0) and the vectors span exactly 33 distinct rays; and the set is KS-uncolorable -- "
    "no {0,1}-assignment with exactly-one per basis and at-most-one per orthogonal edge exists, a finite UNSAT "
    "verified by a bounded backtracking search (~1.2k nodes; also confirmed unsat by z3). Reproducing basis "
    "orthogonality caught one text-extraction artifact (the x=3 third vector is (w^2,-w,1), a dropped minus "
    "sign). The Lean 4.31 kernel re-decides basis orthogonality and uncolorability directly (exact Z[w] "
    "arithmetic; the backtracking solver in-kernel -- no external SAT/DRAT dump), plus a negative control (a "
    "13-basis subset is colorable). With 14 bases this beats the previous record of 16, refuting the "
    "minimum-inputs conjecture. #print axioms at most [propext]; no native_decide, no sorry. Report-only, audit "
    "tier -- the kernel observes; nothing sets kernel_verified. LLMs propose nothing; exact arithmetic and the "
    "kernel decide."
)

_FINDINGS = [
    {"id": "ks-uncolorable", "claim": "The 33-vector, 14-basis set is Kochen-Specker uncolorable",
     "verdict": "CERTIFIED",
     "note": "No {0,1}-assignment with exactly one 1 per basis and at most one 1 per orthogonal edge exists -- a "
             "finite UNSAT verified by a bounded backtracking search (~1.2k nodes), decided directly in the "
             "kernel and independently confirmed unsat by z3."},
    {"id": "record-14-bases", "claim": "It uses only 14 orthogonal bases (a record; previous minimum 16)",
     "verdict": "CERTIFIED",
     "note": "Over Z[w] each of the 14 printed bases is mutually orthogonal and the vectors span exactly 33 "
             "distinct rays; 14 < 16 refutes Conjecture 2 of PRL 134, 010201 (2025) on the minimum number of "
             "inputs/bases."},
    {"id": "faithful", "claim": "Basis orthogonality fixes the transcription (33 rays)",
     "verdict": "CERTIFIED",
     "note": "Reproducing each basis's Hermitian orthogonality caught a dropped minus sign in a pdf text-layer "
             "extraction: the x=3 third vector is (w^2,-w,1). The exact orthogonality is authoritative and "
             "recovers all 33 rays."},
    {"id": "kernel", "claim": "Lean 4.31 re-decides orthogonality + uncolorability + a negative control",
     "verdict": "CERTIFIED",
     "note": "cabello_bases_orth (14 orthogonal bases over Z[w]), cabello_uncolorable (the backtracking solver "
             "returns no assignment), cabello_control (a 13-basis subset is colorable). #print axioms at most "
             "[propext]; no native_decide, no sorry."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000034", kind="lean-proof",
                          checker="Lean 4.31 kernel (plain decide, 3 theorems) + exact Eisenstein-integer arithmetic",
                          result="cabello_bases_orth (14 orthogonal bases over Z[w]) + cabello_uncolorable (no KS "
                                 "assignment, ~1.2k-node backtracking) + cabello_control (13-basis subset "
                                 "colorable); #print axioms at most [propext]"),
]

_REFERENCES = [
    {"citation": ("Cabello, A. (2025). Simplest Kochen-Specker set. Physical Review Letters, 135, 190203 "
                  "(arXiv:2508.07335)."),
     "url": "https://arxiv.org/abs/2508.07335"},
    {"citation": ("Yu, S., & Oh, C. H. (2012). State-independent proof of Kochen-Specker theorem with 13 rays. "
                  "Physical Review Letters, 108, 030402."),
     "url": "https://doi.org/10.1103/PhysRevLett.108.030402"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (simplest Kochen-Specker set)",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/cabello_ks.lean + scripts/verify_cabello_ks.py (exact Z[w] orthogonality of 14 bases + "
             "in-kernel backtracking KS-uncolorability; Lean 4.31 decide)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=34, date="2026-07-06", domain="Quantum contextuality (Kochen-Specker)", kind="refutation",
        title="Kernel-attested Simplest Kochen-Specker Set: a 14-basis KS set refuting a 2025 PRL conjecture (Cabello 2025)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_cabello_ks_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/cabello_ks.lean to public/artifacts/cycle_000034/."},
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

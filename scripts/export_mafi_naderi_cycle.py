"""Emit the Mafi–Naderi integral-closure verification as a Codex Calculemus cycle (ADR 0017). Producer only."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "mafi_naderi_certificate.lean"

_SUMMARY = (
    "An independent kernel verification of a monomial-ideal result, on the general monomial-ideal instrument. "
    "Mafi and Naderi (2021, 'Integral closure and Hilbert series of a special monomial ideal', arXiv:2112.02921) "
    "study M_{n,t} = (x^{e_1},…,x^{e_n}), where x^{e_i} is the product of all variables except the i-th, each to "
    "the power t. Their Theorem 1.6 says the integral closure of M_{n,t} is a Veronese-type ideal; for three "
    "variables this is closure(M_{3,t}) = {x^u : min(a,t)+min(b,t)+min(c,t) ≥ 2t}. Their Corollary 1.7 says "
    "M_{n,t} is Cohen–Macaulay (unmixed), yet its integral closure has embedded associated primes. LLMs propose "
    "nothing here; the Lean 4.31 kernel decides. Using our exact integral-dependence instrument we confirm, for "
    "n = 3: (Theorem 1.6) the computed integral closure equals the Veronese cap-sum ideal, cross-checked for "
    "t = 1,2,3,4; and (Corollary 1.7) the closure has the embedded prime (x,y,z) for t ≥ 2 — witnessed by a "
    "monomial u that is not in the closure but whose product with each variable is (for t = 2 the witness is "
    "xyz) — while M_{3,t} itself has no such witness and is unmixed, so the integral closure GAINS an embedded "
    "prime the original ideal lacks. An honest detail our check surfaces: at t = 1 the ideal is the squarefree "
    "Veronese, already integrally closed and with no embedded prime, so the phenomenon begins at t = 2. Verdict: "
    "agreement — no erratum. Six theorems, kernel-decided by `decide`, standard axioms. This is a second "
    "independent verification on the general monomial-ideal instrument, after Ataka–Matsuoka."
)

_FINDINGS = [
    {"id": "thm16", "claim": "closure(M_{3,t}) equals the Veronese cap-sum ideal (Mafi–Naderi Theorem 1.6)",
     "verdict": "CONFIRMED",
     "note": "The integral closure computed by exact integral dependence equals {min(a,t)+min(b,t)+min(c,t) ≥ "
             "2t}, cross-checked t=1..4; the cap-sum predicate is validated to equal the true closure over the box."},
    {"id": "cor17", "claim": "The integral closure has an embedded prime the ideal lacks (Corollary 1.7)",
     "verdict": "CONFIRMED",
     "note": "closure(M_{3,t}) has the embedded prime (x,y,z) for t≥2 (witness u∉closure with x·u,y·u,z·u∈"
             "closure; xyz at t=2); M_{3,t} itself has no such witness (unmixed). Honest detail: at t=1 there "
             "is no embedded prime (M_{3,1} is the squarefree Veronese). Kernel-decided."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000014", kind="lean-proof",
                          checker="Lean 4.31 kernel (decide)",
                          result="6 theorems decided; #print axioms = standard set"),
]

_REFERENCES = [
    {"citation": ("Mafi, A., & Naderi, D. (2021). Integral closure and Hilbert series of a special monomial "
                  "ideal (arXiv:2112.02921). arXiv."), "url": "https://arxiv.org/abs/2112.02921"},
    {"citation": ("Huneke, C., & Swanson, I. (2006). Integral closure of ideals, rings, and modules (London "
                  "Mathematical Society Lecture Note Series No. 336). Cambridge University Press."), "url": ""},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon #294",
     "url": "https://github.com/elementalcollision/leibniz-daemon/pull/294",
     "role": "produced",
     "note": "scripts/verify_mafi_naderi.py + docs/crt/mafi_naderi_certificate.lean (general monomial-ideal instrument)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=14, date="2026-07-05", domain="Commutative ring theory", kind="verification",
        title=("Independent kernel verification of Mafi–Naderi (2021): the integral closure of M_{3,t} gains an "
               "embedded prime"),
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_mafi_naderi_cycle.py",
                     "target": _TARGET, "merge": "append to cycles[]; copy the .lean to public/artifacts/cycle_000014/."},
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

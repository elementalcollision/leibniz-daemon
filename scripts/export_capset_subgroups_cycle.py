"""Emit the kernel-attested confirmation of Kable–Mills–Wright's (2026) cap-set subgroups of finite fields as a
Codex Calculemus cycle (ADR 0017). New domain: additive combinatorics over finite fields (cap sets).
Producer only.

Run:  python scripts/export_capset_subgroups_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "capset_subgroups.lean"

_SUMMARY = (
    "A fresh 2026 result in a domain new to the ledger — additive combinatorics over finite fields / cap sets — "
    "independently confirmed and kernel-decided. A cap set contains no full line of its affine geometry: in "
    "AG(k,3), the card game SET, a line is three distinct points summing to 0; in AG(k,2), the game EvenQuads, "
    "a 'quad' is four distinct points summing to 0. Kable, Mills & Wright (arXiv:2604.26989) show certain "
    "MULTIPLICATIVE subgroups of a finite field, seen inside the field's ADDITIVE geometry, are cap sets. "
    "Leibniz re-decides these from the field axioms, using none of the paper's tables: it builds GF(pᵏ) = "
    "F_p[t]/(irreducible), confirms it is a genuine field (multiplicative group cyclic of order pᵏ−1), forms "
    "the power-subgroup, and checks the cap property by exact finite-field arithmetic over every triple (char 3) "
    "or quad (char 2). It confirms: the 20 nonzero fourth powers of GF(81) are a SET-cap (no 3 sum to 0 in "
    "AG(4,3)); the 9 nonzero seventh powers of GF(64) are an EvenQuads-cap (no 4 sum to 0 in AG(6,2)); and the "
    "general theorem that the (2ⁿ−1)-th powers form a cap of size 2ⁿ+1 in GF(2^{2n}), verified for n=2..5 "
    "(sizes 5, 9, 17, 33). Both marquee subgroups are the MAXIMAL caps for their decks (sizes 20 and 9), an "
    "external cross-check; and the cap property is model-independent — Leibniz re-verifies GF(81) with a second "
    "irreducible polynomial and obtains the same 20-cap. The Lean 4.31 kernel then independently decides the two "
    "marquee caps over the explicit (F₃)⁴ / (F₂)⁶ element vectors (plain decide, #print axioms = propext only; "
    "no native_decide, no sorry). Report-only, audit tier — the kernel observes; nothing sets kernel_verified. "
    "LLMs propose nothing; exact finite-field arithmetic and the kernel decide."
)

_FINDINGS = [
    {"id": "set-cap",
     "claim": "The 20 nonzero fourth powers of GF(81) are a maximal SET-cap in AG(4,3)", "verdict": "CERTIFIED",
     "note": "No three distinct elements sum to 0; size 20 = the maximal cap size for the SET deck. Verified by "
             "exact F_3 arithmetic and re-confirmed with a second irreducible polynomial (model-independent)."},
    {"id": "evenquads-cap",
     "claim": "The 9 nonzero seventh powers of GF(64) are a maximal EvenQuads-cap in AG(6,2)", "verdict": "CERTIFIED",
     "note": "No four distinct elements sum to 0; size 9 = the maximal cap size for EvenQuads. Exact F_2 arithmetic."},
    {"id": "general",
     "claim": "The (2ⁿ−1)-th powers form a cap of size 2ⁿ+1 in GF(2^{2n})", "verdict": "CERTIFIED",
     "note": "Verified for n=2..5 (sizes 5, 9, 17, 33). n=3 is the EvenQuads case. Each a valid field with the "
             "expected subgroup order and no quad."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000025", kind="lean-proof",
                          checker="Lean 4.31 kernel (plain decide, 2 theorems) + exact GF(p^k) arithmetic",
                          result="capset_set81 (no 3 sum to 0 among 20 GF(81) fourth-powers) + capset_eq64 (no 4 "
                                 "sum to 0 among 9 GF(64) seventh-powers) accepted; #print axioms = [propext]"),
]

_REFERENCES = [
    {"citation": ("Kable, A., Mills, M., & Wright, D. J. (2026). Subgroups of finite fields as cap sets "
                  "(arXiv:2604.26989). arXiv."),
     "url": "https://arxiv.org/abs/2604.26989"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (cap-set subgroups)",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/capset_subgroups.lean + scripts/verify_capset_subgroups.py (exact GF(p^k) arithmetic, "
             "model-independent + Lean 4.31 decide)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=25, date="2026-07-05", domain="Additive combinatorics", kind="verification",
        title="Kernel-attested cap-set subgroups of finite fields (SET, EvenQuads, and the GF(2^2n) family; Kable–Mills–Wright 2026)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_capset_subgroups_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/capset_subgroups.lean to public/artifacts/cycle_000025/."},
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

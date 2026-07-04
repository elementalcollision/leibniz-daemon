"""Emit the Ataka–Matsuoka Example 4.7 verification (and erratum) as a Codex Calculemus cycle (ADR 0017).

A verification cycle: Leibniz independently kernel-checks a third party's Feb-2026 illustrative examples and
reports the verdicts — 4.7(1) confirmed normal, 4.7(2) a kernel-checkable ERRATUM (not integrally closed).
Carries no `kernel_verified` edge, mints nothing, promulgates nothing; the `decide` results are *reported*
checks by the Lean 4.31 kernel, tagged as such. Producer only — Leibniz builds the fragment; the operator
commits it to `elementalcollision/codex-calculemus` and copies the `.lean` cert to `public/artifacts/`.

Run:  python scripts/export_ataka_matsuoka_47_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "ataka_matsuoka_47_certificate.lean"

_SUMMARY = (
    "A second independent kernel pass over Ataka and Matsuoka (arXiv:2602.01782), this time on the "
    "illustrative Example 4.7 (§4.3, reduction numbers of normal ideals) — and it surfaces a kernel-checkable "
    "erratum. We built a general monomial-ideal normality instrument for k[x,y,z] that decides everything by "
    "the integral-dependence definition (x^u ∈ I^p iff some multiset of p generators sums ≤ u; x^u ∈ "
    "closure(I^p) iff x^{ku} ∈ I^{pk} for some k; and normality by the Reid–Roberts–Vitulli reduction, d = 3). "
    "It is cross-validated against the corner-ideal checker, the Example 4.5 sharpness result, and exact "
    "linear-programming membership. On Example 4.7 it finds: 4.7(1), I = (x³,y²,z²,xy,xz,yz), is normal as "
    "stated (a positive control); but 4.7(2), I = (x³,y³,z³,x²y,xy²,x²z,yz), stated to be 'a normal ideal by "
    "Theorem 3.1', is NOT integrally closed. The monomial xz² is not in I, yet its square (xz²)² = x²z⁴ = "
    "(x²z)·(z³) lies in I²; a monomial whose square lies in I² is integral over I, so xz² is in the integral "
    "closure of I but not in I. Hence I is not normal in the standard sense (a normal ideal satisfies I = Ī), "
    "and Theorem 3.1 — which requires I = Ī and μ(I) ≤ 7 — does not apply as printed; the actual integral "
    "closure has eight minimal generators. All of this is kernel-decided by `decide` with no axiom "
    "dependencies. The erratum is a slip in an illustrative example and is independent of the paper's Main "
    "Theorem, whose sharpness (the μ(I) ≤ 7 bound, witness closure(x⁷,y³,z²)) we verified and confirmed "
    "correct in the previous cycle. LLMs propose nothing here; the Lean kernel decides."
)

_FINDINGS = [
    {"id": "4.7(1)", "claim": "I = (x³,y²,z²,xy,xz,yz) is normal", "verdict": "CONFIRMED",
     "note": "Positive control: I and I² are integrally closed (general instrument, integral-dependence + "
             "RRV d=3), so I is normal, as the paper states."},
    {"id": "4.7(2)", "claim": "I = (x³,y³,z³,x²y,xy²,x²z,yz) is 'a normal ideal by Theorem 3.1'",
     "verdict": "ERRATUM",
     "note": "NOT integrally closed: xz² ∉ I but (xz²)² = (x²z)(z³) ∈ I², so xz² ∈ closure(I) ∖ I. Hence I is "
             "not normal (a normal ideal has I = Ī), and Theorem 3.1 (needs I = Ī, μ ≤ 7) does not apply as "
             "printed; μ(Ī) = 8 > 7. Kernel-decided, axiom-free. Independent of the Main Theorem (Example 4.5, "
             "verified correct in the prior cycle)."},
    {"id": "instr", "claim": "A general monomial-ideal normality instrument for k[x,y,z]", "verdict": "VERIFIED",
     "note": "Decides I^p / closure(I^p) membership and normality (RRV d=3) by integral dependence, stdlib and "
             "exact; cross-validated against the corner checker, Example 4.5, and exact LP membership."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000009", kind="lean-proof",
                          checker="Lean 4.31 kernel (decide)",
                          result="three theorems decided; #print axioms = does not depend on any axioms"),
]

_REFERENCES = [
    {"citation": ("Ataka, M., & Matsuoka, N. (2026). Normality of monomial ideals in three variables "
                  "(arXiv:2602.01782). arXiv."), "url": "https://arxiv.org/abs/2602.01782"},
    {"citation": ("Cahen, P.-J., Fontana, M., Frisch, S., & Glaz, S. (2014). Open problems in commutative "
                  "ring theory. In M. Fontana, S. Frisch, & S. Glaz (Eds.), Commutative algebra (pp. "
                  "353–375). Springer."), "url": ""},
    {"citation": ("Reid, L., Roberts, L. G., & Vitulli, M. A. (2003). Some results on normal homogeneous "
                  "ideals. Communications in Algebra, 31(9), 4485–4506."), "url": ""},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon #288",
     "url": "https://github.com/elementalcollision/leibniz-daemon/pull/288",
     "role": "produced",
     "note": "scripts/monomial_ideal_normality.py + scripts/verify_ataka_matsuoka_47.py + "
             "docs/crt/ataka_matsuoka_47_certificate.lean"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=9,
        date="2026-07-04",
        domain="Commutative ring theory",
        kind="verification",
        title=("Independent kernel verification of Ataka–Matsuoka (2026) Example 4.7 — a kernel-checkable "
               "erratum in 4.7(2)"),
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
            "producer": "scripts/export_ataka_matsuoka_47_cycle.py",
            "target": _TARGET,
            "merge": "append the object in `cycles` to the site ledger's top-level `cycles` array; also copy "
                     "docs/crt/ataka_matsuoka_47_certificate.lean to public/artifacts/cycle_000009/.",
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

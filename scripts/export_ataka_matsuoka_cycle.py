"""Emit the Ataka–Matsuoka verification work-log entry for Codex Calculemus (*Il Lavoro* / `/cycles`, ADR 0017).

This is a **verification cycle**, not a promulgated law: Leibniz independently kernel-attests a third party's
published result (Ataka–Matsuoka 2026, Example 4.5) and reports the verdict. It carries no `kernel_verified`
edge, mints nothing, promulgates nothing — the `decide` results it cites are *reported* checks by the Lean
4.31 kernel, tagged as such (see `docs/results/ataka-matsuoka-732-verification-2026-07-04.md` and the
downloadable `docs/crt/ataka_matsuoka_732_certificate.lean`).

Producer only: builds the cycle via `calculemus_site.cycle_payload` and writes the ready-to-merge fragment.
Leibniz produces; the operator commits it into the site repo `elementalcollision/codex-calculemus`
(`ledger/calculemus.json` → `cycles[]`), and the `.lean` certificate is copied to
`public/artifacts/cycle_000008/` so the underpinnings are publicly auditable even though the source repo is
private.

Run:  python scripts/export_ataka_matsuoka_cycle.py            # print the cycle fragment
      python scripts/export_ataka_matsuoka_cycle.py -o FILE    # also write it to FILE
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "ataka_matsuoka_732_certificate.lean"

_SUMMARY = (
    "An independent kernel verification of a February-2026 result. Ataka and Matsuoka (arXiv:2602.01782) "
    "prove that an integrally closed monomial ideal I in k[x,y,z] with at most seven minimal generators is "
    "normal (every power integrally closed), and that the bound seven is sharp. Their sharpness witness "
    "(Example 4.5) is I = the integral closure of (x⁷,y³,z²): it has eight minimal generators and fails to "
    "be normal. LLMs propose nothing here — the paper's claim is the object, and the Lean 4.31 kernel "
    "decides. From the Newton polyhedron (weights (6,14,21), L = lcm = 42) we reproduce BOTH load-bearing "
    "facts and cross-check them verbatim against Example 4.5: the eight minimal generators "
    "(x⁷, y³, z², x⁵y, x³y², x⁴z, y²z, x²yz), and the non-normality witness x⁶y²z, which lies in the integral "
    "closure of I² (weighted degree 85 ≥ 2L = 84) but not in I² itself, so by the Reid–Roberts–Vitulli "
    "reduction (in three variables, normal ⇔ I and I² integrally closed) the ideal is not normal. All three "
    "theorems are decided by `decide` with no axiom dependencies at all. A built-in erratum guard refuses to "
    "emit the certificate unless the generator count, the generator set, the verdict, the witness monomial, "
    "and the weight vector all match the transcribed paper — the same discipline that caught a real erratum "
    "in the SS-RS-GD COLT refutation. Verification-amplification on the flagship Problem-41 instrument; no "
    "trust surface is touched. A companion research pass (paper-grounded, adversarially faithfulness-checked) "
    "records that the three resolved commutative-ring candidates 30a, 30b, and 9 are NOT finite-decidable "
    "counterexamples — 30a (Secord 2023) and 30b (Choi–Walker 2016) were resolved positively, and Problem 9 "
    "(Haotian Ma 2026) has an intrinsically infinite counterexample — so the domain's growth runs through "
    "open monomial questions, not the resolved n-absorbing ones."
)

_FINDINGS = [
    {"id": "gen", "claim": "closure(x⁷,y³,z²) has exactly EIGHT minimal monomial generators", "verdict": "VERIFIED",
     "note": "Our Newton-polyhedron computation of the minimal lattice points of {u : 6u₁+14u₂+21u₃ ≥ 42} "
             "returns the paper's list x⁷,y³,z²,x⁵y,x³y²,x⁴z,y²z,x²yz — set-equal, count 8. Kernel-decided "
             "(eight_minimal_generators, generators_are_paper_list), no axioms."},
    {"id": "norm", "claim": "closure(x⁷,y³,z²) is NOT normal — the sharpness witness for μ(I) ≤ 7 ⇒ normal",
     "verdict": "CERTIFIED",
     "note": "x⁶y²z ∈ closure(I²) (weighted degree 85 ≥ 2L = 84) but x⁶y²z ∉ I², so I² is not integrally "
             "closed; by Reid–Roberts–Vitulli (d=3) I is not normal. Kernel-decided (not_normal_witness_x6y2z), "
             "no axioms. Reproduced verbatim from Example 4.5."},
    {"id": "res", "claim": "The three resolved Tier-A CRT candidates (30a, 30b, 9) are not finite-decidable",
     "verdict": "SKIP (honest)",
     "note": "Paper-grounded + adversarially faithfulness-checked: 30a (Secord 2023) and 30b (Choi–Walker "
             "2016) were resolved POSITIVELY (no counterexample exists); Problem 9 (Haotian Ma 2026) has an "
             "intrinsically infinite Akiba/Nagata counterexample. None is a bounded `decide` target."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000008", kind="lean-proof",
                          checker="Lean 4.31 kernel (decide)",
                          result="three theorems decided; #print axioms = does not depend on any axioms"),
]

# APA references — rendered as the reference list at the foot of the published cycle.
_REFERENCES = [
    {"citation": ("Ataka, M., & Matsuoka, N. (2026). Normality of monomial ideals in three variables "
                  "(arXiv:2602.01782). arXiv."), "url": "https://arxiv.org/abs/2602.01782"},
    {"citation": ("Cahen, P.-J., Fontana, M., Frisch, S., & Glaz, S. (2014). Open problems in commutative "
                  "ring theory. In M. Fontana, S. Frisch, & S. Glaz (Eds.), Commutative algebra (pp. "
                  "353–375). Springer."), "url": ""},
    {"citation": ("Reid, L., Roberts, L. G., & Vitulli, M. A. (2003). Some results on normal homogeneous "
                  "ideals. Communications in Algebra, 31(9), 4485–4506."), "url": ""},
]

# The auditable code trail — our own repo where the certificate + producer live.
_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon #287",
     "url": "https://github.com/elementalcollision/leibniz-daemon/pull/287",
     "role": "produced",
     "note": "scripts/verify_ataka_matsuoka.py + docs/crt/ataka_matsuoka_732_certificate.lean "
             "(min_generators() on the Problem-41 instrument)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=8,
        date="2026-07-04",
        domain="Commutative ring theory",
        kind="verification",
        title=("Independent kernel verification of Ataka–Matsuoka (2026): closure(x⁷,y³,z²) is the sharp "
               "non-normal monomial ideal"),
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
            "producer": "scripts/export_ataka_matsuoka_cycle.py",
            "target": _TARGET,
            "merge": "append the object in `cycles` to the site ledger's top-level `cycles` array; also copy "
                     "docs/crt/ataka_matsuoka_732_certificate.lean to public/artifacts/cycle_000008/.",
        },
        "cycles": [build_cycle()],
    }


def main(argv: list[str]) -> int:
    if "--generated-at" in argv:
        stamp = argv[argv.index("--generated-at") + 1]
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
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

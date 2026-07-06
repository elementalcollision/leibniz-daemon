"""Emit the kernel-attested base case of Bamberg–Giudici–Lansdown–Royle's open Conjecture 4.1 (PΓU(5,q)
non-spreading) as a Codex Calculemus cycle (ADR 0017). New domain: finite polar spaces / non-spreading classical
groups. Producer only.

Run:  python scripts/export_pgu_nonspreading_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "pgu_nonspreading.lean"

_SUMMARY = (
    "An OPEN conjecture in a domain new to the ledger — finite polar spaces and the synchronisation hierarchy of "
    "permutation groups — with its base case independently re-decided and kernel-attested. Bamberg, Giudici, "
    "Lansdown & Royle (Des. Codes Cryptogr. 2024; arXiv:2403.17576) prove (Theorem 4.2) that PΓU(5,q), acting on "
    "the totally isotropic 1-spaces of the Hermitian polar space H(4,q²), is non-spreading — but only CONDITIONAL "
    "on their still-open Conjecture 4.1: for b ∈ F_{q²} with b^{q+1}=−1 and (s,u,w) ∈ F_{q²}³ on the norm cone "
    "s^{q+1}=u^{q+1}+w^{q+1}, the count n(κ) of λ ∈ F_{q²}∪{∞} solving "
    "(wλ+1)(b+uλ)^q − (wλ+1)^q(b+uλ) = κ(b²+1+λ²(s²−u²−w²))^{(q+1)/2} satisfies n(κ)=n(−κ) for all κ ∈ F_q^*. "
    "Leibniz re-decides this by exact GF(q²) arithmetic (F_{q²}=F_q[X]/(X²−r); Frobenius x^q negates the "
    "X-coordinate; λ over F_{q²}∪{∞} handled by homogenising [λ:μ] on P¹(F_{q²})). For the primes q ∈ {3,5,7} it "
    "enumerates every admissible b and every (s,u,w) on the norm cone and finds the symmetry n(κ)=n(−κ) holds "
    "with zero violations for all non-trivial triples; for q ≥ 5 the symmetry is specifically κ↦−κ (tuples with "
    "n(1)≠n(2) exist). A faithfulness finding: read literally the conjecture fails at exactly one triple, the "
    "trivial origin (s,u,w)=(0,0,0) — the zero vector, no geometric point (in the paper's derivation (s,u,w) is a "
    "non-zero totally isotropic point); with the non-degeneracy (s,u,w)≠0 it holds exactly. The Lean 4.31 kernel "
    "then re-decides the base case q=3 by plain decide (the field, the admissible parameter sets and P¹(F₉) all "
    "generated from (q,r)=(3,2), no baked data): the symmetry holds for every admissible non-trivial parameter, "
    "and the origin genuinely breaks it (a discriminating negative control). Every theorem depends on no axioms; "
    "no native_decide, no sorry. Certifying Conjecture 4.1 at q=3 makes Theorem 4.2 UNCONDITIONAL there: "
    "PΓU(5,3) on H(4,9) is non-spreading. Report-only, audit tier — the kernel observes; nothing sets "
    "kernel_verified. LLMs propose nothing; exact finite-field arithmetic and the kernel decide."
)

_FINDINGS = [
    {"id": "conj41-holds", "claim": "Conjecture 4.1 (open) verified for q ∈ {3,5,7}: n(κ)=n(−κ) for all "
                                    "non-trivial admissible parameters",
     "verdict": "CERTIFIED",
     "note": "Exact GF(q²) census over every admissible b and every (s,u,w) on the norm cone (|valid (s,u,w)| = "
             "225 / 3025 / 16513 for q = 3/5/7); zero symmetry violations among non-trivial triples."},
    {"id": "origin-sole-exception", "claim": "The only exception to the literal statement is the trivial origin "
                                             "(s,u,w)=(0,0,0)",
     "verdict": "CERTIFIED",
     "note": "Across q ∈ {3,5,7} the unique failing triple is the zero vector — no projective point (the paper's "
             "(s,u,w) is a non-zero totally isotropic point). With (s,u,w) ≠ 0 the conjecture holds exactly. "
             "Pins the implicit non-degeneracy; a triviality, not a defect."},
    {"id": "specificity", "claim": "The symmetry is specifically κ↦−κ, not 'all counts equal'",
     "verdict": "CERTIFIED",
     "note": "For q ≥ 5 there exist admissible tuples with n(1) ≠ n(2) (2 ≠ ±1), so n is genuinely non-constant "
             "in κ and the ± symmetry is a real constraint."},
    {"id": "kernel-q3", "claim": "Lean 4.31 re-decides the base case q=3, making Theorem 4.2 unconditional there",
     "verdict": "CERTIFIED",
     "note": "pgu_q3_symmetry (symmetry for all non-trivial parameters) + pgu_q3_origin (origin breaks it — "
             "negative control); field/parameters/P¹ generated from (q,r)=(3,2). #print axioms: both depend on no "
             "axioms — no native_decide, no sorry. Hence PΓU(5,3) on H(4,9) is non-spreading, unconditionally."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000029", kind="lean-proof",
                          checker="Lean 4.31 kernel (plain decide, 2 theorems) + exact GF(q²) arithmetic",
                          result="pgu_q3_symmetry accepted, pgu_q3_origin accepted (origin breaks the symmetry); "
                                 "#print axioms = no axioms for both theorems"),
]

_REFERENCES = [
    {"citation": ("Bamberg, J., Giudici, M., Lansdown, J., & Royle, G. F. (2024). Tactical decompositions in "
                  "finite polar spaces and non-spreading classical group actions. Designs, Codes and "
                  "Cryptography (arXiv:2403.17576)."),
     "url": "https://arxiv.org/abs/2403.17576"},
    {"citation": ("Araújo, J., Cameron, P. J., & Steinberg, B. (2017). Between primitive and 2-transitive: "
                  "synchronization and its friends. EMS Surveys in Mathematical Sciences, 4(2), 101–184."),
     "url": "https://doi.org/10.4171/EMSS/22"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (Conjecture 4.1 / PΓU(5,q) non-spreading)",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/pgu_nonspreading.lean + scripts/verify_pgu_nonspreading.py (exact GF(q²) solution-count "
             "symmetry n(κ)=n(−κ) for q ∈ {3,5,7} + Lean 4.31 decide, base case q=3)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=29, date="2026-07-06", domain="Finite geometry (polar spaces)", kind="verification",
        title="Kernel-attested base case of the open Conjecture 4.1 — PΓU(5,3) on H(4,9) is non-spreading (Bamberg–Giudici–Lansdown–Royle 2024)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_pgu_nonspreading_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/pgu_nonspreading.lean to public/artifacts/cycle_000029/."},
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

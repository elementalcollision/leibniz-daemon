"""Emit the kernel-attested confirmation of Aliabadi's (2026) counterexample to the Brualdi–Friedland–Pothen
sparse-basis conjecture as a Codex Calculemus cycle (ADR 0017). New domain: combinatorial matrix theory /
elementary vectors. Producer only.

Run:  python scripts/export_bfp_counterexample_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "bfp_counterexample.lean"

_SUMMARY = (
    "A fresh 2026 counterexample in a domain new to the ledger — combinatorial matrix theory / elementary "
    "vectors — independently confirmed and decided by the Lean kernel. Brualdi, Friedland & Pothen conjectured "
    "(Conjecture 2.1 in Aliabadi 2026) a clean combinatorial test: for an m×n rank-m matrix A with "
    "algebraically-independent nonzero entries, elementary vectors x₁,…,xₘ of the row space with zero-sets "
    "Jₛ=Z(xₛ) form a BASIS iff for every nonempty P⊆[m], rank A[:, ⋂_{s∈P} Jₛ] ≤ m−|P|. Aliabadi "
    "(arXiv:2605.30401) refutes the SUFFICIENCY direction with an explicit 4×8 sparse-generic A: all "
    "rank-intersection inequalities hold, yet the four elementary vectors are linearly DEPENDENT. The mechanism "
    "is that the inequalities only inspect ⋂Jₛ, which here are tiny (|⋂|≤4−|P|), so the test passes for free "
    "while the real dependence lives outside its view. Leibniz does NOT trust the paper's vectors: it "
    "reconstructs each xₛ as the unique row-space vector vanishing on Jₛ and verifies, EXACTLY over ℚ(a,…,l) "
    "(the algebraically-independent case the conjecture requires), that Z(xₛ)=Jₛ, that each xₛ is a genuine "
    "elementary vector (its support is a COCIRCUIT — Jₛ is a hyperplane; row-space elementary vectors have "
    "cocircuit, not circuit, supports), that all 15 inequalities hold, and that rank[x₁;…;x₄]=3<4 (dependent ⇒ "
    "not a basis). A matroid-faithful integer specialization (its 39 basis 4×4 minors match the generic ones) "
    "then lets the Lean 4.31 kernel DECIDE the same facts (plain decide, no native_decide; #print axioms only "
    "propext), including elementary-ness via nonzero 3×3/4×4 minors computed from A in-kernel and a nonzero "
    "integer vector d with d·[x₁;…;x₄]=0. A corrupted d is rejected (negative control). Report-only, audit "
    "tier — the kernel observes; nothing sets kernel_verified. LLMs propose nothing; exact linear algebra and "
    "the kernel decide."
)

_FINDINGS = [
    {"id": "sufficiency-refuted",
     "claim": "The BFP sparse-basis conjecture's SUFFICIENCY direction is false (Conjecture 2.1)",
     "verdict": "REFUTED",
     "note": "For the explicit 4×8 sparse-generic A, all 15 rank-intersection inequalities |⋂Jₛ|≤4−|P| hold, "
             "yet the four elementary vectors are linearly dependent (rank 3 < 4) — not a basis."},
    {"id": "elementary-genuine",
     "claim": "The four vectors are genuine elementary vectors (cocircuit / minimal support)", "verdict": "CERTIFIED",
     "note": "Reconstructed by Leibniz (not trusted from the paper): Z(xₛ)=Jₛ, rank A[:,Jₛ]=3, and adjoining "
             "any outside column raises the rank to 4 — verified symbolically over ℚ(a,…,l) and in-kernel."},
    {"id": "kernel-decided",
     "claim": "The Lean 4.31 kernel decides a matroid-faithful integer witness, axiom-clean", "verdict": "CERTIFIED",
     "note": "Integer point realizes the generic matroid (39 bases match). Plain decide; #print axioms only "
             "propext (a canonical trusted Lean axiom); no native_decide, no sorry. Corrupted d rejected."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000021", kind="lean-proof",
                          checker="Lean 4.31 kernel (plain decide; #print axioms = [propext])",
                          result="theorem bfp_counterexample accepted: membership + Z(xₛ)=Jₛ + elementary "
                                 "minors + BFP inequalities + nonzero d with d·X=0; only propext"),
]

_REFERENCES = [
    {"citation": ("Aliabadi, M. (2026). A counterexample to a basis conjecture of Brualdi, Friedland, and "
                  "Pothen (arXiv:2605.30401). arXiv."),
     "url": "https://arxiv.org/abs/2605.30401"},
    {"citation": ("Brualdi, R. A., Friedland, S., & Pothen, A. (1995). The sparse basis problem and multilinear "
                  "algebra. SIAM Journal on Matrix Analysis and Applications, 16(1), 1–20."),
     "url": "https://doi.org/10.1137/S0895479892238452"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (BFP counterexample)",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/bfp_counterexample.lean + scripts/verify_bfp_counterexample.py (exact ℚ(a,…,l) + "
             "matroid-faithful integer instance + Lean 4.31 decide)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=21, date="2026-07-05", domain="Combinatorial matrix theory", kind="refutation",
        title="Kernel-attested counterexample to the Brualdi–Friedland–Pothen sparse-basis conjecture (Aliabadi 2026)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_bfp_counterexample_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/bfp_counterexample.lean to public/artifacts/cycle_000021/."},
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

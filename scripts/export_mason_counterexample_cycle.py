"""Emit the kernel-attested confirmation of Larson's (2026) counterexample to Mason's matroid log-concavity
conjecture as a Codex Calculemus cycle (ADR 0017). New domain: matroid theory / log-concavity. Producer only.

Run:  python scripts/export_mason_counterexample_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "mason_counterexample.lean"

_SUMMARY = (
    "A fresh 2026 result in a domain new to the ledger — matroid theory / log-concavity — independently "
    "re-derived and re-decided by the Lean kernel. Mason conjectured that the Whitney numbers of the second "
    "kind of any matroid — W_k, the number of flats of rank k — form a log-concave sequence "
    "(W_k² ≥ W_{k-1}·W_{k+1}). Larson (arXiv:2607.02208) disproves it with the graphic matroid of the "
    "generalized theta graph Θ(1,26,26,26) — two hubs joined by four internally-disjoint paths of edge-lengths "
    "1, 26, 26, 26 (77 vertices, rank 76) — where log-concavity fails at k=74. Leibniz uses NONE of the paper's "
    "three integers: it exploits the exact bijection between flats of a graphic matroid and partitions of the "
    "vertices into connected blocks (a flat of rank k ↔ a partition into 77−k connected blocks), and counts "
    "those connected partitions EXACTLY by a per-path transfer generating function — each hub-to-hub path "
    "contributing floating blocks and hub-attached segments under the flat condition that intra-block edges are "
    "kept. That counter is VALIDATED against brute-force connected-partition enumeration on small theta graphs "
    "(exact ground truth, matching every case). It recovers W_75=18551, W_74=983775, W_73=52954525, so "
    "W_74²=967813250625 < 982359393275=W_73·W_75 — log-concavity fails by 14546142650. The Lean 4.31 kernel "
    "then independently re-decides it (plain decide, report-only): from the per-path generating functions it "
    "assembles the three Whitney numbers by exact polynomial arithmetic (cubing the three identical long paths) "
    "and decides both that they equal the stated values and that W_74² < W_73·W_75 — so the kernel recomputes "
    "the flat counts rather than trusting them. #print axioms is clean (propext only). Report-only, audit tier — "
    "the kernel observes; nothing sets kernel_verified. LLMs propose nothing; exact combinatorics and the "
    "kernel decide."
)

_FINDINGS = [
    {"id": "counterexample",
     "claim": "Mason's matroid log-concavity conjecture is FALSE: the Whitney numbers of Θ(1,26,26,26) are not "
              "log-concave at k=74",
     "verdict": "REFUTED",
     "note": "W_75=18551, W_74=983775, W_73=52954525 ⇒ W_74²=967813250625 < 982359393275=W_73·W_75 "
             "(fails by 14546142650). Independently recomputed from the matroid, not taken from the paper."},
    {"id": "counter-validated",
     "claim": "The Whitney numbers are recomputed by an exact connected-partition counter validated vs brute force",
     "verdict": "CERTIFIED",
     "note": "flats ↔ connected vertex partitions; a per-path transfer generating function counts them, matching "
             "brute-force enumeration on small theta graphs including the Θ(1,L,L,L) shape."},
    {"id": "kernel-redecided",
     "claim": "The Lean 4.31 kernel assembles the Whitney numbers itself and decides the log-concavity failure",
     "verdict": "CERTIFIED",
     "note": "Two plain-decide theorems: mason_whitney_values (kernel cubes the per-path GFs → 18551/983775/"
             "52954525) and mason_log_concavity_fails (W_74² < W_73·W_75). #print axioms = [propext]; no "
             "native_decide, no sorry."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000023", kind="lean-proof",
                          checker="Lean 4.31 kernel (plain decide, 2 theorems) + exact connected-partition counting",
                          result="mason_whitney_values + mason_log_concavity_fails accepted; kernel recomputes "
                                 "W_75/74/73 = 18551/983775/52954525 and decides W_74² < W_73·W_75"),
]

_REFERENCES = [
    {"citation": ("Larson, M. (2026). Counterexamples to two conjectures about matroids (arXiv:2607.02208). "
                  "arXiv."),
     "url": "https://arxiv.org/abs/2607.02208"},
    {"citation": ("Mason, J. H. (1972). Matroids: unimodal conjectures and Motzkin's theorem. In D. J. A. "
                  "Welsh & D. R. Woodall (Eds.), Combinatorics (pp. 207–220). Institute of Mathematics and Its "
                  "Applications."),
     "url": "https://mathscinet.ams.org/mathscinet-getitem?mr=349445"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (Mason counterexample)",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/mason_counterexample.lean + scripts/verify_mason_counterexample.py (exact connected-"
             "partition counting validated vs brute force + Lean 4.31 decide)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=23, date="2026-07-05", domain="Matroid theory", kind="refutation",
        title="Kernel-attested counterexample to Mason's matroid log-concavity conjecture (Larson 2026)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_mason_counterexample_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/mason_counterexample.lean to public/artifacts/cycle_000023/."},
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

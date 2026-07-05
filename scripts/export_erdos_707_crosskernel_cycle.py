"""Emit the cross-kernel Erdős-707 verification (Lean 4.31 ↔ Rocq 9.0) as a Codex Calculemus cycle (ADR 0017).
The cross-kernel attestation sweep applied to the finite core of a freshly-resolved $1000 Erdős problem.
Producer only.

Run:  python scripts/export_erdos_707_crosskernel_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "erdos_707_crosscheck.v"

_SUMMARY = (
    "The cross-kernel attestation sweep reaches a marquee result: the finite core of Erdős Problem 707 (the "
    "Sidon-Extension Conjecture — a $1000 problem posed repeatedly from 1976), which Leibniz's Lean 4.31 "
    "kernel decided in cycle 15 / PR #295, independently RE-DECIDED by the Rocq 9.0 (Coq) kernel. Erdős asked "
    "whether every finite Sidon set extends to a finite perfect difference set (PDS); it was disproved by "
    "Alexeev & Mixon (arXiv:2510.19804) via {1,2,4,8,13} (and Hall's {1,3,9,10,13}), with size-4 candidates "
    "{0,1,3,11}, {0,1,4,11} from Niu (arXiv:2604.25214). A PDS of order n has n(n−1)=v−1, so B ⊂ ℤ_v is a PDS "
    "iff its pairwise diffs mod v are distinct, and non-extension at order n means no size-n superset is Sidon "
    "mod v — a bounded decidable fact. For each of the four counterexample sets the Rocq kernel re-decides "
    "(by vm_compute) the SAME facts Lean decided: the set is Sidon, and it is non-extending at orders |S| and "
    "|S|+1. All 12 Examples are confirmed AXIOM-FREE by Rocq's own library checker rocqchk (* Axioms: <none> *, "
    "no unsafe constructs), and exact Python set-arithmetic is a third independent cross-check. Two independent "
    "trusted cores agreeing on the finite exhaustion of a freshly-resolved $1000 problem is strictly stronger "
    "evidence than either alone. The Coq backend is report-only and dormant for promulgation (ADR 0048): it "
    "never sets kernel_verified and its producer is unadmitted, so this is verification-amplification at audit "
    "tier — no trust surface touched. LLMs propose nothing; both kernels decide."
)

_FINDINGS = [
    {"id": "crosskernel", "claim": "The Erdős-707 finite core re-decided in a second kernel (Rocq 9.0)",
     "verdict": "CERTIFIED",
     "note": "For {0,1,3,11}, {0,1,4,11}, {1,2,4,8,13}, {1,3,9,10,13}: each Sidon and non-extending at orders "
             "|S|, |S|+1 — the same facts Lean decided (#295), re-decided by Rocq via vm_compute. 12 Examples."},
    {"id": "sound-audit", "claim": "The Coq re-decision is axiom-free (rocqchk whole-development audit)",
     "verdict": "CERTIFIED",
     "note": "rocqchk -o reports * Axioms: <none> and <none> for type-in-type / unsafe-(co)fixpoints / "
             "assumed-positivity — the Coq analogue of Lean's #print-axioms-clean decide."},
    {"id": "scope", "claim": "Finite core in a second kernel — the infinite claim stays non-finite", "verdict": "NOTED",
     "note": "Cross-checks the SAME finite exhaustion (Sidon + non-extension at small orders); 'no PDS at all' "
             "is proven non-finitely (Alexeev–Mixon polarity; size-4 still conjectural). No trust surface."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000019", kind="coq-proof",
                          checker="Rocq 9.0 kernel (rocq compile + rocqchk audit)",
                          result="12 Examples decided by vm_compute; rocqchk CONTEXT SUMMARY: axioms <none>, "
                                 "no unsafe constructs"),
]

_REFERENCES = [
    {"citation": ("Alexeev, B., & Mixon, D. G. (2025). Forbidden Sidon subsets of perfect difference sets, "
                  "featuring a human-assisted proof (arXiv:2510.19804). arXiv."),
     "url": "https://arxiv.org/abs/2510.19804"},
    {"citation": ("Niu, T. (2026). Size-4 counterexamples to the Sidon-extension conjecture (arXiv:2604.25214). "
                  "arXiv."), "url": "https://arxiv.org/abs/2604.25214"},
    {"citation": ("The Rocq Development Team. (2025). The Rocq Prover (Version 9.0) [Computer software]. Inria, "
                  "CNRS, and contributors."), "url": "https://rocq-prover.org/"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (cross-kernel Erdős 707)",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/erdos_707_crosscheck.v + scripts/verify_erdos_707_crosskernel.py (ADR 0048 sound Coq backend)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=19, date="2026-07-05", domain="Combinatorics", kind="verification",
        title="Cross-kernel confirmation of the Erdős-707 finite core (Sidon-Extension Conjecture; Lean 4.31 ↔ Rocq 9.0)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_erdos_707_crosskernel_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/erdos_707_crosscheck.v to public/artifacts/cycle_000019/."},
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

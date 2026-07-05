"""Emit the cross-kernel Guo–Krattenthaler verification (Lean 4.31 ↔ Rocq 9.0) as a Codex Calculemus cycle
(ADR 0017). A verification cycle: Leibniz re-decides an already-Lean-decided divisibility census in a SECOND,
independent kernel (Rocq/Coq), axiom-free. Carries no `kernel_verified`, mints nothing, promulgates nothing.
Producer only.

Run:  python scripts/export_gk_crosskernel_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "gk_coq_crosscheck.v"

_SUMMARY = (
    "The first cross-kernel amplification in the ledger: a result already decided by the Lean 4.31 kernel, "
    "independently re-decided by a SECOND trusted core — the Rocq 9.0 (Coq) kernel. Guo and Krattenthaler "
    "(2014, J. Number Theory 135, 167–184, arXiv:1301.7651) proved three binomial divisibilities that hold "
    "for every positive integer n: 6n−1 divides both C(12n,3n) and C(12n,4n), and 66n−1 divides C(330n,88n). "
    "Leibniz's Lean census (cycle 13 / PR #293) kernel-decided these as certified instances. Here the SAME 17 "
    "instances — (6n−1)∣C(12n,3n) and (6n−1)∣C(12n,4n) for n=1..8, and (66n−1)∣C(330,88) — are re-decided by "
    "the Rocq 9.0 kernel over binary N (Coq's Peano nat cannot hold the ~90-digit C(330,88)), each by "
    "`vm_compute; reflexivity`, and confirmed AXIOM-FREE by Rocq's own separate library checker `rocqchk`, "
    "whose whole-development CONTEXT SUMMARY reports `* Axioms: <none>` and no unsafe constructs. Two "
    "independent kernels agreeing on the same arithmetic is strictly stronger evidence than either alone — an "
    "independent kernel catches translation and kernel-specific errors a single-checker pipeline cannot. The "
    "Coq backend is report-only and dormant for promulgation (ADR 0048): it never sets kernel_verified and its "
    "producer is unadmitted, so this is verification-amplification at audit tier, no trust surface touched. "
    "LLMs propose nothing; both kernels decide, and math.comb is a third, independent cross-check."
)

_FINDINGS = [
    {"id": "crosskernel", "claim": "The GK divisibilities re-decided in a second kernel (Rocq 9.0)",
     "verdict": "CERTIFIED",
     "note": "All 17 instances the Lean census decided (#293) verify again in Coq over binary N, each "
             "`vm_compute; reflexivity`. Two independent trusted cores (Lean 4.31 + Rocq 9.0) agree."},
    {"id": "sound-audit", "claim": "The Coq re-decision is axiom-free (rocqchk whole-development audit)",
     "verdict": "CERTIFIED",
     "note": "Rocq's separate checker `rocqchk -o` re-validates the compiled .vo and reports `* Axioms: "
             "<none>` plus `<none>` for type-in-type / unsafe-(co)fixpoints / assumed-positivity — the Coq "
             "analogue of Lean's `#print axioms`-clean `decide`."},
    {"id": "scope", "claim": "Finite instances in a second kernel — not the general-n theorem", "verdict": "NOTED",
     "note": "This cross-checks the SAME finite instances Lean decided; the all-n prime-modulus theorem is "
             "cycle 13's Phase 2 (Kummer, Lean). No trust surface — report-only, ADR 0048 dormant tier."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000017", kind="coq-proof",
                          checker="Rocq 9.0 kernel (rocq compile + rocqchk audit)",
                          result="17 Examples decided over binary N; rocqchk CONTEXT SUMMARY: axioms <none>, "
                                 "no unsafe constructs"),
]

_REFERENCES = [
    {"citation": ("Guo, V. J. W., & Krattenthaler, C. (2014). Some divisibility properties of binomial and "
                  "q-binomial coefficients. Journal of Number Theory, 135, 167–184."),
     "url": "https://arxiv.org/abs/1301.7651"},
    {"citation": ("The Rocq Development Team. (2025). The Rocq Prover (Version 9.0) [Computer software]. Inria, "
                  "CNRS, and contributors."), "url": "https://rocq-prover.org/"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon #299",
     "url": "https://github.com/elementalcollision/leibniz-daemon/pull/299",
     "role": "produced",
     "note": "docs/crt/gk_coq_crosscheck.v + scripts/verify_gk_crosskernel.py (ADR 0048 sound Coq backend)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=17, date="2026-07-05", domain="Number theory", kind="verification",
        title="Cross-kernel confirmation of Guo–Krattenthaler binomial divisibilities (Lean 4.31 ↔ Rocq 9.0)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_gk_crosskernel_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/gk_coq_crosscheck.v to public/artifacts/cycle_000017/."},
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

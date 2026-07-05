"""Emit the Erdős 707 finite-core verification as a Codex Calculemus cycle (ADR 0017). Producer only."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "erdos_707_certificate.lean"

_SUMMARY = (
    "An independent kernel verification of the finite core of a freshly-resolved $1000 Erdős problem. Erdős "
    "Problem 707, the Sidon-Extension Conjecture, asserts that every finite Sidon set (a set of integers whose "
    "pairwise differences are all distinct) extends to a finite perfect difference set — a set B in ℤ_v of "
    "size n, with v = n²−n+1, in which every nonzero residue is a difference exactly once. Erdős posed it "
    "repeatedly from 1976 with a $1000 reward, and it stood for nearly 50 years. Alexeev and Mixon "
    "(arXiv:2510.19804, October 2025) disproved it: the size-5 Sidon set {1,2,4,8,13} extends to no perfect "
    "difference set (as does Hall's 1947 set {1,3,9,10,13}, which predates the conjecture). Niu "
    "(arXiv:2604.25214) then exhibited size-4 candidates {0,1,3,11} and {0,1,4,11} that fail to extend for "
    "every modulus v ≤ 133, evidence that the smallest non-extending Sidon set has size 4. LLMs propose "
    "nothing here; the Lean 4.31 kernel decides. The key reduction is that a perfect difference set of order n "
    "satisfies n(n−1) = v−1, so a size-n set in ℤ_v is a perfect difference set precisely when its pairwise "
    "differences mod v are all distinct; hence non-extension at a given order is a bounded, decidable fact — "
    "no size-n superset of S is Sidon mod v. We kernel-decide, for each of the four counterexample sets and "
    "with no axioms: that it is a Sidon set; that it does not extend to a perfect difference set at order |S| "
    "(the set reduced mod v is not one); and that it does not extend at order |S|+1 (adjoining any single "
    "residue never yields one). Our instrument additionally reproduces the non-extension for all orders with "
    "v ≤ 43, a faithful slice of the papers' unconditional exhaustion. Honest scope: non-extension to ANY "
    "finite perfect difference set is an infinite claim, established non-finitely by the polarity argument (the "
    "size-4 case remains conjectural); we certify the finitely-checkable core."
)

_FINDINGS = [
    {"id": "sidon", "claim": "The four counterexample sets are Sidon sets", "verdict": "CERTIFIED",
     "note": "{1,2,4,8,13} and {1,3,9,10,13} (Alexeev–Mixon / Hall), {0,1,3,11} and {0,1,4,11} (Niu) — all "
             "have distinct pairwise differences over ℤ. Kernel-decided, no axioms."},
    {"id": "nonext", "claim": "Each set is non-extending at small orders (Erdős 707 finite core)",
     "verdict": "CERTIFIED",
     "note": "Non-extension at order |S| (the set mod v = |S|²−|S|+1 is not a perfect difference set) and at "
             "order |S|+1 (no single adjoined residue yields one), kernel-decided; the instrument reproduces "
             "the non-extension for all orders with v ≤ 43 (the papers' full run reaches v ≤ 133)."},
    {"id": "scope", "claim": "The full 'no perfect difference set at all' claim is infinite", "verdict": "NOTED",
     "note": "Proven non-finitely by Alexeev–Mixon's polarity argument (size 5); the size-4 case is still "
             "conjectural. We certify the finite exhaustion, an independent verification of the checkable core."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000015", kind="lean-proof",
                          checker="Lean 4.31 kernel (decide)",
                          result="12 theorems decided; #print axioms = does not depend on any axioms"),
]

_REFERENCES = [
    {"citation": ("Alexeev, B., & Mixon, D. G. (2025). Forbidden Sidon subsets of perfect difference sets, "
                  "featuring a human-assisted proof (arXiv:2510.19804). arXiv."),
     "url": "https://arxiv.org/abs/2510.19804"},
    {"citation": ("Niu, T. (2026). Size-4 counterexamples to the Sidon-extension conjecture (arXiv:2604.25214). "
                  "arXiv."), "url": "https://arxiv.org/abs/2604.25214"},
    {"citation": ("Hall, M. (1947). Cyclic projective planes. Duke Mathematical Journal, 14(4), 1079–1090."),
     "url": ""},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon #295",
     "url": "https://github.com/elementalcollision/leibniz-daemon/pull/295",
     "role": "produced",
     "note": "scripts/verify_erdos_707.py + docs/crt/erdos_707_certificate.lean"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=15, date="2026-07-05", domain="Combinatorics", kind="verification",
        title="Independent kernel verification of the finite core of Erdős Problem 707 (Sidon-Extension Conjecture)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_erdos_707_cycle.py",
                     "target": _TARGET, "merge": "append to cycles[]; copy the .lean to public/artifacts/cycle_000015/."},
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

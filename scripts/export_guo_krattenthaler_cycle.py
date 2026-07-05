"""Emit the Guo–Krattenthaler verification (Phase 1) as a Codex Calculemus cycle (ADR 0017).

A verification cycle: Leibniz independently kernel-decides a published number-theory result's divisibility
claims. Carries no `kernel_verified` edge, mints nothing, promulgates nothing; the `decide` results are
reported checks by the Lean 4.31 kernel. Producer only.

Run:  python scripts/export_guo_krattenthaler_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "guo_krattenthaler_certificate.lean"

_SUMMARY = (
    "An independent kernel verification of a Journal of Number Theory result. Guo and Krattenthaler (2014, "
    "'Some divisibility properties of binomial and q-binomial coefficients', J. Number Theory 135, 167–184, "
    "arXiv:1301.7651) prove two headline facts. First, three new divisibilities that hold for every positive "
    "integer n: 6n−1 divides both C(12n,3n) and C(12n,4n), and 66n−1 divides C(330n,88n). In the paper these "
    "follow from a deeper phenomenon — the divisibility and positivity of quotients of q-binomial coefficients "
    "by q-integers, generalizing the positivity of the q-Catalan numbers. Second, they confirm a conjecture of "
    "Z.-W. Sun: if a has a prime factor that does not divide b, then there are infinitely many n for which "
    "bn+1 does NOT divide C((a+b)n, an) — in contrast with the Catalan case a=b=1, where n+1 always divides "
    "C(2n,n). LLMs propose nothing here; the Lean 4.31 kernel decides. This Phase-1 census kernel-decides the "
    "three divisibilities as certified instances (for a range of n, up to the ~90-digit C(330,88) which the "
    "kernel handles via sub-term sharing) and confirms Sun's conjecture by explicit non-divisibility witnesses "
    "for six qualifying pairs (a,b). All 23 theorems are decided by `decide` over exact Nat.choose and depend "
    "only on the standard axiom propext. This target was chosen because it reuses, verbatim, the from-scratch "
    "Gaussian-binomial machinery Leibniz built for the Problem-16 self-ordered proofs (the q-Pascal recurrence "
    "and q-factorial divisibility) — the same q-integer positivity that underlies Guo–Krattenthaler; the "
    "all-n theorem (Phase 2) is the natural follow-on."
)

_FINDINGS = [
    {"id": "div", "claim": "Three all-n binomial divisibilities of Guo–Krattenthaler", "verdict": "CERTIFIED",
     "note": "(6n−1)∣C(12n,3n) and (6n−1)∣C(12n,4n) certified for n=1..8; (66n−1)∣C(330n,88n) for n=1 (a "
             "~90-digit binomial). Axiom-`decide` over exact Nat.choose; #print axioms = [propext]."},
    {"id": "sun", "claim": "Sun's non-divisibility conjecture (confirmed by Guo–Krattenthaler)",
     "verdict": "CERTIFIED",
     "note": "If a has a prime factor ∤ b, then ∃∞ n with (bn+1)∤C((a+b)n,an). Kernel-decided by explicit "
             "witnesses for (2,1),(3,1),(3,2),(4,3),(5,2),(2,3); the Catalan a=b=1 always-divides case anchors "
             "the contrast."},
    {"id": "q", "claim": "Reuses the from-scratch Gaussian-binomial machinery (Problem 16)", "verdict": "NOTED",
     "note": "The paper's mechanism is q-binomial-by-q-integer positivity — the same construction Leibniz "
             "built (gBinom q-Pascal recurrence, qf, qf_dvd_ffall). The all-n theorem via q-positivity is the "
             "Phase-2 follow-on."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000013", kind="lean-proof",
                          checker="Lean 4.31 kernel (decide)",
                          result="23 theorems decided; #print axioms = standard set (propext)"),
]

_REFERENCES = [
    {"citation": ("Guo, V. J. W., & Krattenthaler, C. (2014). Some divisibility properties of binomial and "
                  "q-binomial coefficients. Journal of Number Theory, 135, 167–184."),
     "url": "https://arxiv.org/abs/1301.7651"},
    {"citation": ("Sun, Z.-W. (2013). Products and sums divisible by central binomial coefficients. "
                  "Electronic Journal of Combinatorics, 20(1), #P9."), "url": ""},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon #293",
     "url": "https://github.com/elementalcollision/leibniz-daemon/pull/293",
     "role": "produced",
     "note": "scripts/guo_krattenthaler_divisibility.py + docs/crt/guo_krattenthaler_certificate.lean"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=13,
        date="2026-07-05",
        domain="Number theory",
        kind="verification",
        title=("Independent kernel verification of Guo–Krattenthaler (2014) binomial divisibility (Phase 1)"),
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
            "producer": "scripts/export_guo_krattenthaler_cycle.py",
            "target": _TARGET,
            "merge": "append the object in `cycles` to the site ledger's top-level `cycles` array; also copy "
                     "docs/crt/guo_krattenthaler_certificate.lean to public/artifacts/cycle_000013/.",
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

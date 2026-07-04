"""Emit the Problem 16 self-ordered sequence census as a Codex Calculemus cycle (ADR 0017).

A certification cycle: kernel-decided refutations of natural non-self-ordered sequences, plus a correction to
an earlier loose claim. Carries no `kernel_verified` edge, mints nothing, promulgates nothing — the `decide`
results are *reported* checks by the Lean 4.31 kernel. Producer only; the operator commits the fragment to
`elementalcollision/codex-calculemus` and copies the `.lean` cert to `public/artifacts/`.

Run:  python scripts/export_prob16_census_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "prob16_census_certificate.lean"

_SUMMARY = (
    "Cahen–Fontana–Frisch–Glaz Problem 16 (Chabert) asks for the natural self-ordered integer sequences. A "
    "sequence a is self-ordered (Adam–Cahen–Fares simultaneously ordered) when its factorial "
    "D_n = ∏_{k<n}(aₙ − aₖ) divides P(m,n) = ∏_{k<n}(aₘ − aₖ) for all m and n. Self-ordered is an infinite "
    "condition, so it cannot be certified by a bounded computation — but its negation is finitely witnessed: "
    "one pair (m,n) with D_n not dividing P(m,n) refutes it, and that is a kernel-decidable fact. This census "
    "screens a curated set of natural sequences and kernel-certifies the refutations. Five natural sequences "
    "are certified NOT self-ordered: n³ (witness m,n = 3,2), n⁴ (4,3), the factorial (n+1)! (3,2), the "
    "Fibonacci numbers (4,3), and the primes (3,2). Each certificate hardcodes only the short value prefix its "
    "witness needs, so polynomial, factorial, Fibonacci, and prime sequences are all handled uniformly, with "
    "no symbolic sequence definition required. The five sequences that pass are self-ordered up to N = 30 "
    "(bounded evidence, not a proof): the identity n, the arithmetic 3+5n, n², the triangular numbers, and 2ⁿ. "
    "A correction rides along: an earlier loose framing had listed 'refute {n²}' as an angle for this problem "
    "— that is wrong. n² is self-ordered up to N = 30; the refutable pure powers are n^k with k ≥ 3. Notably, "
    "three of the most natural non-polynomial sequences — the factorials, the Fibonacci numbers, and the "
    "primes — are certified NOT self-ordered, honest evidence about where self-ordering does not come from. "
    "LLMs propose nothing; the Lean kernel decides. These are certified instances of an open classification, "
    "not a classification."
)

_FINDINGS = [
    {"id": "refute", "claim": "Five natural sequences are NOT self-ordered", "verdict": "CERTIFIED",
     "note": "n³ (witness (3,2)), n⁴ (4,3), (n+1)! (3,2), distinct Fibonacci (4,3), primes (3,2). Each "
             "kernel-decided (D_n ∤ P(m,n)); #print axioms returns only the standard set (propext)."},
    {"id": "n2", "claim": "n² is self-ordered — the earlier 'refute {n²}' framing was wrong", "verdict": "CORRECTED",
     "note": "n² is self-ordered up to N=30 (no refuting witness). The refutable pure powers are n^k with "
             "k ≥ 3. The internal corpus note has been corrected."},
    {"id": "natural", "claim": "Factorial, Fibonacci, and primes are not self-ordered", "verdict": "OBSERVED",
     "note": "Three of the most natural non-polynomial sequences fail self-ordering, each by a small explicit "
             "witness — honest evidence about where self-ordering does not arise."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000011", kind="lean-proof",
                          checker="Lean 4.31 kernel (decide)",
                          result="5 refutation theorems decided; #print axioms = standard set (propext)"),
]

_REFERENCES = [
    {"citation": ("Cahen, P.-J., Fontana, M., Frisch, S., & Glaz, S. (2014). Open problems in commutative "
                  "ring theory. In M. Fontana, S. Frisch, & S. Glaz (Eds.), Commutative algebra (pp. "
                  "353–375). Springer."), "url": ""},
    {"citation": ("Adam, D., Cahen, P.-J., & Fares, Y. (2010). Subsets of ℤ with simultaneous ordering. "
                  "Integers, 10, 437–451."), "url": ""},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon #290",
     "url": "https://github.com/elementalcollision/leibniz-daemon/pull/290",
     "role": "produced",
     "note": "scripts/prob16_census.py + docs/crt/prob16_census_certificate.lean"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=11,
        date="2026-07-04",
        domain="Commutative ring theory",
        kind="certification",
        title=("A self-ordered sequence census (Problem 16) — natural non-self-ordered sequences certified, "
               "and the n² correction"),
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
            "producer": "scripts/export_prob16_census_cycle.py",
            "target": _TARGET,
            "merge": "append the object in `cycles` to the site ledger's top-level `cycles` array; also copy "
                     "docs/crt/prob16_census_certificate.lean to public/artifacts/cycle_000011/.",
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

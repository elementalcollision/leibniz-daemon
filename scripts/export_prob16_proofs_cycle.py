"""Emit the Problem 16 positive-proofs cycle for Codex Calculemus (ADR 0017).

A certification cycle: kernel-verified PROOFS that arithmetic sequences are self-ordered — the positive side
of Problem 16, crossed from bounded evidence to theorem. Carries no `kernel_verified` edge, mints nothing,
promulgates nothing; the elaborations are reported checks by the Lean 4.31 kernel. Producer only.

Run:  python scripts/export_prob16_proofs_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "prob16_self_ordered_proofs.lean"

_SUMMARY = (
    "Cahen–Fontana–Frisch–Glaz Problem 16 (Chabert) asks for the natural self-ordered integer sequences. A "
    "sequence a is self-ordered when its factorial D_n = ∏_{k<n}(aₙ − aₖ) divides P(m,n) = ∏_{k<n}(aₘ − aₖ) "
    "for all m and n. This is an infinite condition, so our earlier census could only refute it or give "
    "bounded evidence for the positive cases. Here we cross that line and PROVE the positive side, in the "
    "Lean 4.31 kernel, for an entire class. First, the identity sequence aₙ = n is self-ordered: its "
    "factorial is D_n = ∏_{k<n}(n − k) = n!, and n! divides the product of any n consecutive integers "
    "∏_{k<n}(m − k) — the standard factorial-divides-descending-factorial fact, with the case m < n handled "
    "by a zero factor in the product. Second, and generally, EVERY arithmetic sequence aₙ = α + βn is "
    "self-ordered: each factor (α+βx) − (α+βk) equals β(x − k), so both D_n and P(m,n) factor as βⁿ times the "
    "identity factorial; the shared βⁿ cancels and the claim reduces to the identity case. Corollaries "
    "instantiate the census's self-ordered arithmetic sequences — n, 2n, and 3 + 5n — as theorems, upgrading "
    "them from 'self-ordered up to N = 30 (evidence)' to proofs. All four theorems depend only on the "
    "standard axioms (propext, Classical.choice, Quot.sound); the proofs are complete, with no admitted goals "
    "and no compiler-trusted shortcuts. Together with the census refutations (n³, n⁴, factorial, Fibonacci, "
    "primes), Problem 16 now has both a certified negative side and a proved positive class. The harder "
    "geometric case aₙ = qⁿ — whose ratio P/D is a Gaussian binomial coefficient in ℤ[q], hence an integer — "
    "was routed to a hosted Goedel-Prover but did not converge in the time budget, and is left as future "
    "work. LLMs propose nothing that counts here; the Lean kernel decides every step."
)

_FINDINGS = [
    {"id": "identity", "claim": "The identity sequence aₙ = n is self-ordered", "verdict": "PROVED",
     "note": "D_n = n! divides the product of n consecutive integers ∏_{k<n}(m − k); kernel-verified, "
             "standard axioms (identity_selfOrdered)."},
    {"id": "arith", "claim": "Every arithmetic sequence aₙ = α + βn is self-ordered", "verdict": "PROVED",
     "note": "Each factor scales by β, so D_n and P(m,n) share a factor βⁿ and it reduces to the identity "
             "case; fully general in α, β. Kernel-verified, standard axioms (arith_selfOrdered)."},
    {"id": "geometric", "claim": "Geometric aₙ = qⁿ (Gaussian-binomial) — attempted mechanically",
     "verdict": "FUTURE WORK",
     "note": "Routed to the wired Goedel-Prover-V2 (Featherless); did not converge in the time budget. A hand "
             "proof would go through the q-factorial / q-binomial integrality."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000012", kind="lean-proof",
                          checker="Lean 4.31 kernel",
                          result="4 theorems elaborated, 0 sorry; #print axioms = standard set"),
]

_REFERENCES = [
    {"citation": ("Cahen, P.-J., Fontana, M., Frisch, S., & Glaz, S. (2014). Open problems in commutative "
                  "ring theory. In M. Fontana, S. Frisch, & S. Glaz (Eds.), Commutative algebra (pp. "
                  "353–375). Springer."), "url": ""},
    {"citation": ("Adam, D., Cahen, P.-J., & Fares, Y. (2010). Subsets of ℤ with simultaneous ordering. "
                  "Integers, 10, 437–451."), "url": ""},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon #291",
     "url": "https://github.com/elementalcollision/leibniz-daemon/pull/291",
     "role": "produced",
     "note": "docs/crt/prob16_self_ordered_proofs.lean + scripts/prob16_self_ordered_proofs.py"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=12,
        date="2026-07-04",
        domain="Commutative ring theory",
        kind="certification",
        title=("Problem 16 positive side proved — arithmetic sequences are self-ordered (kernel-verified)"),
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
            "producer": "scripts/export_prob16_proofs_cycle.py",
            "target": _TARGET,
            "merge": "append the object in `cycles` to the site ledger's top-level `cycles` array; also copy "
                     "docs/crt/prob16_self_ordered_proofs.lean to public/artifacts/cycle_000012/.",
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

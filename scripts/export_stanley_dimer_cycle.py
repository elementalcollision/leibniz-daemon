"""Emit the kernel-attested disproof of Stanley's 1985 dimer conjecture (k=13) as a Codex Calculemus cycle
(ADR 0017). Independent first-principles confirmation of Guo & Tao (2026); Problem 33 in Lai (2024).
Producer only.

Run:  python scripts/export_stanley_dimer_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_CERT = _ROOT / "docs" / "crt" / "stanley_dimer_13.lean"

_SUMMARY = (
    "A 41-year-old conjecture, disproved and decided by the Lean kernel. Richard Stanley (1985) showed the "
    "domino-tiling counts A_{k,n} of the k×n rectangle have a rational generating function with denominator "
    "degree 2^⌊(k+1)/2⌋, and conjectured the minimal linear-recurrence order of {A_{k,n}} equals that bound "
    "for every k (Problem 33 in Lai's 2024 AMS open-problems volume). Guo & Tao (2026, arXiv:2605.28195) "
    "disproved it, with k=13 the smallest counterexample. Leibniz reproduces the disproof from FIRST "
    "PRINCIPLES, using none of the paper's polynomials: a broken-profile transfer DP computes A_{k,n} as exact "
    "big integers (A_{2,n}=Fibonacci, A_{2,13}=377; A_{4,n}=OEIS A005178), and exact-rational Berlekamp–Massey "
    "reads the true minimal order — which equals Stanley's bound EXACTLY for k=2..12 but is 112 < 128 = 2^7 at "
    "k=13. The deficiency 128−112 = 16 = deg(f₁₆) matches Guo–Tao's squared factor f₁₆². The Lean 4.31 kernel "
    "then DECIDES the disproof (plain decide, no native_decide; #print axioms reports NONE): on the even "
    "subsequence B_m=A_{13,2m} (order 56, Stanley bound 64), a monic order-56 recurrence annihilates B on 64 "
    "consecutive equations, so — since B obeys an order-≤64 recurrence — the minimal even order is ≤ 56 < 64. "
    "A corrupted coefficient is rejected by the same decide (negative control). The natural full formalization "
    "(order-112 recurrence over a 128-wide window of 10^130-digit integers) walls the decide big-literal limit "
    "(ADR 0047); the even subsequence plus a compact List.zipWith/foldl encoding bring it inside the kernel "
    "(~1.3 s). Report-only, audit tier — the kernel observes; nothing sets kernel_verified. LLMs propose "
    "nothing; exact arithmetic and the kernel decide."
)

_FINDINGS = [
    {"id": "counterexample", "claim": "Stanley's 1985 dimer conjecture is FALSE at k=13 (minimal order 112 < 128)",
     "verdict": "REFUTED",
     "note": "Exact tiling counts + exact Berlekamp–Massey: the minimal linear-recurrence order equals "
             "Stanley's 2^⌊(k+1)/2⌋ for k=2..12 but is 112 (< 2^7=128) at k=13 — the smallest counterexample. "
             "Deficiency 16 = deg(f₁₆), matching Guo–Tao's repeated factor f₁₆²."},
    {"id": "kernel-decided", "claim": "The Lean 4.31 kernel decides the disproof, axiom-free",
     "verdict": "CERTIFIED",
     "note": "On B_m=A_{13,2m} (order 56, Stanley bound 64) a monic order-56 recurrence annihilates B on 64 "
             "consecutive equations; plain decide, #print axioms NONE ⇒ minimal even order ≤ 56 < 64. A "
             "corrupted coefficient is rejected (negative control). Compact List encoding beats the decide wall."},
    {"id": "scope", "claim": "Smallest counterexample only; the infinite families are not replayed", "verdict": "NOTED",
     "note": "The Guo–Tao families k=14h−1, 30h−1 (next k=27, 29) need 2^13/2^14-state DPs and wider windows "
             "beyond cheap CPU; the closed-form infinite argument is not re-derived. Report-only; no trust surface."},
]

_ARTIFACTS = [
    downloadable_artifact(_CERT, cycle_id="cycle_000020", kind="lean-proof",
                          checker="Lean 4.31 kernel (plain decide; #print axioms clean)",
                          result="theorem stanley_dimer13_even_order_le_56 accepted; 64-equation window "
                                 "annihilated; does not depend on any axioms"),
]

_REFERENCES = [
    {"citation": ("Guo, Q.-H., & Tao, T. (2026). Repeated roots of Stanley's dimer-covering denominators, "
                  "disproving a 1985 conjecture (arXiv:2605.28195). arXiv."),
     "url": "https://arxiv.org/abs/2605.28195"},
    {"citation": ("Stanley, R. P. (1985). On dimer coverings of rectangles of fixed width. Discrete Applied "
                  "Mathematics, 12(1), 81–87."),
     "url": "https://doi.org/10.1016/0166-218X(85)90042-0"},
    {"citation": ("Lai, C.-Y. (Ed.). (2024). Open Problems in Algebraic Combinatorics (Problem 33). Proceedings "
                  "of Symposia in Pure Mathematics, Vol. 110. American Mathematical Society."),
     "url": "https://www.ams.org/books/pspum/110/"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (Stanley dimer disproof)",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "docs/crt/stanley_dimer_13.lean + scripts/verify_stanley_dimer.py (exact DP + Berlekamp–Massey + "
             "Lean 4.31 decide)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=20, date="2026-07-05", domain="Combinatorics", kind="refutation",
        title="Kernel-attested disproof of Stanley's 1985 dimer conjecture at k=13 (Problem 33; Guo–Tao 2026)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_stanley_dimer_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/stanley_dimer_13.lean to public/artifacts/cycle_000020/."},
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

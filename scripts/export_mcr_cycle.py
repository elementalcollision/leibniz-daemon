"""Emit the MCR-whitepaper-audit work-log entry for Codex Calculemus (*Il Lavoro* /
`/cycles`, ADR 0017).

The audit is a *verification cycle*, not a promulgated law: it adjudicates a third
party's claims and reports verdicts. It therefore belongs in the work-log, never in
*Le Leggi* — it carries no `kernel_verified`, mints no edge, promulgates nothing.
Any kernel/Z3 result it references is a *reported* check by the tool named, tagged
by that tool (see `docs/audits/mcr-whitepaper-audit-2026-07-03.md` and the
reproducible artifacts `mcr_audit_artifacts.py` / `mcr_p4_not_derivable.lean`).

This script is the producer: it builds the cycle via `calculemus_site.cycle_payload`
and writes the ready-to-merge `cycles` fragment. Leibniz produces; the operator
commits it into the site repo's `ledger/calculemus.json` under `cycles[]` (the site
is the separate repo `elementalcollision/codex-calculemus`; see the publish note
`docs/audits/mcr-codex-cycle-publish.md`).

Run:  python scripts/export_mcr_cycle.py            # print the cycle fragment
      python scripts/export_mcr_cycle.py -o FILE    # also write it to FILE
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload  # noqa: E402

# Public-safe: describes artifacts by name + checker + result only; no internal repo
# paths reach the public site (the internal report warns against posting those).
_FINDINGS = [
    {"id": "P1", "claim": "Theorem 1 — 'level invariance'", "verdict": "VACUOUS",
     "note": "It is the free theorem: the learn/predict naturality square commutes for the real "
             "counter AND for a no-op stub that learns and predicts nothing — insensitive to the body."},
    {"id": "P2", "claim": "Corollary 1 — universality syllogism", "verdict": "REFUTED",
     "note": "Under the honest reading (Theorem 1 gives Representable ⇒ Runnable, not ε-Learnable), "
             "P1 & P2 ⊬ C; Z3 finds a countermodel (SAT). Only an equivocated P2 rescues the entailment."},
    {"id": "P3", "claim": "Order-1 error floor (flagship)", "verdict": "REFUTED",
     "note": "Counterexample proved: on the mode-X/Y stream the error floor at the ambiguous state a is "
             "min(q, 1−q) > 0 (unconditional per-symbol ≈ half that, still > 0); Z3 returns UNSAT on the "
             "negation, so the floor holds for every q ∈ (0,1)."},
    {"id": "P4", "claim": "Derivability claim", "verdict": "REFUTED (Lean)",
     "note": "A map that is at once strictly increasing (count) and constant (assign) on a LinearOrder is a "
             "subsingleton; on ℤ it forces 0 = 1. Kernel-checked in Lean 4.31 + Mathlib, 0 errors, 0 sorry."},
    {"id": "P5", "claim": "Entropy bound E ≤ log₂ N", "verdict": "ILL-POSED",
     "note": "Surprisal E = −log₂ p(w) is bounded by log₂(corpus size), not log₂ N. A hapax in a 10⁶-token, "
             "N=100 vocabulary gives E ≈ 19.93 > log₂100 ≈ 6.64 — a ~13.3-bit violation."},
    {"id": "P6", "claim": "Sample-complexity bound", "verdict": "TRUE-BUT-WEAKER",
     "note": "The two-sided Hoeffding constant is ln(2/δ); with the missing union bound the corrected total "
             "is O(N ln N), which SURVIVES (ln(2N/δ) = ln(2/δ) + ln N). Weaker than stated, not false."},
    {"id": "P7", "claim": "§13 AGI conclusion", "verdict": "NOT-PROVEN",
     "note": "Deliberately downgraded from REFUTED: the AGI claim is unsupported by Theorems 1–4, not shown "
             "false. The honest verdict is that nothing in the formal core reaches it."},
    {"id": "P8", "claim": "The steelman — provable weaker statement", "verdict": "PROVEN",
     "note": "The one genuinely-true statement the work can build from — a valid but exponentially-costly "
             "weaker claim. Offered as the constructive path, not as support for §13."},
]

_ARTIFACTS = [
    {"name": "mcr_p4_not_derivable.lean", "kind": "lean-proof",
     "checker": "Lean 4.31 kernel + Mathlib", "result": "0 errors, 0 sorry"},
    {"name": "mcr_audit_artifacts.py", "kind": "smt+exact-numeric",
     "checker": "Z3 4.16.0 + exact rational arithmetic", "result": "all reproducible artifacts GREEN: True"},
]

_SUMMARY = (
    "An external formal-verification pass over the MCR whitepaper — its four theorems and the §13 conclusion, "
    "adjudicated by machine, not by judgement. Eight problems (P1–P8) were checked with Z3 4.16.0 and the "
    "Lean 4.31 kernel. Theorem 1 is the free theorem, holding even for a no-op stub (vacuous); the "
    "universality syllogism is invalid (Z3 countermodel); the order-1 error floor min(q, 1−q) > 0 is proven "
    "(Z3 UNSAT on its negation); the derivability claim collapses to 0 = 1 on the integers (Lean, 0 sorry); "
    "the entropy bound is ill-posed (a hapax exceeds log₂N by ~13 bits); the sample-complexity bound is true "
    "but weaker (O(N ln N) survives the union bound). The §13 AGI conclusion is left NOT-PROVEN — unsupported, "
    "not shown false — and one genuinely-true, exponentially-costly weaker statement (P8) is proven as the "
    "honest thing the work can build from. Nothing in Theorems 1–4 supports the AGI conclusion; every verdict "
    "is backed by a re-runnable artifact."
)


def build_cycle() -> dict:
    return cycle_payload(
        cycle=2,  # the illustrative entry is Cycle 1; renumber to the next int in your ledger if needed
        date="2026-07-03",
        domain="Formal verification",
        kind="audit",
        title="Independent formal-verification audit of the MCR whitepaper (Z3 + Lean)",
        summary=_SUMMARY,
        findings=_FINDINGS,
        artifacts=_ARTIFACTS,
    )


def main(argv: list[str]) -> int:
    cycle = build_cycle()
    fragment = {"cycles": [cycle]}
    text = json.dumps(fragment, indent=2, ensure_ascii=False) + "\n"
    if "-o" in argv:
        i = argv.index("-o")
        out = Path(argv[i + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        print(f"wrote {out}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

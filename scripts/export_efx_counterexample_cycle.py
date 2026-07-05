"""Emit the exact-census confirmation of the first EFX-nonexistence counterexample (Akrami, Mayorov, Mehlhorn,
Srinivas & Weidenbach 2026) as a Codex Calculemus cycle (ADR 0017). New domain: fair division. Producer only.

Run:  python scripts/export_efx_counterexample_cycle.py [-o FILE]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.calculemus_site import cycle_payload, downloadable_artifact  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_ARTIFACT = _ROOT / "scripts" / "verify_efx_counterexample.py"

_SUMMARY = (
    "A landmark 2026 result in a domain new to the ledger — fair division / discrete allocation — independently "
    "confirmed by exact exhaustive census. Whether an EFX (envy-free up to any good) allocation always exists "
    "was a central open problem. Akrami, Mayorov, Mehlhorn, Srinivas & Weidenbach (arXiv:2604.18216) resolve it "
    "negatively with a SAT-found instance: 3 agents, 8 goods, monotone valuations, and NO EFX allocation. Each "
    "agent i's valuation vᵢ is ordinal — vᵢ(A) is the rank (0..255) of the subset A in agent i's linear order "
    "over the 2⁸ = 256 subsets. Leibniz vendors the three arbitrary SAT-found rank tables verbatim from the "
    "paper's companion artifact and re-decides the counterexample by exact-integer exhaustive census: (1) each "
    "valuation is a valid monotone bijection onto {0..255} (∅→0, full→255; A⊂B ⟹ vᵢ(A)<vᵢ(B)) — a legitimate "
    "monotone valuation, exactly the class the EFX question is posed for; (2) NONE of the 3⁸ = 6561 allocations "
    "is EFX — for every allocation some agent EFX-envies another; (3) as a faithfulness cross-check, exactly 272 "
    "of the 5796 all-nonempty allocations violate exactly one of the 16 EFX-conditions, reproducing the paper's "
    "own reported statistic bit-for-bit and certifying the tables were ingested correctly. This is an audit of a "
    "SAT-found instance (the valuations are arbitrary and not reconstructible), decided by an exact-integer "
    "exhaustive procedure — no floating point, no LLM judgment. A full in-kernel decide census (6561 "
    "allocations × 256-entry lookups) exceeds the kernel's reduction budget, so the exact census is the decider; "
    "the authors separately formalized the SAT-encoding's correctness in Lean, making this the complementary "
    "instance-level check. Report-only, audit tier — no trust surface. LLMs propose nothing; an exact decision "
    "procedure decides."
)

_FINDINGS = [
    {"id": "no-efx",
     "claim": "EFX allocations need not exist: an explicit 3-agent, 8-good monotone instance has no EFX allocation",
     "verdict": "CERTIFIED",
     "note": "Exact census: 0 of the 3⁸=6561 allocations is EFX; every allocation has an EFX-envy that removing "
             "any single good does not eliminate. Resolves a central open problem in fair division (negatively)."},
    {"id": "valid-instance",
     "claim": "The three valuations are valid monotone ordinal valuations", "verdict": "CERTIFIED",
     "note": "Each is a bijection onto {0..255} with ∅→0, full→255, and A⊂B ⟹ vᵢ(A)<vᵢ(B) — verified over all "
             "256 subsets and all subset pairs. Monotone ⇒ the counterexample also covers submodular valuations."},
    {"id": "faithfulness",
     "claim": "Ingested tables reproduce the paper's statistics bit-for-bit", "verdict": "NOTED",
     "note": "5796 all-nonempty allocations, of which exactly 272 violate exactly one of the 16 EFX-conditions "
             "— matching the paper. A single mis-ingested rank would almost surely perturb this count."},
]

_ARTIFACTS = [
    downloadable_artifact(_ARTIFACT, cycle_id="cycle_000024", kind="python-verifier",
                          checker="exact-integer exhaustive EFX census over all 3^8 allocations",
                          result="0 EFX allocations of 6561; valuations valid monotone bijections; 272 of 5796 "
                                 "nonempty allocations violate exactly one EFX-condition (matches paper)"),
]

_REFERENCES = [
    {"citation": ("Akrami, H., Mayorov, A., Mehlhorn, K., Srinivas, S., & Weidenbach, C. (2026). A "
                  "counterexample to EFX: n ≥ 3 agents, m ≥ n + 5 items, submodular valuations via SAT-solving "
                  "(arXiv:2604.18216). arXiv."),
     "url": "https://arxiv.org/abs/2604.18216"},
]

_REPOSITORIES = [
    {"name": "elementalcollision/leibniz-daemon (EFX counterexample audit)",
     "url": "https://github.com/elementalcollision/leibniz-daemon",
     "role": "produced",
     "note": "scripts/verify_efx_counterexample.py + docs/crt/efx/Val{0,1,2}ByCard.txt (exact exhaustive census "
             "over the vendored valuation tables)"},
]

_TARGET = "elementalcollision/codex-calculemus : ledger/calculemus.json -> cycles[]"


def build_cycle() -> dict:
    return cycle_payload(
        cycle=24, date="2026-07-05", domain="Fair division", kind="verification",
        title="Exact-census confirmation of the first EFX-nonexistence counterexample (Akrami–Mayorov–Mehlhorn–Srinivas–Weidenbach 2026)",
        summary=_SUMMARY, findings=_FINDINGS, artifacts=_ARTIFACTS, references=_REFERENCES,
        repositories=_REPOSITORIES)


def build_fragment(*, generated_at: str = "") -> dict:
    return {"meta": {"generated_at": generated_at, "producer": "scripts/export_efx_counterexample_cycle.py",
                     "target": _TARGET,
                     "merge": "append to cycles[]; copy docs/crt/efx/Val{0,1,2}ByCard.txt to public/artifacts/cycle_000024/."},
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

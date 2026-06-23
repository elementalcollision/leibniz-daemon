"""Demonstrate the ADR 0029 v2 repair PANEL promulgating soundly under N+1=2 — BILLABLE.

Runs `RepairingDemonstrate` with an EMPTY base consensus (contributes 0 votes) and a real
two-reasoner panel (opus + an OpenRouter model, default gpt-5.5) on known-non-trivial goals.
If BOTH reasoners independently kernel-prove a goal, the panel satisfies N+1=2 on its own and
the candidate promulgates — each proof verified by `discharge` (the sole stamper). This
isolates the panel's new capability from the stochastic discovery funnel.

Usage (needs ANTHROPIC_API_KEY + OPENROUTER_API_KEY in .env + the Lean image):
    python scripts/measure_panel.py            # default known-closeable goals
    python scripts/measure_panel.py "theorem t (n:Nat) : (2*n)*(2*n+1)*(2*n+2) % 8 = 0"
Env: LEIBNIZ_REPAIR_PANEL (default openai/gpt-5.5), LEIBNIZ_REPAIR_ROUNDS (default 1).
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_REPO = Path(__file__).resolve().parent.parent

_DEFAULT_GOALS = [
    "theorem panel_div8 (n : Nat) : (2*n) * (2*n+1) * (2*n+2) % 8 = 0",
    "theorem panel_div3 (n : ℕ) : (n^3 + 5*n) % 3 = 0",
]


def main() -> int:
    from leibniz.env import load_env
    load_env(_REPO / ".env")

    from leibniz.backends import lean_repl
    from leibniz.backends.lean_cli import LeanCliBackend
    from leibniz.consensus import ConsensusResult
    from leibniz.cost import CostBudget
    from leibniz.proof_repair import ProofRepairer, RepairingDemonstrate
    from leibniz.propositio import Enuntiatio, Expressio, Propositio
    from leibniz.providers.anthropic_provider import AnthropicProvider
    from leibniz.providers.openrouter_provider import OpenRouterProvider
    from leibniz.trust import PROOF_EDGE
    from leibniz.types import ClaimType, EdgeEvidence, TrustTier, Verdict
    from leibniz.verifiers import LeanVerifier

    if not (os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("OPENROUTER_API_KEY")):
        print("[measure_panel] need ANTHROPIC_API_KEY and OPENROUTER_API_KEY in .env.")
        return 2

    goals = sys.argv[1:] or _DEFAULT_GOALS
    rounds = int(os.environ.get("LEIBNIZ_REPAIR_ROUNDS", "1") or 1)
    panel_model = os.environ.get("LEIBNIZ_REPAIR_PANEL", "openai/gpt-5.5").split(",")[0].strip()
    meter = CostBudget.from_env()
    backend = lean_repl.LeanReplBackend() if lean_repl.available() else LeanCliBackend()
    lean = LeanVerifier(backend)

    primary = ProofRepairer(provider=AnthropicProvider(meter=meter, max_tokens=4096),
                            lean=lean, max_rounds=rounds, identity="repair:claude-opus-4-8")
    member = ProofRepairer(provider=OpenRouterProvider(model=panel_model, meter=meter, max_tokens=4096),
                           lean=lean, max_rounds=rounds, identity=f"repair:{panel_model}")

    @dataclass
    class _EmptyConsensus:
        """Base ensemble that always comes up short with ZERO verifiers, so the panel must
        supply BOTH N+1 votes itself."""
        min_consensus: int = 2
        obligation: str = "claim"
        lean: object = None

        def prove(self, expr):
            edge = EdgeEvidence(edge=PROOF_EDGE, tier=TrustTier.MECHANICAL, verdict=Verdict.FAIL,
                                detail={"consensus": 0}, cost_units=0.0)
            return ConsensusResult(0, self.min_consensus, 2, edge, None, frozenset(), None)

    dem = RepairingDemonstrate(_EmptyConsensus(lean=lean), primary, panel=(member,))
    print(f"[measure_panel] panel [claude-opus-4-8, {panel_model}], rounds {rounds}, "
          f"empty base, N+1=2; {len(goals)} goal(s). BILLABLE.")

    promulgated = 0
    for i, goal in enumerate(goals):
        print(f"\n[measure_panel] goal {i}: {goal[:110]}")
        prop = Propositio(
            enuntiatio=Enuntiatio(statement="c", claim_type=ClaimType.INVARIANT, falsifiable_claim="n"),
            expressio=Expressio(theorem_src=goal, imports=("Mathlib.Tactic",)),
        )
        t0 = time.time()
        dem.run(prop)
        dt = time.time() - t0
        edges = [e for e in prop.edges if e.edge == PROOF_EDGE]
        e = edges[-1] if edges else None
        if e and e.verdict is Verdict.PASS:
            promulgated += 1
            # independent re-verification of the attached proof (belt-and-suspenders)
            demo2 = type(prop.demonstratio)(proof_obligation="reverify", proof_src=prop.demonstratio.proof_src)
            lean.discharge(prop.expressio, demo2)   # sole stamper; sets demo2.kernel_verified
            print(f"  → PROMULGATED ({dt:.0f}s): consensus={e.detail.get('consensus')}, "
                  f"models={e.detail.get('repair_models')}; re-verify={'Q.E.D.' if demo2.kernel_verified else 'REJECT'}")
            print(f"     proof: {(prop.demonstratio.proof_src or '')[:160]}")
        else:
            print(f"  → not promulgated ({dt:.0f}s) — both reasoners did not independently close it")

    if hasattr(backend, "close"):
        backend.close()
    print(f"\n[measure_panel] {promulgated}/{len(goals)} promulgated via the panel "
          f"(two distinct reasoners, kernel-verified). cost ${meter.spent_usd:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

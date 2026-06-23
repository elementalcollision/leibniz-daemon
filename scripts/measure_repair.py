"""Targeted reach test for the ADR 0029 agentic repair loop — BILLABLE.

Runs the IN-HOUSE repair loop (a frontier reasoner drafting + repairing against our own
kernel's error, `leibniz/proof_repair.py::ProofRepairer`) directly on hard goals, and
reports what it closes. Unlike `calibrate_discovery.py` (which measures repair's effect
through the whole discovery funnel, where most candidates die in the cheap gates before
ever reaching proof), this isolates repair's RAW proving reach on goals that are already
valid Lean and already known to be non-trivial.

The headline comparison is the Aristotle harvest: Harmonic Aristotle (a hosted agentic
prover) closed 3/3 of the daemon's real near-misses and our kernel re-verified each. This
asks the same question of our OWN loop (Claude + our kernel, no hosted agent): does an
in-house scaffold reach the same goals? `discharge` is still the sole `kernel_verified`
writer, so every "closed" here is a genuine kernel Q.E.D.

Usage (needs ANTHROPIC_API_KEY in .env + the Lean image; extras: propose,verify):
    python scripts/measure_repair.py --aristotle-goals       # head-to-head: the 3 Aristotle closed
    python scripts/measure_repair.py --from-memory 5         # N real daemon LEAN near-misses
    python scripts/measure_repair.py "theorem t (n:Nat) : (n^3 + 5*n) % 6 = 0"
Env: LEIBNIZ_REPAIR_ROUNDS (default 2), LEIBNIZ_REPAIR_MODEL (default the conjecture model).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_REPO = Path(__file__).resolve().parent.parent

# The exact goals Harmonic Aristotle closed (and our kernel re-verified) in the harvest —
# the daemon's own near-misses. Re-running the in-house loop on these is a clean head-to-head.
_ARISTOTLE_GOALS = [
    "theorem n_cubed_plus_five_n_div_six (n : Nat) : (n^3 + 5*n) % 6 = 0",
    "theorem prod_four_consecutive_even_start_div_four (n : ℕ) : 4 ∣ (2*n)*(2*n+1)*(2*n+2)*(2*n+3)",
    "theorem n_np1_2np1_div_six (n : Nat) : n * (n + 1) * (2 * n + 1) % 6 = 0",
]


def _goals(argv: list[str]) -> list[str]:
    if argv and argv[0] == "--aristotle-goals":
        return list(_ARISTOTLE_GOALS)
    if len(argv) >= 2 and argv[0] == "--from-memory":
        # The daemon's LEAN near-misses: candidates that reached formalization but the
        # kernel never closed (most-recent-first, deduped). Same source as try_aristotle.
        from leibniz.runtime import PersistentRuntime
        n = int(argv[1])
        seen: set[str] = set()
        out: list[str] = []
        for p in PersistentRuntime().recall_recent(200):
            ts = p.expressio.theorem_src if p.expressio else None
            if not ts or ts in seen or (p.demonstratio and p.demonstratio.kernel_verified):
                continue
            seen.add(ts)
            out.append(ts)
            if len(out) >= n:
                break
        return out
    return [argv[0]] if argv else []


def main() -> int:
    from leibniz.env import load_env
    load_env(_REPO / ".env")

    goals = _goals(sys.argv[1:])
    if not goals:
        print(__doc__)
        return 2

    from leibniz.backends import lean_repl
    from leibniz.backends.lean_cli import LeanCliBackend
    from leibniz.cost import CostBudget
    from leibniz.propositio import Expressio
    from leibniz.proof_repair import ProofRepairer
    from leibniz.providers.anthropic_provider import AnthropicProvider
    from leibniz.verifiers import LeanVerifier

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[measure_repair] ANTHROPIC_API_KEY not set (.env).")
        return 2

    from leibniz.assembly import frontier_reasoner

    rounds = int(os.environ.get("LEIBNIZ_REPAIR_ROUNDS", "2") or 2)
    model = os.environ.get("LEIBNIZ_REPAIR_MODEL") or os.environ.get(
        "LEIBNIZ_CONJECTURE_MODEL", "claude-opus-4-8")
    meter = CostBudget.from_env()
    # Frontier reasoner with failover (ADR 0029): Anthropic primary, OpenRouter backups when
    # it is down. So this measures the SCAFFOLD's reach even during an Anthropic outage; the
    # model that actually closes each goal is recorded (last_used).
    primary = AnthropicProvider(model=model, meter=meter, max_tokens=4096)
    provider = frontier_reasoner(primary, meter=meter)
    chain = getattr(provider, "providers", [primary])
    chain_desc = ", ".join(str(getattr(p, "model", type(p).__name__)) for p in chain)
    # The repairer discharges through (and reads kernel errors from) the SAME verifier the
    # daemon uses: REPL when available (import-cached), else the CLI kernel. discharge stays
    # the sole kernel_verified writer — every "closed" below is a real Q.E.D.
    backend = lean_repl.LeanReplBackend() if lean_repl.available() else LeanCliBackend()
    lean = LeanVerifier(backend)
    repairer = ProofRepairer(provider=provider, lean=lean, max_rounds=rounds)

    print(f"[measure_repair] in-house repair loop — reasoner chain [{chain_desc}], "
          f"max_rounds {rounds}, backend {'REPL' if lean_repl.available() else 'CLI'}; "
          f"{len(goals)} goal(s). BILLABLE.")
    closed = 0
    per_goal = []
    t0 = time.time()
    for i, goal in enumerate(goals):
        print(f"\n[measure_repair] goal {i}: {goal[:120]}")
        g0 = time.time()
        try:
            out = repairer.prove(Expressio(theorem_src=goal, imports=("Mathlib.Tactic",)))
        except Exception as e:  # surface unexpected issues; a goal must not abort the run
            print(f"  ! error: {type(e).__name__}: {e}")
            per_goal.append({"goal": goal, "closed": False, "error": repr(e)})
            continue
        dt = time.time() - g0
        if out is None:
            print(f"  → NOT closed after {rounds} repair round(s) ({dt:.0f}s)")
            per_goal.append({"goal": goal, "closed": False, "seconds": round(dt, 1)})
            continue
        demo, ev = out
        rnd = repairer.stats.rounds_to_close[-1] if repairer.stats.rounds_to_close else None
        used = getattr(provider, "last_used", None) or model  # which reasoner closed it
        closed += 1
        verb = "initial draft" if rnd == 0 else f"repair round {rnd}"
        print(f"  → Q.E.D. via {verb} by {used} ({dt:.0f}s); "
              f"kernel_verified={demo.kernel_verified}, verdict={ev.verdict.name}")
        print(f"     proof: {(demo.proof_src or '')[:200]}")
        per_goal.append({"goal": goal, "closed": True, "round": rnd, "model": used,
                         "seconds": round(dt, 1), "proof": demo.proof_src})

    elapsed = time.time() - t0
    s = repairer.stats.as_dict()
    if hasattr(backend, "close"):
        backend.close()

    print("\n" + "=" * 64)
    print("REPAIR REACH SUMMARY (ADR 0029)")
    print("=" * 64)
    print(f"  closed (re-verified by our kernel): {closed}/{len(goals)}")
    print(f"  rounds_to_close:  {s['rounds_to_close']}  (0 = closed on the initial draft)")
    print(f"  repair rounds spent: {s['repairs']}  over {s['attempted']} attempt(s)")
    print(f"  elapsed: {elapsed:.0f}s")
    if meter is not None:
        print(f"  cost: ${meter.spent_usd:.4f} ({meter.input_tokens}+{meter.output_tokens} tok)")
    # Guard against a silent provider failure being misread as "repair can't prove these":
    # the loop swallows provider exceptions (defensive), so 0 closed + 0 tokens means the
    # reasoner never actually answered (auth / transient API outage), NOT a reach result.
    if s["attempted"] > 0 and meter is not None and meter.input_tokens == 0:
        print("  ⚠ WARNING: 0 tokens spent across all attempts — the reasoner made NO "
              "successful calls (API/key/transient failure). This is NOT a reach result; "
              "re-run before interpreting.")

    import json
    rep = _REPO / "repair_reach_report.json"
    rep.write_text(json.dumps({
        "closed": closed, "total": len(goals), "stats": s,
        "per_goal": per_goal, "elapsed_s": round(elapsed, 1), "model": model,
        "cost_usd": round(meter.spent_usd, 4) if meter else None,
    }, indent=2) + "\n")
    print(f"\n[measure_repair] wrote {rep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

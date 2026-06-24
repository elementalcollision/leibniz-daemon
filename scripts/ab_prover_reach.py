"""A/B the prover ensemble on FIXED goals — does a candidate prover pull its weight? BILLABLE.

`calibrate_discovery.py` measures a prover change through the WHOLE funnel, where stochastic
conjectures confound the comparison (arm B sees different goals than arm A). This isolates the
prover question: run the SAME fixed goals through TWO prover sets under N+1 consensus and
ATTRIBUTE the closes per prover — so you can tell whether e.g. Goedel-Prover-V2 closes goals the
incumbent set misses, and in how many it was DECISIVE (consensus would have failed without it).

This is the validity test to run BEFORE committing a new prover to organic/PROD runs — and the
textbook UAT experiment: run it on the isolated UAT instance; PROD's ledger is never touched.
`LeanVerifier.discharge` stays the sole `kernel_verified` writer — every "closed" is a real Q.E.D.

Goals: formalized `theorem_src` pulled from a prior run's ledger (the real conjecture mix).

Usage (needs the Lean image + creds; extras: propose,verify):
    LEIBNIZ_AB_PROVERS_A="deepseek/deepseek-prover-v2,deepseek/deepseek-prover-v2,anthropic/claude-opus-4-8" \\
    LEIBNIZ_AB_PROVERS_B="deepseek/deepseek-prover-v2,Goedel-LM/Goedel-Prover-V2-32B@featherless,anthropic/claude-opus-4-8" \\
    LEIBNIZ_GATEWAY_FEATHERLESS_URL=https://api.featherless.ai/v1/chat/completions \\
    python scripts/ab_prover_reach.py /tmp/organic3_memory.db 12

Env: LEIBNIZ_PROOF_CONSENSUS (default 2); FEATHERLESS_API_KEY in .env. One trial per goal per
arm — the close-RATE over N goals averages prover stochasticity across goals, not within one.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_REPO = Path(__file__).resolve().parent.parent

# Default arms: the control is the current organic config (deepseek twice + opus = 2 voters);
# the treatment swaps the redundant deepseek for Goedel on Featherless (3 distinct voters).
_DEFAULT_A = "deepseek/deepseek-prover-v2,deepseek/deepseek-prover-v2,anthropic/claude-opus-4-8"
_DEFAULT_B = ("deepseek/deepseek-prover-v2,Goedel-LM/Goedel-Prover-V2-32B@featherless,"
              "anthropic/claude-opus-4-8")


def _candidate_models(arm_a: str, arm_b: str) -> set[str]:
    """Models in B but not A — the change under test (e.g. {Goedel-...})."""
    norm = lambda s: {m.strip().split("@", 1)[0] for m in s.split(",") if m.strip()}  # noqa: E731
    return norm(arm_b) - norm(arm_a)


def summarize_ab(rows: list[dict], candidates: set[str]) -> dict:
    """Pure attribution over per-goal A/B results (CI-tested; no I/O).

    Each row: {goal, a: {reached, identities, count, required}, b: {...}} where `identities` is
    the list of `model:<name>` strings that produced a kernel proof for that goal/arm.

    Reports per-arm reach, B-only unlocks, and — the headline validity signal — how many of
    those B-only unlocks the CANDIDATE model(s) actually closed, plus goals where a candidate
    was DECISIVE (a closer AND consensus was exactly at threshold, so dropping it fails)."""
    def _models(ids):
        return {i.split("model:", 1)[-1] for i in ids if i.startswith("model:")}

    reach_a = sum(1 for r in rows if r["a"]["reached"])
    reach_b = sum(1 for r in rows if r["b"]["reached"])
    b_only = [r for r in rows if r["b"]["reached"] and not r["a"]["reached"]]
    a_only = [r for r in rows if r["a"]["reached"] and not r["b"]["reached"]]
    cand_closed_b_only = sum(1 for r in b_only if _models(r["b"]["identities"]) & candidates)
    # decisive: candidate is a closer AND removing one closer drops below the bar (count==required)
    cand_decisive = sum(
        1 for r in rows
        if (_models(r["b"]["identities"]) & candidates) and r["b"]["count"] == r["b"]["required"]
    )
    per_prover_b: dict[str, int] = {}
    for r in rows:
        for m in _models(r["b"]["identities"]):
            per_prover_b[m] = per_prover_b.get(m, 0) + 1
    per_prover_a: dict[str, int] = {}
    for r in rows:
        for m in _models(r["a"]["identities"]):
            per_prover_a[m] = per_prover_a.get(m, 0) + 1
    return {
        "goals": len(rows),
        "reached_A": reach_a, "reached_B": reach_b,
        "b_only_unlocks": len(b_only), "a_only_regressions": len(a_only),
        "candidate_closed_b_only": cand_closed_b_only,
        "candidate_decisive": cand_decisive,
        "candidates": sorted(candidates),
        "closes_per_prover_A": dict(sorted(per_prover_a.items())),
        "closes_per_prover_B": dict(sorted(per_prover_b.items())),
    }


def _goals_from_db(db_path: str, n: int) -> list[str]:
    """Formalized theorem_src from a prior run's ledger (deduped, most-recent-first)."""
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT theorem_src FROM memory WHERE theorem_src IS NOT NULL ORDER BY ts DESC"
    ).fetchall()
    con.close()
    seen: set[str] = set()
    out: list[str] = []
    for (ts,) in rows:
        if ts and ts not in seen:
            seen.add(ts)
            out.append(ts)
        if len(out) >= n:
            break
    return out


def _run_arm(models: str, goals: list[str], meter, lean, min_consensus: int) -> list[dict]:
    """Build the arm's ensemble and run every goal through N+1 consensus; return per-goal rows."""
    from leibniz.assembly import prover_ensemble
    from leibniz.consensus import ProofConsensus
    from leibniz.propositio import Expressio

    os.environ["LEIBNIZ_PROVER_MODELS"] = models
    os.environ.pop("LEIBNIZ_HF_PROVER_MODELS", None)  # force the OpenRouter/generic path
    consensus = ProofConsensus(provers=prover_ensemble(meter=meter), lean=lean,
                               min_consensus=min_consensus)
    out = []
    for g in goals:
        try:
            res = consensus.prove(Expressio(theorem_src=g, imports=("Mathlib.Tactic",)))
            out.append({"reached": res.reached, "count": res.count, "required": res.required,
                        "identities": sorted(res.identities)})
        except Exception as e:  # a goal must not abort the run
            out.append({"reached": False, "count": 0, "required": min_consensus,
                        "identities": [], "error": repr(e)})
    return out


def main() -> int:
    from leibniz.env import load_env
    load_env(_REPO / ".env")

    args = sys.argv[1:]
    db = args[0] if args else str(_REPO / ".leibniz" / "memory.db")
    n = int(args[1]) if len(args) > 1 else 12
    if not Path(db).exists():
        print(f"[ab_prover] ledger not found: {db}\n{__doc__}")
        return 2
    goals = _goals_from_db(db, n)
    if not goals:
        print(f"[ab_prover] no formalized goals in {db}")
        return 2

    arm_a = os.environ.get("LEIBNIZ_AB_PROVERS_A") or _DEFAULT_A
    arm_b = os.environ.get("LEIBNIZ_AB_PROVERS_B") or _DEFAULT_B
    candidates = _candidate_models(arm_a, arm_b)
    min_consensus = int(os.environ.get("LEIBNIZ_PROOF_CONSENSUS", "2") or 2)

    from leibniz.backends import lean_repl
    from leibniz.backends.lean_cli import LeanCliBackend
    from leibniz.cost import CostBudget
    from leibniz.verifiers import LeanVerifier

    meter = CostBudget.from_env()
    backend = lean_repl.LeanReplBackend() if lean_repl.available() else LeanCliBackend()
    lean = LeanVerifier(backend)

    print(f"[ab_prover] {len(goals)} goals from {db}; N+1={min_consensus}; "
          f"backend {'REPL' if lean_repl.available() else 'CLI'}. BILLABLE.")
    print(f"  arm A (control):   {arm_a}")
    print(f"  arm B (treatment): {arm_b}")
    print(f"  candidate(s) under test: {sorted(candidates) or '(none — B ⊆ A)'}")

    t0 = time.time()
    res_a = _run_arm(arm_a, goals, meter, lean, min_consensus)
    res_b = _run_arm(arm_b, goals, meter, lean, min_consensus)
    rows = [{"goal": g, "a": a, "b": b} for g, a, b in zip(goals, res_a, res_b)]
    summary = summarize_ab(rows, candidates)
    elapsed = time.time() - t0
    if hasattr(backend, "close"):
        backend.close()

    print("\n" + "=" * 64)
    print("PROVER A/B REACH SUMMARY")
    print("=" * 64)
    for k in ("goals", "reached_A", "reached_B", "b_only_unlocks", "a_only_regressions",
              "candidate_closed_b_only", "candidate_decisive"):
        print(f"  {k:24s} {summary[k]}")
    print(f"  closes/prover A: {summary['closes_per_prover_A']}")
    print(f"  closes/prover B: {summary['closes_per_prover_B']}")
    print(f"  elapsed {elapsed:.0f}s; cost ${meter.spent_usd:.4f} "
          f"({meter.input_tokens}+{meter.output_tokens} tok)")
    if meter.input_tokens == 0:
        print("  ⚠ WARNING: 0 tokens — provers made NO successful calls (auth/outage). "
              "NOT a reach result; re-run before interpreting.")

    out = _REPO / "ab_prover_reach_report.json"
    out.write_text(json.dumps({"summary": summary, "arm_a": arm_a, "arm_b": arm_b,
                               "rows": rows, "elapsed_s": round(elapsed, 1),
                               "cost_usd": round(meter.spent_usd, 4)}, indent=2) + "\n")
    print(f"\n[ab_prover] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

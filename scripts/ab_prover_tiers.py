"""Difficulty-tiered A/B prover-reach harness — finds where small provers plateau vs large ones.

Extends ``ab_prover_reach.py`` (reuses its pure functions) with a per-tier run:
- T0: elementary goals (decide/ring/omega-class)
- T1: AMC/AIME-flavored (divisibility / inequalities, several tactic steps)
- T2: Putnam/olympiad-flavored (multi-step, classical theorems)

The plateau is visible in the per-tier table: tier where arm-A reach collapses
while arm-B (with the larger prover) holds is the difficulty cliff.

Goal source: ``scripts/ab_goalsets/tiered.json`` — a STARTER set of original
kernel-verified Lean 4 goals. It is NOT the full miniF2F or PutnamBench benchmarks;
importing those is a follow-up task (see the JSON _meta.note field).

Usage (needs the Lean image + creds; extras: propose,verify):
    LEIBNIZ_GATEWAY_FEATHERLESS_URL=https://api.featherless.ai/v1/chat/completions \\
    LEIBNIZ_PROOF_CONSENSUS=1 \\
    python scripts/ab_prover_tiers.py \\
        --tiers scripts/ab_goalsets/tiered.json \\
        [--arm-a anthropic/claude-opus-4-8] \\
        [--arm-b Goedel-LM/Goedel-Prover-V2-32B@featherless,anthropic/claude-opus-4-8]

Env: LEIBNIZ_PROOF_CONSENSUS (default 2; use 1 for single-voter reach test);
     LEIBNIZ_AB_PROVERS_A / _B to override arms without re-typing the flags.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

# ---------------------------------------------------------------------------
# Reuse all pure functions from ab_prover_reach — no duplication.
# ---------------------------------------------------------------------------
_SPEC = importlib.util.spec_from_file_location(
    "ab_prover_reach", Path(__file__).resolve().parent / "ab_prover_reach.py"
)
_ab = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_ab)

summarize_ab = _ab.summarize_ab          # pure attribution math
liveness_probe = _ab.liveness_probe     # one tiny probe per prover
liveness_problems = _ab.liveness_problems
preflight = _ab.preflight
_build_ensemble = _ab._build_ensemble
_available_models = _ab._available_models
_run_arm = _ab._run_arm
_candidate_models = _ab._candidate_models
_DEFAULT_A = _ab._DEFAULT_A
_DEFAULT_B = _ab._DEFAULT_B

VALID_TIERS = ("T0", "T1", "T2")


# ---------------------------------------------------------------------------
# Tier-file loading and validation (pure — CI-safe, no I/O beyond file read)
# ---------------------------------------------------------------------------

class TierFileError(ValueError):
    """Raised when the tiered goal file is malformed."""


def load_tier_file(path: str | Path) -> dict[str, list[dict]]:
    """Load and validate a tiered goal JSON file.

    Returns a dict mapping tier name -> list of goal dicts with ``theorem_src``
    and ``imports`` keys. Raises ``TierFileError`` on schema violations.

    This function is pure (no network, no Lean) and is CI-tested.
    """
    p = Path(path)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TierFileError(f"invalid JSON in {path}: {exc}") from exc
    except OSError as exc:
        raise TierFileError(f"cannot read {path}: {exc}") from exc

    # Must have at least one tier key (underscore-prefixed keys are metadata)
    tier_keys = [k for k in raw if not k.startswith("_")]
    if not tier_keys:
        raise TierFileError(f"{path} contains no tier keys (got: {list(raw)})")

    tiers: dict[str, list[dict]] = {}
    for tier in tier_keys:
        goals = raw[tier]
        if not isinstance(goals, list):
            raise TierFileError(f"tier {tier!r} must be a list, got {type(goals).__name__}")
        for i, g in enumerate(goals):
            if not isinstance(g, dict):
                raise TierFileError(f"{tier}[{i}] must be a dict, got {type(g).__name__}")
            if "theorem_src" not in g:
                raise TierFileError(f"{tier}[{i}] missing 'theorem_src' key")
            if not isinstance(g.get("imports"), list):
                raise TierFileError(f"{tier}[{i}] 'imports' must be a list")
        tiers[tier] = goals
    return tiers


def aggregate_tiers(
    tier_rows: dict[str, list[dict]],
    candidates: set[str],
) -> dict[str, dict]:
    """Aggregate per-tier A/B rows into a per-tier summary dict.

    ``tier_rows`` maps tier -> list of {goal, a: {...}, b: {...}} rows (same
    shape as the rows passed to ``summarize_ab``). Returns a dict mapping
    tier name -> summarize_ab output dict plus tier-level goal count.

    Pure — no I/O, no network, CI-tested.
    """
    return {tier: summarize_ab(rows, candidates) for tier, rows in tier_rows.items()}


def plateau_tier(tier_summaries: dict[str, dict], tiers: list[str]) -> str | None:
    """Return the first tier where arm-A reach drops below arm-B reach (the plateau).

    Returns None if arm-A and arm-B track each other across all tiers (no plateau
    detected in this tier set), or if there is only one tier.

    Pure — CI-tested.
    """
    for tier in tiers:
        s = tier_summaries.get(tier, {})
        n = s.get("goals", 0)
        if n == 0:
            continue
        ra = s.get("reached_A", 0)
        rb = s.get("reached_B", 0)
        if rb > ra:
            return tier
    return None


# ---------------------------------------------------------------------------
# Pretty-print helpers
# ---------------------------------------------------------------------------

def _tier_table(summaries: dict[str, dict], tiers: list[str], elapsed: dict[str, float]) -> str:
    """Render a per-tier comparison table."""
    header = (
        f"{'Tier':<6} {'Goals':>5} {'Reach_A':>7} {'Reach_B':>7} "
        f"{'B-only':>6} {'Decisive':>8} {'Latency(s)':>10}"
    )
    sep = "-" * len(header)
    lines = [sep, header, sep]
    for tier in tiers:
        s = summaries.get(tier)
        if s is None:
            continue
        n = s["goals"]
        ra = s["reached_A"]
        rb = s["reached_B"]
        b_only = s["b_only_unlocks"]
        decisive = s["candidate_decisive"]
        lat = elapsed.get(tier, 0.0)
        flag = " <-- PLATEAU" if rb > ra else ""
        lines.append(
            f"{tier:<6} {n:>5} {ra:>7} {rb:>7} {b_only:>6} {decisive:>8} {lat:>10.1f}{flag}"
        )
    lines.append(sep)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    from leibniz.env import load_env
    load_env(_REPO / ".env")

    parser = argparse.ArgumentParser(
        description="Difficulty-tiered prover A/B reach — finds the plateau tier."
    )
    parser.add_argument(
        "--tiers",
        default=str(Path(__file__).parent / "ab_goalsets" / "tiered.json"),
        help="Path to tiered goal JSON file (default: scripts/ab_goalsets/tiered.json)",
    )
    parser.add_argument(
        "--arm-a",
        default=os.environ.get("LEIBNIZ_AB_PROVERS_A") or _DEFAULT_A,
        dest="arm_a",
        help="Arm A (control) — comma-separated model IDs",
    )
    parser.add_argument(
        "--arm-b",
        default=os.environ.get("LEIBNIZ_AB_PROVERS_B") or _DEFAULT_B,
        dest="arm_b",
        help="Arm B (treatment) — comma-separated model IDs",
    )
    parser.add_argument(
        "--output",
        default=str(_REPO / "ab_prover_tiers_report.json"),
        help="Where to write the JSON report",
    )
    args = parser.parse_args()

    # --- Load tier file -------------------------------------------------------
    try:
        tiers = load_tier_file(args.tiers)
    except TierFileError as e:
        print(f"[ab_tiers] TIER FILE ERROR: {e}")
        return 2

    tier_order = [t for t in VALID_TIERS if t in tiers]
    if not tier_order:
        tier_order = sorted(tiers)

    total_goals = sum(len(v) for v in tiers.values())
    print(f"[ab_tiers] loaded {len(tiers)} tiers, {total_goals} total goals from {args.tiers}")
    for t in tier_order:
        print(f"  {t}: {len(tiers[t])} goals")

    arm_a, arm_b = args.arm_a, args.arm_b
    candidates = _candidate_models(arm_a, arm_b)
    min_consensus = int(os.environ.get("LEIBNIZ_PROOF_CONSENSUS", "2") or 2)

    from leibniz.backends import lean_repl
    from leibniz.backends.lean_cli import LeanCliBackend
    from leibniz.cost import CostBudget
    from leibniz.providers import ProviderUnavailable
    from leibniz.verifiers import LeanVerifier

    meter = CostBudget.from_env()

    # --- Pre-flight -----------------------------------------------------------
    try:
        a_ens = _build_ensemble(arm_a, meter)
        b_ens = _build_ensemble(arm_b, meter)
    except ProviderUnavailable as e:
        print(f"[ab_tiers] PRE-FLIGHT FAILED (no billable calls made):\n  - {e}")
        return 2

    problems = preflight(
        _available_models(a_ens), _available_models(b_ens), candidates, min_consensus
    )
    if problems:
        print("[ab_tiers] PRE-FLIGHT FAILED (no billable calls made):")
        for p in problems:
            print(f"  - {p}")
        return 2

    # --- Liveness probe -------------------------------------------------------
    print("[ab_tiers] liveness probe (1 trivial call per distinct prover)...")
    live = liveness_probe([a_ens, b_ens])
    for model, (ok, detail) in sorted(live.items()):
        print(f"  {'ALIVE' if ok else 'DEAD '} {model}: {detail}")
    live_probs = liveness_problems(live, candidates)
    if live_probs:
        print("[ab_tiers] LIVENESS FAILED (aborting before the A/B loop):")
        for p in live_probs:
            print(f"  - {p}")
        return 2

    backend = lean_repl.LeanReplBackend() if lean_repl.available() else LeanCliBackend()
    lean = LeanVerifier(backend)

    print(f"\n[ab_tiers] BILLABLE — running {len(tier_order)} tiers × 2 arms × N+1={min_consensus}")
    print(f"  arm A (control):   {arm_a}")
    print(f"  arm B (treatment): {arm_b}")
    print(f"  candidate(s): {sorted(candidates) or '(none — B subset of A)'}")

    # --- Per-tier A/B loop ----------------------------------------------------
    tier_rows: dict[str, list[dict]] = {}
    tier_elapsed: dict[str, float] = {}

    for tier in tier_order:
        goals = [g["theorem_src"] for g in tiers[tier]]
        print(f"\n[ab_tiers] === {tier} ({len(goals)} goals) ===")
        t0 = time.time()
        res_a = _run_arm(a_ens, goals, lean, min_consensus)
        res_b = _run_arm(b_ens, goals, lean, min_consensus)
        elapsed_t = time.time() - t0
        tier_elapsed[tier] = elapsed_t
        rows = [
            {"goal": g, "a": a, "b": b}
            for g, a, b in zip(goals, res_a, res_b)
        ]
        tier_rows[tier] = rows
        s = summarize_ab(rows, candidates)
        print(
            f"  reached_A={s['reached_A']}/{s['goals']}  "
            f"reached_B={s['reached_B']}/{s['goals']}  "
            f"b_only={s['b_only_unlocks']}  decisive={s['candidate_decisive']}  "
            f"({elapsed_t:.0f}s)"
        )

    if hasattr(backend, "close"):
        backend.close()

    # --- Aggregate and report -------------------------------------------------
    summaries = aggregate_tiers(tier_rows, candidates)
    plateau = plateau_tier(summaries, tier_order)

    print("\n" + "=" * 64)
    print("TIERED PROVER A/B REACH SUMMARY")
    print("=" * 64)
    print(_tier_table(summaries, tier_order, tier_elapsed))
    if plateau:
        print(f"\nPLATEAU detected at tier {plateau}: arm-A reach falls behind arm-B.")
        print("Small provers cannot keep up — this is the difficulty cliff.")
    else:
        print("\nNo plateau detected — arm-A tracks arm-B across all tiers.")
        print("Consider adding harder tiers or more goals to find the cliff.")

    total_elapsed = sum(tier_elapsed.values())
    print(f"\n  total elapsed {total_elapsed:.0f}s; cost ${meter.spent_usd:.4f} "
          f"({meter.input_tokens}+{meter.output_tokens} tok)")
    if meter.input_tokens == 0:
        print("  WARNING: 0 tokens — provers made NO successful calls (auth/outage). "
              "NOT a reach result; re-run before interpreting.")

    report = {
        "arm_a": arm_a,
        "arm_b": arm_b,
        "candidates": sorted(candidates),
        "min_consensus": min_consensus,
        "tiers": tier_order,
        "plateau_tier": plateau,
        "summaries": summaries,
        "tier_elapsed_s": {t: round(v, 1) for t, v in tier_elapsed.items()},
        "total_elapsed_s": round(total_elapsed, 1),
        "cost_usd": round(meter.spent_usd, 4),
        "tier_rows": tier_rows,
    }
    out = Path(args.output)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\n[ab_tiers] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

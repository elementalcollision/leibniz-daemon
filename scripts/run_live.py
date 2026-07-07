"""Live end-to-end run (R4 exit test) — REAL backends, BILLABLE LLM calls.

Loads .env, builds the real daemon, turns one circadian cycle, prints the report,
and renders any promulgated law to Calculemus. Bounded by frontier/analogy limits
to keep cost in check.

Run (needs creds in .env + the Lean image + the propose/verify extras):
    python scripts/run_live.py [frontier_limit] [analogy_limit]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.assembly import build_daemon  # noqa: E402
from leibniz.calculemus import render_propositio  # noqa: E402
from leibniz.env import load_env  # noqa: E402
from leibniz.types import FinishReason  # noqa: E402


def main() -> int:
    frontier_limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    analogy_limit = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    loaded = load_env(Path(__file__).resolve().parent.parent / ".env")
    print(f"[run_live] loaded {loaded} env vars from .env")

    daemon = build_daemon(frontier_limit=frontier_limit, analogy_limit=analogy_limit)
    print("[run_live] turning one circadian cycle (LIVE — real LLM + kernel calls)...")
    report = daemon.circadian_cycle()

    print("\n=== CycleReport ===")
    print(f"  seeds:         {report.seeds}")
    print(f"  conjectured:   {report.conjectured}")
    print(f"  reached proof: {report.reached_proof}")
    print(f"  promulgated:   {report.promulgated}")
    print("  dispositions:")
    for reason, n in sorted(report.by_reason.items()):
        print(f"    {reason:<14} {n}")

    # The runtime persists every candidate to SQLite; recall the most recent and pick out
    # this cycle's promulgated laws by their DISPOSITION. A recalled memory carries
    # `finish_reason`, never the policy-gated `promulgated` flag (that is set only by the live
    # gate and never replayed from storage — see runtime._row_to_prop), so we filter on the
    # disposition and render the triad; we do NOT re-promulgate a historical record.
    recent = daemon.runtime.recall_recent(max(50, report.promulgated * 2))
    proven = [p for p in recent if p.finish_reason is FinishReason.PROMULGATED][: report.promulgated]
    for p in proven:
        print("\n=== PROMULGATED (kernel-checked) ===")
        print(render_propositio(p))
    if not proven:
        print("\n[run_live] No law promulgated this cycle — see dispositions above. "
              "The daemon ran end-to-end; discovery success is a tuning matter, not a "
              "trust-boundary failure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

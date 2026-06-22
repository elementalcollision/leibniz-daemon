"""Live calibration of the discovery frontier (ADR 0018) — REAL backends, BILLABLE.

Seeds the real daemon from the curated arXiv feed, turns instrumented cycles with
the full stack (Anthropic conjecture/formalize, the HuggingFace prover ensemble, the
Lean kernel under N+1 consensus, Z3), and measures actual outcomes against the
frontier controller — then recommends how to tune its constants to the prover's real
reach. Bounded by a USD cap and a small cycle/seed count.

The point is NOT "promulgate a theorem on the first run" — it is to measure where the
proposed difficulty sits relative to the prover's reach (the by_reason mix + the
frontier's success rate), so the band can be calibrated. Zero promulgations with a
clean failure spectrum is a valid, informative result.

Run (needs .env creds + Lean image + extras):
    python scripts/calibrate_discovery.py [cycles] [seeds_per_cycle] [cap_usd]
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_REPO = Path(__file__).resolve().parent.parent
_FEED = Path("/Users/dave/Agent_Data/Agents (Chimera, Newton, Leibniz)/arxiv_feed/feeds/latest/leibniz.json")
# Prover ensemble on HuggingFace (the specialized prover models live there).
_HF_PROVERS = "deepseek-ai/DeepSeek-Prover-V2-671B,deepseek-ai/DeepSeek-V3.2,deepseek-ai/DeepSeek-R1"


def _seed_from_record(rec: dict) -> str:
    title = (rec.get("title") or "").strip()
    abstract = (rec.get("abstract") or "").replace("\n", " ").strip()
    first = abstract.split(". ")[0][:240]
    work = ",".join(rec.get("work_items") or [])
    cat = rec.get("primary_category", "")
    return f"[{cat} · {work}] {title}. {first}"


class FeedSurvey:
    """Survey that yields conjecture seeds from the curated feed, highest
    seed_priority first, advancing a cursor each cycle."""

    def __init__(self, records: list[dict], batch: int):
        self.records = sorted(records, key=lambda r: r.get("seed_priority", 0), reverse=True)
        self.batch = batch
        self.cursor = 0

    def run(self, domain: str) -> list[str]:
        out, n = [], len(self.records)
        for _ in range(self.batch):
            if n == 0:
                break
            out.append(_seed_from_record(self.records[self.cursor % n]))
            self.cursor += 1
        return out


def main() -> int:
    cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    seeds_per_cycle = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    cap_usd = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0

    from leibniz.env import load_env  # noqa: E402
    load_env(_REPO / ".env")
    # Configure the run BEFORE build_daemon (it reads env): HF provers + USD cap.
    os.environ["LEIBNIZ_HF_PROVER_MODELS"] = _HF_PROVERS
    os.environ["LEIBNIZ_DAILY_USD_CAP"] = str(cap_usd)
    os.environ.setdefault("LEIBNIZ_PROOF_CONSENSUS", "2")

    from leibniz.assembly import build_daemon  # noqa: E402
    from leibniz.calculemus import Calculemus, render_propositio  # noqa: E402
    from leibniz.daemon import CycleReport  # noqa: E402

    feed = json.loads(_FEED.read_text())
    records = feed.get("records", [])
    print(f"[calibrate] feed: {len(records)} records (run_date {feed.get('run_date')})")
    print(f"[calibrate] {cycles} cycles × {seeds_per_cycle} seeds; USD cap ${cap_usd:.2f}; "
          f"consensus {os.environ['LEIBNIZ_PROOF_CONSENSUS']}; provers HF[{_HF_PROVERS.count(',')+1}]")

    daemon = build_daemon(frontier_limit=seeds_per_cycle, analogy_limit=0)
    daemon.survey = FeedSurvey(records, seeds_per_cycle)  # seed from the feed
    daemon.domains = ()  # single domain; the feed drives the seeds

    rows = []
    t0 = time.time()
    for i in range(cycles):
        if daemon.cost_budget is not None and daemon.cost_budget.exhausted():
            print(f"[calibrate] USD cap reached (${daemon.cost_budget.spent_usd:.2f}); stopping.")
            break
        fresh_only = (i == 0)
        seeds = daemon._next_seeds(fresh_only, seeds_per_cycle, 4, "feed")
        rep = CycleReport()
        rep.seeds = len(seeds)
        print(f"\n[calibrate] cycle {i}: {len(seeds)} seeds (band target "
              f"{daemon.frontier.target:.2f}) — running LIVE…")
        daemon._run_seeds(seeds, rep)
        fr = daemon.frontier
        nb = daemon.notebook
        row = {
            "cycle": i, "seeds": rep.seeds, "conjectured": rep.conjectured,
            "reached_proof": rep.reached_proof, "promulgated": rep.promulgated,
            "by_reason": dict(rep.by_reason),
            "band_target": round(fr.target, 3), "success_rate": round(fr.success_rate(), 3),
            "notebook": {"proven": len(nb.proven), "too_hard": len(nb.too_hard), "avoid": len(nb.avoid)},
            "spent_usd": round(daemon.cost_budget.spent_usd, 4) if daemon.cost_budget else None,
        }
        rows.append(row)
        print(f"  → conjectured {rep.conjectured}, reached_proof {rep.reached_proof}, "
              f"promulgated {rep.promulgated}; dispositions {dict(rep.by_reason)}; "
              f"spent ${row['spent_usd']}")
        if fr is not None:
            fr.update()

    elapsed = time.time() - t0
    cb = daemon.cost_budget

    # ---- promulgated laws (kernel-checked) --------------------------------------
    cx = Calculemus()
    proven = [p for p in daemon.runtime.recall_recent(200)
              if p.demonstratio and p.demonstratio.kernel_verified]
    for p in proven:
        if p.promulgated:
            cx.promulgate(p)
        print("\n=== KERNEL-VERIFIED ===")
        print(render_propositio(p))

    # ---- calibration summary + recommendation ----------------------------------
    agg: dict[str, int] = {}
    for r in rows:
        for k, v in r["by_reason"].items():
            agg[k] = agg.get(k, 0) + v
    total_conj = sum(r["conjectured"] for r in rows)
    total_proof = sum(r["reached_proof"] for r in rows)
    total_promul = sum(r["promulgated"] for r in rows)

    print("\n" + "=" * 64)
    print("CALIBRATION SUMMARY")
    print("=" * 64)
    print(f"  cycles run:      {len(rows)} in {elapsed:.0f}s")
    print(f"  conjectured:     {total_conj}")
    print(f"  reached proof:   {total_proof}")
    print(f"  PROMULGATED:     {total_promul}")
    print(f"  kernel-verified: {len(proven)}")
    print(f"  dispositions:    {agg}")
    if daemon.frontier is not None:
        print(f"  frontier band:   start 0.45 → {daemon.frontier.target:.2f} "
              f"(success rate {daemon.frontier.success_rate():.2f}, aim {daemon.frontier.aim:.2f})")
    if cb is not None:
        print(f"  cost:            ${cb.spent_usd:.4f} ({cb.input_tokens}+{cb.output_tokens} tok)")

    dom = max(agg, key=agg.get) if agg else None
    print("\nRECOMMENDATION:")
    if total_promul:
        print(f"  • Discovery is live — {total_promul} law(s) promulgated to the Codex "
              f"(awaiting operator publish). Hold the band near {daemon.frontier.target:.2f}.")
    elif dom == "unproven":
        print("  • Dominant outcome UNPROVEN → conjectures sit ABOVE the prover's reach. "
              "Lower the frontier band (reduce target/floor + aim) and lean on weakening; "
              "consider a stronger/longer prover budget.")
    elif dom in ("known", "trivial"):
        print("  • Dominant outcome KNOWN/TRIVIAL → conjectures sit BELOW the frontier. "
              "Raise the band (increase aim/target) for harder, more novel claims.")
    elif dom == "malformed":
        print("  • Dominant outcome MALFORMED → autoformalization is the bottleneck, not "
              "the frontier. Strengthen the FORMALIZE model / import-repair before re-tuning the band.")
    elif dom in ("unfaithful", "gamed", "defer"):
        print("  • Dominant outcome faithfulness-related → the conjecturer states claims the "
              "formal statement doesn't capture; tighten the structured claim contract.")
    else:
        print("  • Mixed/low signal — widen the run (more cycles/seeds, higher cap) to get a "
              "clearer spectrum before adjusting constants.")

    out = _REPO / "calibration_report.json"
    out.write_text(json.dumps({"rows": rows, "aggregate": agg, "elapsed_s": round(elapsed, 1),
                               "promulgated": total_promul, "kernel_verified": len(proven),
                               "cost_usd": round(cb.spent_usd, 4) if cb else None}, indent=2) + "\n")
    print(f"\n[calibrate] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

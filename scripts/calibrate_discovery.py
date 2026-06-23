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
    # Configure the run BEFORE build_daemon (it reads env): USD cap + the prover. Default
    # to the HF ensemble, but DEFER to a pre-set alternative prover (harness A's
    # LEIBNIZ_PROVER_MODELS/BASE_URL, or LEIBNIZ_ARISTOTLE) so wrappers like
    # measure_goedel.py can swap the prover without this harness clobbering it.
    if not (os.environ.get("LEIBNIZ_PROVER_MODELS") or os.environ.get("LEIBNIZ_PROVER_BASE_URL")):
        os.environ.setdefault("LEIBNIZ_HF_PROVER_MODELS", _HF_PROVERS)
    os.environ["LEIBNIZ_DAILY_USD_CAP"] = str(cap_usd)
    os.environ.setdefault("LEIBNIZ_PROOF_CONSENSUS", "2")
    os.environ.setdefault("LEIBNIZ_PROVER_MAX_TOKENS", "4096")  # deeper proof-draft budget
    _prover_desc = (os.environ.get("LEIBNIZ_PROVER_MODELS")
                    or f"HF[{_HF_PROVERS.count(',') + 1}]")

    from leibniz.assembly import build_daemon  # noqa: E402
    from leibniz.calculemus import Calculemus, render_propositio  # noqa: E402
    from leibniz.daemon import CycleReport  # noqa: E402

    feed = json.loads(_FEED.read_text())
    records = feed.get("records", [])
    print(f"[calibrate] feed: {len(records)} records (run_date {feed.get('run_date')})")
    _repair_on = os.environ.get("LEIBNIZ_PROOF_REPAIR", "") not in ("", "0")
    print(f"[calibrate] {cycles} cycles × {seeds_per_cycle} seeds; USD cap ${cap_usd:.2f}; "
          f"consensus {os.environ['LEIBNIZ_PROOF_CONSENSUS']}; prover {_prover_desc}"
          f"{' + Aristotle' if os.environ.get('LEIBNIZ_ARISTOTLE', '') not in ('', '0') else ''}"
          f"{' + repair(0029)' if _repair_on else ''}")

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
            if daemon.frontier_path:
                fr.save(daemon.frontier_path)  # persist the learned band across runs
        if nb is not None and daemon.notebook_path:
            nb.save(daemon.notebook_path)  # ADR 0023: persist near-misses across runs

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
    if daemon.notebook is not None:
        nb = daemon.notebook
        print(f"  notebook:        proven {len(nb.proven)}, too_hard {len(nb.too_hard)} "
              f"(accumulating for weaken-and-retry), avoid {len(nb.avoid)}")
    dec = getattr(daemon.demonstrate, "decomposer", None)  # ADR 0027 instrumentation
    decomp_stats = dec.stats.as_dict() if dec is not None and hasattr(dec, "stats") else None
    if decomp_stats is not None:
        s = decomp_stats
        print(f"  decomposition:   attempted {s['attempted']}, planned {s['planned']}, "
              f"sub-lemmas {s['lemmas_proven']}/{s['lemmas_proposed']} proven, "
              f"composed {s['closed']}/{s['composed_attempts']} closed")
    rep_stage = getattr(daemon.demonstrate, "repairer", None)  # ADR 0029 instrumentation
    repair_stats = None
    if rep_stage is not None and hasattr(rep_stage, "stats"):
        # Aggregate the PANEL (ADR 0029 v2): the primary + each distinct-model member each run
        # their own loop, so sum their reach. promulgated is recorded on the primary only (it is
        # the stage's count, not per-member). rounds_to_close concatenates all members' wins.
        members = [rep_stage, *getattr(daemon.demonstrate, "panel", ())]
        repair_stats = {
            "panel_size": len(members),
            "attempted": sum(m.stats.attempted for m in members),
            "closed": sum(m.stats.closed for m in members),
            "repairs": sum(m.stats.repairs for m in members),
            "promulgated": rep_stage.stats.promulgated,
            "rounds_to_close": [r for m in members for r in m.stats.rounds_to_close],
        }
    if repair_stats is not None:
        s = repair_stats
        # `closed` is repair's RAW reach — goals the base ensemble + decomposition came up SHORT
        # on, that some repair reasoner kernel-closed; `promulgated` is the N+1-gated subset
        # (>=2 DISTINCT models closed the same goal). rounds_to_close shows whether wins came on
        # the initial draft (0) or needed kernel-error repair (>=1).
        print(f"  repair (0029):   panel {s['panel_size']}, attempted {s['attempted']}, "
              f"closed {s['closed']} (promulgated {s['promulgated']}), "
              f"repair-rounds {s['repairs']}; rounds_to_close {s['rounds_to_close']}")
    if cb is not None:
        print(f"  cost:            ${cb.spent_usd:.4f} ({cb.input_tokens}+{cb.output_tokens} tok)")

    dom = max(agg, key=agg.get) if agg else None
    print("\nRECOMMENDATION:")
    if total_promul:
        print(f"  • Discovery is live — {total_promul} law(s) promulgated to the Codex "
              f"(awaiting operator publish). Hold the band near {daemon.frontier.target:.2f}.")
    elif total_proof == 0 and total_conj > 0:
        # The decisive signal is reached_proof, NOT the disposition label: a
        # faithfulness DEFER carries no FinishReason and surfaces as 'unproven', so
        # reached_proof==0 means candidates die in the CHEAP GATES before any proving.
        print("  • NOTHING reached proof (reached_proof=0): candidates die in the cheap "
              "gates BEFORE proving — dominant outcome is faithfulness DEFER (the honest "
              "gate cannot certify these contracts), surfacing as 'unproven'. Band/prover "
              "tuning will NOT help; the blocker is upstream. Highest-leverage next step: "
              "steer the conjecturer to emit FULLY-ENCODABLE arithmetic contracts "
              "(claim_domain/claim_property/established_domain in the DSL: integer vars, "
              "+ - *, constant ^ and mod/div, comparisons) and/or widen the DSL to "
              "functions/symbolic exponents.")
    elif dom == "unproven":
        print("  • Conjectures REACH proof but the prover cannot close them (above its "
              "reach). Lower the frontier band (target/aim), lean on weakening, and raise "
              "the prover budget.")
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
                               "decomposition": decomp_stats, "repair": repair_stats,
                               "cost_usd": round(cb.spent_usd, 4) if cb else None}, indent=2) + "\n")
    print(f"\n[calibrate] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

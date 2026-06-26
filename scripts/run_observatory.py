"""Opt-in LIVE Walnut-decided Observatory run (ADR 0038). BILLABLE LLM + real Walnut.

Generates N automatic-sequence conjectures (Role.CONJECTURE), DECIDES each with Walnut over
unbounded n (the non-Q.E.D. tier — never kernel-Q.E.D.), and writes the
DECIDED/REFUTED/UNPROVEN records to a JSON ledger for the blind-novelty panel.

Needs creds in .env (the CONJECTURE model) AND a built Walnut, located via env:
    export LEIBNIZ_WALNUT_JAR=/abs/path/to/Walnut/build/libs/Walnut-all.jar
    # or, if the jar is not in <home>/build/libs/:
    export LEIBNIZ_WALNUT_HOME=/abs/path/to/Walnut

Run:
    python3 scripts/run_observatory.py [count] [out.json]

Without LEIBNIZ_WALNUT_JAR the runner DEFERs every claim (=> all UNPROVEN) — sound, but
nothing is decided; the script warns up front.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from leibniz.assembly import build_conjecturer  # noqa: E402
from leibniz.cost import CostBudget  # noqa: E402
from leibniz.env import load_env  # noqa: E402
from leibniz.observatory import WALNUT_DECISION_EDGE, WalnutObservatory  # noqa: E402
from leibniz.types import FinishReason  # noqa: E402
from leibniz.walnut_conjecture import WalnutConjecturer  # noqa: E402


def _record(prop) -> dict:
    """The ledger row for one decided/quarantined claim. Includes the decision-path `reason`
    (diagnostics) and, for a DECIDED record, the certificate (the provenance edge) so the
    blind panel sees the formal-first statement of record."""
    ex = prop.expressio
    edge = next((e for e in prop.edges if e.edge == WALNUT_DECISION_EDGE), None)
    return {
        "pid": prop.pid,
        "finish_reason": prop.finish_reason.value if prop.finish_reason else None,
        "reason": (edge.detail.get("reason") if edge else None),  # decided_sentence / no_result / ...
        "statement": prop.enuntiatio.statement,
        "walnut_predicate": ex.walnut_predicate if ex else None,
        "walnut_numeration": ex.walnut_numeration if ex else None,
        "promulgated": prop.promulgated,           # MUST be False — tier is non-Q.E.D.
        "automaton_certificate": (edge.detail.get("automaton") if edge else None),
    }


def run_observatory(conjecturer: WalnutConjecturer, count: int, out_path: Path) -> dict:
    """Generate + decide `count` claims; persist the ledger; return a summary. Pure given the
    injected conjecturer (so it is unit-testable without live LLM/Walnut)."""
    records, counts = [], Counter()
    sample_failure = None  # diagnostics: first unusable-proposal reason (provider error or raw draft)
    for _ in range(count):
        prop = conjecturer.generate_and_decide()
        if prop is None:
            counts["no_proposal"] += 1
            if sample_failure is None:
                sample_failure = conjecturer.last_error or ((conjecturer.last_draft or "")[:400]
                                                            or "(empty draft)")
            continue
        counts[prop.finish_reason.value if prop.finish_reason else "none"] += 1
        records.append(_record(prop))
    # SAFETY: a Walnut-tier ledger must never contain a promulgated/Q.E.D. record.
    assert all(not r["promulgated"] for r in records), "tier leak: a record is promulgated"
    reason_hist = Counter(r["reason"] for r in records if r["reason"])  # WHY each was decided/quarantined
    out_path.write_text(json.dumps({"count": count, "by_reason": dict(counts),
                                    "reason_histogram": dict(reason_hist),
                                    "records": records}, indent=2))
    return {"count": count, "by_reason": dict(counts), "reason_histogram": dict(reason_hist),
            "decided": counts.get(FinishReason.WALNUT_DECIDED.value, 0),
            "sample_failure": sample_failure, "ledger": str(out_path)}


def main() -> int:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("observatory_ledger.json")

    loaded = load_env(Path(__file__).resolve().parent.parent / ".env")
    print(f"[observatory] loaded {loaded} env vars from .env")
    if not os.environ.get("LEIBNIZ_WALNUT_JAR"):
        print("[observatory] WARNING: LEIBNIZ_WALNUT_JAR unset — every claim will DEFER "
              "(=> UNPROVEN). Set it to the built Walnut-all.jar to decide live.")

    conjecturer = WalnutConjecturer(
        provider=build_conjecturer(meter=CostBudget.from_env()),
        observatory=WalnutObservatory(),
    )
    print(f"[observatory] generating + deciding {count} automatic-sequence claims (LIVE)...")
    summary = run_observatory(conjecturer, count, out)

    print("\n=== Observatory run (non-Q.E.D. Walnut-decided tier) ===")
    print(f"  decided (WALNUT_DECIDED): {summary['decided']}")
    for reason, n in sorted(summary["by_reason"].items()):
        print(f"    {reason:<16} {n}")
    if summary.get("reason_histogram"):
        print("  why (decision-path reason):")
        for why, n in sorted(summary["reason_histogram"].items()):
            print(f"    {why:<22} {n}")
        if not summary["decided"]:
            print("  (re-run with LEIBNIZ_WALNUT_DEBUG=1 to see Walnut's stderr on 'no_result')")
    print(f"  ledger -> {summary['ledger']}")
    if summary.get("by_reason", {}).get("no_proposal") and summary.get("sample_failure"):
        # diagnostics: show WHY proposals were unusable (provider error or a raw-draft sample)
        print("\n  [diag] a sample unusable proposal (provider error or raw draft):")
        print("  " + str(summary["sample_failure"]).replace("\n", "\n  "))
    if summary["decided"]:
        print("  NEXT: blind-novelty panel (ADR 0034 §5) on the DECIDED records — trigger 1/2 "
              "for the kernel bridge (task #54). These are NOT Q.E.D. (decided by Walnut, "
              "not the Lean kernel).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

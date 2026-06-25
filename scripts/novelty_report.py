#!/usr/bin/env python3
"""Novelty report (ADR 0034 Stage 0) — a READ-ONLY view of structural diversity.

Prints the `novelty_metrics` profile for:
  • the known-results corpus (its own internal diversity — demonstrable today), and
  • optionally, the promulgated laws in a runtime DB, measured against the corpus.

This is instrumentation: it computes coverage + nearest-neighbour signature distances and
decides NOTHING (ADR 0034 §6, Prohibition 1). Read the module docstring of
`leibniz.novelty_metrics` for what these numbers can and cannot tell you — in short, a
distance distribution that does not move means we have NOT diversified (trustworthy), but one
that moves rightward is necessary-not-sufficient for genuine novelty (the metric shares a
coordinate system with the generator; §4 measurement circularity). The real success signal is
the operator's blind human read (§5.1).

Usage:
    python scripts/novelty_report.py                 # corpus profile only
    python scripts/novelty_report.py --db .leibniz/memory.db   # + promulgations in that DB
    python scripts/novelty_report.py --json          # machine-readable
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from leibniz import novelty_metrics as nm  # noqa: E402
from leibniz.corpus import CorpusBackend  # noqa: E402


def _corpus_properties() -> list[str]:
    return [e.claim_property for e in CorpusBackend.from_json().entries if e.claim_property]


def _promulgated_properties(db_path: str) -> tuple[list, int]:
    """Return (stored claim_property list, total promulgated rows). A promulgated row whose
    claim_property is NULL (pre-Stage-0) contributes to the total but carries no property — the
    gap between the two counts is the persistence-coverage finding (ADR 0034 §4).

    Read-only: a DB that predates the Stage-0 migration has no `claim_property` column. We do
    NOT alter it (the migration belongs to PersistentRuntime, not to a report) — we detect the
    missing column and report every promulgation as no-property-stored."""
    con = sqlite3.connect(db_path)
    try:
        have = {r[1] for r in con.execute("PRAGMA table_info(memory)")}
        total = con.execute(
            "SELECT COUNT(*) FROM memory WHERE kernel_verified=1 AND qed='Q.E.D.'"
        ).fetchone()[0]
        if "claim_property" not in have:
            return [], total
        rows = con.execute(
            "SELECT claim_property FROM memory WHERE kernel_verified=1 AND qed='Q.E.D.'"
        ).fetchall()
    finally:
        con.close()
    return [r[0] for r in rows if r[0]], total


def _fmt(profile: dict) -> str:
    s = profile["distance_summary"]
    dist = (f"min={s['min']:.2f} mean={s['mean']:.2f} max={s['max']:.2f}"
            if s else "n/a (no neighbours)")
    return (
        f"  examined        : {profile['n_total']}\n"
        f"  signature cover : {profile['n_covered']}/{profile['n_total']} "
        f"({profile['coverage']:.0%})  <- blind to the rest (where genuine novelty would live)\n"
        f"  distinct shapes : {profile['distinct_clusters']}\n"
        f"  nearest-nbr dist: {dist}\n"
        f"  isolated points : {profile['isolated']}"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ADR 0034 Stage 0 read-only novelty report")
    ap.add_argument("--db", help="runtime DB to read promulgations from (optional)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args(argv)

    corpus_props = _corpus_properties()
    out: dict = {"corpus": nm.profile(corpus_props)}

    if args.db:
        props, total = _promulgated_properties(args.db)
        out["promulgated"] = {
            "rows_total": total,
            "with_property": len(props),
            "profile": nm.profile(props, reference=corpus_props),
        }

    if args.json:
        print(json.dumps(out, indent=2, default=list))
        return 0

    print("=== ADR 0034 Stage 0 — novelty instrumentation (read-only; decides nothing) ===\n")
    print("KNOWN-RESULTS CORPUS (internal structural diversity):")
    print(_fmt(out["corpus"]))
    if "promulgated" in out:
        p = out["promulgated"]
        print(f"\nPROMULGATIONS in {args.db}:")
        print(f"  promulgated rows: {p['rows_total']}  |  with stored claim_property: "
              f"{p['with_property']}")
        if p["with_property"] == 0 and p["rows_total"] > 0:
            print("  (pre-Stage-0 rows store no claim_property — the persistence gap this stage\n"
                  "   fixes going forward; ADR 0034 §4. Re-run after a fresh cycle to measure.)")
        else:
            print(_fmt(p["profile"]))
    print("\nReminder: a flat distribution => NOT diversified (trustworthy); a rising one is\n"
          "necessary-not-sufficient for genuine novelty (§4). The blind human read is the gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

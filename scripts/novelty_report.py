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


def _promulgated_rows(db_path: str) -> tuple[list, int, dict]:
    """Return (stored claim_property list, total promulgated rows, origin->count). A promulgated
    row whose claim_property is NULL (pre-Stage-0) contributes to the total but carries no property
    — the gap is the persistence-coverage finding (ADR 0034 §4). The origin breakdown (ADR 0034
    §5) isolates MINED-origin promulgations for the kill condition.

    Read-only: a DB predating a migration lacks the column; we detect it and degrade, never ALTER."""
    con = sqlite3.connect(db_path)
    try:
        have = {r[1] for r in con.execute("PRAGMA table_info(memory)")}
        total = con.execute(
            "SELECT COUNT(*) FROM memory WHERE kernel_verified=1 AND qed='Q.E.D.'"
        ).fetchone()[0]
        if "claim_property" not in have:
            return [], total, {}
        has_origin = "seed_origin" in have
        cols = "claim_property" + (", seed_origin" if has_origin else "")
        rows = con.execute(
            f"SELECT {cols} FROM memory WHERE kernel_verified=1 AND qed='Q.E.D.'"
        ).fetchall()
    finally:
        con.close()
    props = [r[0] for r in rows if r[0]]
    origins: dict = {}
    if has_origin:
        for r in rows:
            origins[r[1] or "untagged"] = origins.get(r[1] or "untagged", 0) + 1
    return props, total, origins


def _mined_properties(db_path: str) -> list:
    """The claim_property of promulgations whose seed_origin is 'mined' (ADR 0034 §5 — the kill
    condition's numerator). Empty if the DB has no seed_origin column or no mined promulgations."""
    con = sqlite3.connect(db_path)
    try:
        if "seed_origin" not in {r[1] for r in con.execute("PRAGMA table_info(memory)")}:
            return []
        rows = con.execute(
            "SELECT claim_property FROM memory "
            "WHERE kernel_verified=1 AND qed='Q.E.D.' AND seed_origin='mined'"
        ).fetchall()
    finally:
        con.close()
    return [r[0] for r in rows if r[0]]


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
        props, total, origins = _promulgated_rows(args.db)
        mined = _mined_properties(args.db)
        out["promulgated"] = {
            "rows_total": total,
            "with_property": len(props),
            "by_origin": origins,                       # ADR 0034 §5: mined vs feed breakdown
            "profile": nm.profile(props, reference=corpus_props),
            "mined_profile": nm.profile(mined, reference=corpus_props) if mined else None,
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
        if p["by_origin"]:
            print(f"  by seed origin  : {p['by_origin']}")
        if p["with_property"] == 0 and p["rows_total"] > 0:
            print("  (pre-Stage-0 rows store no claim_property — the persistence gap this stage\n"
                  "   fixes going forward; ADR 0034 §4. Re-run after a fresh cycle to measure.)")
        else:
            print(_fmt(p["profile"]))
        if p.get("mined_profile"):
            print("\n  MINED-origin promulgations (ADR 0034 §5 kill-condition numerator):")
            print(_fmt(p["mined_profile"]))
    print("\nReminder: a flat distribution => NOT diversified (trustworthy); a rising one is\n"
          "necessary-not-sufficient for genuine novelty (§4). The blind human read is the gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

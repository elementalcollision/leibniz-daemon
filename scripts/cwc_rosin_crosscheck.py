"""Rosin-2026 cross-check for the CWC table-of-record oracle (FunSearch precondition).

The FunSearch decision-package (docs/funsearch-decision-package.md §6.1) requires that, before any
record "beat" is claimed, the oracle's novelty floor reflects Christopher D. Rosin's 2026 improvements
to A(n,d,w) (arXiv 2603.00174, "Automated Discovery of Improved Constant Weight Binary Codes": 24
improved lower bounds, 6<=d<=18, 18<=n<=35). Otherwise a search that merely re-discovers a Rosin code
would be falsely flagged "novel" against a stale table.

This module is the SINGLE SOURCE OF TRUTH for those 24 published values (two independent web extractions
of Table 1 — arXiv HTML and ar5iv — agreed exactly). It cross-checks them against the committed Brouwer
snapshot and provides `assert_post_rosin`, which the test suite uses to GUARD the property: every Rosin
cell must satisfy snapshot >= Rosin's new bound. A future snapshot refresh that regresses below Rosin
fails CI, loudly.

Finding (2026-06-27): the committed snapshot (Brouwer's table, fetched 2026-06-27) ALREADY dominates
Rosin on all 24 cells (19 equal, 5 strictly beyond — the table advanced further since Rosin). So the
precondition is SATISFIED with the current snapshot; no overlay is needed. Pure stdlib.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cwc_table_oracle as ora  # noqa: E402

# arXiv 2603.00174 Table 1: (n,d,w) -> (previous_best_known, rosin_new_lower_bound).
ROSIN_2026: dict[tuple[int, int, int], tuple[int, int]] = {
    (18, 6, 6): (132, 133),
    (22, 8, 9): (280, 292), (23, 8, 9): (400, 412), (23, 8, 10): (616, 648),
    (24, 8, 9): (640, 656), (24, 8, 11): (1288, 1378), (25, 8, 7): (254, 255),
    (25, 8, 9): (829, 837), (25, 8, 11): (1662, 1702), (25, 8, 12): (2576, 2610),
    (26, 8, 7): (257, 259), (26, 8, 8): (760, 763), (26, 8, 11): (1988, 2030),
    (27, 8, 10): (1600, 1704), (28, 8, 6): (130, 131), (28, 8, 10): (1867, 2028),
    (22, 10, 8): (24, 25), (25, 10, 8): (48, 50), (28, 10, 7): (37, 38),
    (30, 12, 9): (42, 43),
    (31, 16, 13): (16, 17), (31, 16, 14): (21, 24), (32, 16, 13): (24, 25),
    (35, 18, 16): (21, 22),
}

PROVENANCE = {
    "source_name": "Christopher D. Rosin, Automated Discovery of Improved Constant Weight Binary Codes",
    "arxiv_id": "2603.00174v1",
    "published": "2026-02-26",
    "table": "Table 1 (24 improved lower bounds, 6<=d<=18, 18<=n<=35)",
    "extraction": "two independent web extractions (arXiv HTML + ar5iv) agreed exactly on all 24 cells",
    "fetched_at": "2026-06-27",
}


def rosin_floor(n: int, d: int, w: int) -> int | None:
    """Rosin's published lower bound for a cell, or None if not one of the 24 improved cells."""
    v = ROSIN_2026.get((n, d, w))
    return v[1] if v else None


def crosscheck(snap=None) -> dict:
    """Compare each Rosin cell against the committed snapshot. Returns a structured report."""
    snap = snap if snap is not None else ora.load_snapshot()[0]
    rows = []
    for (n, d, w), (prev, new) in sorted(ROSIN_2026.items()):
        s = snap.get((n, d, w))
        if s is None:
            status = "untabulated"
        elif s == new:
            status = "snapshot==rosin"
        elif s > new:
            status = "snapshot>rosin (table advanced further)"
        else:
            status = "STALE (snapshot<rosin)"
        rows.append({"cell": [n, d, w], "snapshot": s, "rosin_prev": prev, "rosin_new": new,
                     "status": status})
    dominated = all(r["snapshot"] is not None and r["snapshot"] >= r["rosin_new"] for r in rows)
    return {
        "provenance": PROVENANCE,
        "snapshot_dominates_rosin": dominated,
        "cells_total": len(rows),
        "cells_equal": sum(1 for r in rows if r["status"] == "snapshot==rosin"),
        "cells_beyond": sum(1 for r in rows if r["status"].startswith("snapshot>rosin")),
        "cells_stale": sum(1 for r in rows if r["status"].startswith("STALE")),
        "cells_untabulated": sum(1 for r in rows if r["status"] == "untabulated"),
        "rows": rows,
    }


def assert_post_rosin(snap=None) -> tuple[bool, list[tuple[int, int, int]]]:
    """The GUARD: every Rosin cell must satisfy snapshot >= rosin_new. Returns (ok, violations).
    A violation means the oracle's novelty floor is below a published Rosin record — novelty claims on
    that cell would be unsound until the snapshot is refreshed."""
    snap = snap if snap is not None else ora.load_snapshot()[0]
    bad = [(n, d, w) for (n, d, w), (_p, new) in ROSIN_2026.items()
           if snap.get((n, d, w)) is None or snap[(n, d, w)] < new]
    return (not bad, bad)


def rosin_bound_seed():
    """The first BoundSeed (ADR 0041 Phase 3): Rosin 2026's 24 improved A(n,d,w) bounds packaged as an
    UNTRUSTED FLOOR seed for leibniz/seeds.py. Validating it against the committed snapshot leaves the
    floor UNCHANGED — the snapshot already dominates all 24 cells (verified) — i.e. no behavior change,
    exactly the Phase-3 gate. extraction_agreement=2 (two independent web extractions agreed)."""
    from leibniz.seeds import Seed, SeedKind, SeedProvenance
    cells = {(n, d, w): new for (n, d, w), (_prev, new) in ROSIN_2026.items()}
    prov = SeedProvenance(
        source_id=PROVENANCE["arxiv_id"], url="https://arxiv.org/abs/2603.00174",
        fetched_at=PROVENANCE["fetched_at"], extraction_method=PROVENANCE["extraction"])
    return Seed(kind=SeedKind.FLOOR, payload={"cells": cells}, provenance=prov,
                extraction_agreement=2,
                proof_of_use="arXiv 2603.00174 Table 1 (two independent extractions agreed on all 24)")


def main() -> int:
    report = crosscheck()
    out = Path(__file__).resolve().parent.parent / "docs" / "results" / "cwc_oracle_rosin_crosscheck.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[cwc-rosin-crosscheck] {report['cells_total']} Rosin cells; "
          f"equal={report['cells_equal']} beyond={report['cells_beyond']} "
          f"stale={report['cells_stale']} untab={report['cells_untabulated']}")
    print(f"  snapshot dominates Rosin on all 24: {report['snapshot_dominates_rosin']}")
    print(f"  -> {out}")
    return 0 if report["snapshot_dominates_rosin"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

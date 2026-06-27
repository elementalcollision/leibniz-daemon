"""Probe β piece 2 — the automated table-of-record ORACLE for constant-weight codes.

The α lesson: a search track's novelty must be judged by an AUTOMATED lookup against a real
table-of-record, never by a hand/LLM detector (Probe α's name-detector false-negatived 8/8). This
parses Andries Brouwer's A(n,d,w) lower-bound tables (BSSS 1990 + Brouwer–Etzion 2011) into a
committed snapshot and answers `best_known(n,d,w)` / `is_improvement(...)`. NOVELTY for Probe β =
a Lean-checked witness whose size strictly exceeds `best_known`.

Soundness posture (the α safeguard): the snapshot is VALIDATED against ground-truth anchors
(Fano/Steiner optima) and monotonicity-in-n, and `load_snapshot` REFUSES a snapshot that fails —
a wrong oracle would poison every novelty claim. Out-of-table cells return None (conservative:
"unknown to the table", never a fabricated bound). Pure stdlib.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent.parent / "docs" / "results" / "brouwer_cwc_lower_bounds.json"

# Ground-truth anchors that are independently certain (Fano/Steiner optima, textbook Brouwer cells).
# A wrong parse will miss these => load is refused.
GROUND_TRUTH: dict[tuple[int, int, int], int] = {
    (6, 4, 3): 4, (7, 4, 3): 7, (13, 4, 3): 26, (9, 4, 3): 12, (8, 4, 4): 14,
}


def _num(cell: str) -> int | None:
    """Leading integer of a Brouwer cell, ignoring markers (`.`=exact, `[…]`=ref, superscripts)."""
    m = re.search(r"\d+", cell.replace(",", ""))
    return int(m.group()) if m else None


def _row_cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def parse_brouwer_markdown(md: str) -> dict[tuple[int, int, int], int]:
    """Parse Brouwer's `# Bounds on A(n,d,w)` lower-bound matrices (rows=n, cols=w) from the page
    markdown into {(n,d,w): lower_bound}. Deterministic; the d=4 matrix precedes its heading so it
    defaults to d=4 until a `Bounds on A(n,<d>,w)` heading sets the current distance."""
    lines = md.split("\n")
    snap: dict[tuple[int, int, int], int] = {}
    cur_d: int | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        h = re.search(r"Bounds on A\(n,\s*(\d+),\s*w\)", line)
        if h:
            cur_d = int(h.group(1))
        if line.lstrip().startswith("|") and re.match(r"\|\s*n\\?\\?w\s*\|", line):
            d = cur_d or 4
            ws = [_num(c) for c in _row_cells(line)[1:]]
            j = i + 1
            if j < len(lines) and set(lines[j].replace("|", "").strip()) <= set("-: "):
                j += 1  # skip a |---|---| separator
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                cs = _row_cells(lines[j])
                n = _num(cs[0])
                if n is not None:
                    for w, cell in zip(ws, cs[1:]):
                        v = _num(cell)
                        if w is not None and v is not None:
                            snap[(n, d, w)] = v
                j += 1
            i = j
            continue
        i += 1
    return snap


def validate(snap: dict[tuple[int, int, int], int]) -> tuple[bool, list[str]]:
    """Ground-truth + structural validation (the α safeguard). Returns (ok, problems)."""
    problems = []
    for k, expected in GROUND_TRUTH.items():
        if snap.get(k) != expected:
            problems.append(f"anchor A{k} = {snap.get(k)} != {expected}")
    for (n, d, w), v in snap.items():
        pv = snap.get((n - 1, d, w))
        if pv is not None and v < pv:
            problems.append(f"monotonicity A({n},{d},{w})={v} < A({n-1},{d},{w})={pv}")
    return (not problems, problems)


def load_snapshot(path: Path = SNAPSHOT) -> tuple[dict[tuple[int, int, int], int], dict]:
    """Load + VALIDATE the committed snapshot. Raises if it fails ground truth (refuse a wrong
    oracle). Returns (cells, provenance)."""
    data = json.loads(path.read_text())
    snap = {tuple(int(x) for x in k.split(",")): v for k, v in data["cells"].items()}
    ok, problems = validate(snap)
    if not ok:
        raise ValueError(f"CWC oracle snapshot failed validation: {problems[:5]}")
    return snap, data["provenance"]


def best_known(n: int, d: int, w: int, snap=None) -> int | None:
    """Best-known A(n,d,w) lower bound from the table-of-record, or None if not tabulated
    (conservative: a cell outside Brouwer's range has no oracle bound)."""
    snap = snap if snap is not None else load_snapshot()[0]
    return snap.get((n, d, w))


def is_improvement(n: int, d: int, w: int, found: int, snap=None) -> bool:
    """True iff `found` strictly beats the table-of-record's best-known A(n,d,w). False when the
    cell is untabulated (no record to beat) — never claim novelty against an unknown."""
    bk = best_known(n, d, w, snap)
    return bk is not None and found > bk


def build_snapshot(md: str, provenance: dict, path: Path = SNAPSHOT) -> dict:
    """Refresh path: parse the fetched Brouwer markdown, validate, and write the snapshot. Refuses
    to write a snapshot that fails ground truth."""
    snap = parse_brouwer_markdown(md)
    ok, problems = validate(snap)
    if not ok:
        raise ValueError(f"refusing to write an invalid snapshot: {problems[:5]}")
    out = {"provenance": {**provenance, "cells": len(snap), "validated": True},
           "cells": {f"{n},{d},{w}": v for (n, d, w), v in sorted(snap.items())}}
    path.write_text(json.dumps(out, indent=2))
    return out["provenance"]


def main() -> int:
    snap, prov = load_snapshot()
    print(f"[cwc-oracle] snapshot OK: {len(snap)} cells, validated against {len(GROUND_TRUTH)} "
          f"anchors + monotonicity")
    print(f"  source: {prov.get('source_url')} (fetched {prov.get('fetched_at')})")
    print(f"  A(7,4,3) best-known = {best_known(7,4,3,snap)}  (Fano)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

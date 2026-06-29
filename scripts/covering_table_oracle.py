"""Automated covering-design table-of-record oracle (ADR 0043, Track B1).

Mirrors the La Jolla Covering Repository (ljcr.dmgordon.org) best-known C(v,k,t) upper bounds, exactly as
cwc_table_oracle.py mirrors Brouwer's CWC table. Novelty is settled by an exact integer comparison
against this single table — never by an LLM judge (invariant 4).

KEY ASYMMETRY vs CWC: a covering of size B is an UPPER bound C(v,k,t) <= B, so SMALLER is better. An
"improvement" / record beat is therefore a witness with STRICTLY FEWER blocks than the table's
best-known. (CWC is the mirror: a code of size M is a lower bound, and larger is better.)
"""
from __future__ import annotations

import json
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent / "data" / "covering_snapshot.json"


def load_snapshot(path: Path = SNAPSHOT) -> tuple[dict[tuple[int, int, int], int], dict]:
    """Load the committed LJCR snapshot. Returns (bounds, meta) where bounds maps (v,k,t) -> best-known."""
    raw = json.loads(Path(path).read_text())
    bounds = {tuple(int(x) for x in key.split(",")): int(val) for key, val in raw["bounds"].items()}
    meta = {k: val for k, val in raw.items() if k != "bounds"}
    return bounds, meta


def best_known(v: int, k: int, t: int, snap=None) -> int | None:
    """Best-known C(v,k,t) (fewest blocks) from the table, or None if the cell is untabulated."""
    if snap is None:
        snap = load_snapshot()[0]
    return snap.get((v, k, t))


def is_improvement(v: int, k: int, t: int, found: int, snap=None) -> bool:
    """True iff a covering of size `found` STRICTLY beats the table record (fewer blocks). Untabulated
    cells are NOT improvements (novelty is not claimable without a record to beat)."""
    bk = best_known(v, k, t, snap)
    return bk is not None and found < bk

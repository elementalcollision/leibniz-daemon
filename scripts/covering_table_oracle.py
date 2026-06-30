"""Automated covering-design table-of-record oracle (ADR 0043, Track B1; hardened per ADR 0045 review).

Mirrors the La Jolla Covering Repository (ljcr.dmgordon.org) best-known C(v,k,t) upper bounds, exactly as
cwc_table_oracle.py mirrors Brouwer's CWC table. Novelty is settled by an exact integer comparison
against this single table — never by an LLM judge (invariant 4).

KEY ASYMMETRY vs CWC: a covering of size B is an UPPER bound C(v,k,t) <= B, so SMALLER is better. An
"improvement" / record beat is therefore a witness with STRICTLY FEWER blocks than the table's
best-known. (CWC is the mirror: a code of size M is a lower bound, and larger is better.)

SNAPSHOT VALIDATION (ADR 0045 adversarial-review must-fix #4): like the CWC oracle, the snapshot is
validated at load and load REFUSES a snapshot that fails — (a) GROUND_TRUTH anchors (independently-known
optimal covering numbers) must match exactly, and (b) every entry must be >= its Schonheim lower bound
(a best-known BELOW the provable lower bound is a corrupt/mis-parsed cell). This is a sanity backstop, not
a staleness guarantee; a fresh, provenance-stamped snapshot is still the real defense against staleness.
"""
from __future__ import annotations

import json
from pathlib import Path


def _ceildiv(a: int, b: int) -> int:
    """Exact integer ceil(a/b) for positive ints (no float — float rounding made L(98,5,2) read 491)."""
    return -(-a // b)

SNAPSHOT = Path(__file__).resolve().parent / "data" / "covering_snapshot.json"

# Independently-known OPTIMAL covering numbers (Schonheim-tight: Steiner systems / known optima). A
# snapshot whose entry for any anchor disagrees is rejected (catches parse drift / a wrong table).
GROUND_TRUTH: dict[tuple[int, int, int], int] = {
    (6, 3, 2): 6,    # Schonheim-tight
    (7, 3, 2): 7,    # Fano / STS(7) = binom(7,2)/binom(3,2)
    (9, 3, 2): 12,   # AG(2,3) / STS(9)
    (13, 3, 2): 26,  # STS(13)
    (8, 4, 3): 14,   # Schonheim-tight
}


def schonheim(v: int, k: int, t: int) -> int:
    """The Schonheim lower bound L(v,k,t) <= C(v,k,t): L(v,k,t)=ceil(v/k * L(v-1,k-1,t-1)), L(.,.,1)=ceil(v/k).
    Exact integer arithmetic throughout (ceil(v*inner/k)) — a float intermediate misrounds e.g. L(98,5,2)."""
    if t <= 1:
        return _ceildiv(v, k)
    return _ceildiv(v * schonheim(v - 1, k - 1, t - 1), k)


def validate(snap: dict[tuple[int, int, int], int]) -> tuple[bool, list[str]]:
    """Ground-truth + structural validation (the covering analog of the CWC oracle's safeguard).
    Returns (ok, problems)."""
    problems = []
    for cell, expected in GROUND_TRUTH.items():
        if snap.get(cell) != expected:
            problems.append(f"anchor C{cell} = {snap.get(cell)} != {expected}")
    for (v, k, t), val in snap.items():
        if not (1 <= t <= k <= v):
            problems.append(f"ill-formed cell C({v},{k},{t})")
            continue
        lb = schonheim(v, k, t)
        if val < lb:                                  # a best-known below the provable lower bound is corrupt
            problems.append(f"below-Schonheim C({v},{k},{t})={val} < L={lb}")
    return (not problems, problems)


def load_snapshot(path: Path = SNAPSHOT) -> tuple[dict[tuple[int, int, int], int], dict]:
    """Load + VALIDATE the committed LJCR snapshot. RAISES if it fails ground truth / the Schonheim floor
    (refuse a wrong oracle — ADR 0045 must-fix #4). Returns (bounds, meta)."""
    raw = json.loads(Path(path).read_text())
    bounds = {tuple(int(x) for x in key.split(",")): int(val) for key, val in raw["bounds"].items()}
    ok, problems = validate(bounds)
    if not ok:
        raise ValueError(f"covering oracle snapshot failed validation: {problems[:5]}")
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

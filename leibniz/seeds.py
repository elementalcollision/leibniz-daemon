"""Research-seeding: untrusted seeds from ingested research (ADR 0041 Phase 3).

One-directional and authoring-time. A `Seed` carries something an ingested paper *suggested* — a
record floor, a conjecture target, a construction — and is **UNTRUSTED**: a validated seed may only
ever feed a PROPOSER (a conjecture to attempt, a construction to run in the sandbox, a floor that can
RAISE — never lower — the bar). It NEVER decides anything; the kernel / automated oracle / the tool
registry re-check everything downstream (ADR 0041 E4).

Soundness posture (the guards `validate_seed` enforces, ADR 0041 §3.2 + the round-3 ATTACK-1
floor-raising guard):
  - **proof-of-use** required (a reference tying the value to the exact source span — blocks fabricated
    grounding);
  - FLOOR seeds need **>=2 agreeing independent extractions** (transcription-error guard);
  - FLOOR values are cross-checked **bidirectionally** against the validated table-of-record snapshot: a
    value <= snapshot is fine but *dominated* (it never lowers the floor — `effective_floor` uses
    `max()`); a value **> snapshot is QUARANTINED unless mechanically re-derived** (a fabricated raise
    could mask a genuine beat); an untabulated cell yields no floor (never a fabricated bound);
  - a claimed raise whose mechanical re-derivation FAILED is a **CONFLICT** (retained, surfaced).

Dependency-clean by design: the snapshot is INJECTED (`snap` dict), so this module imports NO network
client and NO scraper/oracle code — the runtime decision path depends only on committed data. (A test
pins the no-network property; the crawl/scrape that *produces* seeds is authoring-time, off this path.)
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Optional


class SeedKind(Enum):
    FLOOR = "floor"              # a numeric table-of-record value (e.g. A(n,d,w) >= v)
    TARGET = "target"           # a conjecture / open problem to attempt (a proposer goal)
    CONSTRUCTION = "construction"  # an explicit construction / program (an untrusted SandboxedTool input)
    HINT = "hint"               # generic untyped lead


class SeedStatus(Enum):
    UNTRUSTED = "untrusted"     # freshly extracted; not yet validated
    VALIDATED = "validated"     # passed the guards; may feed a PROPOSER (never a decider)
    QUARANTINED = "quarantined"  # failed a guard; retained, never deleted (inv 6), off the floor
    CONFLICT = "conflict"       # an ingested claim that a mechanical re-check contradicted (retained)


@dataclass(frozen=True)
class SeedProvenance:
    source_id: str              # e.g. an arXiv id
    url: str = ""
    version: str = ""
    fetched_at: str = ""
    extraction_method: str = ""
    license_note: str = ""


@dataclass(frozen=True)
class Seed:
    kind: SeedKind
    payload: dict               # FLOOR: {"cells": {(n,d,w): value}}; TARGET/CONSTRUCTION: free-form
    provenance: SeedProvenance
    extraction_agreement: int = 1   # # of independent extractions that agreed (FLOOR needs >= 2)
    proof_of_use: str = ""          # reference tying the value to the source span (anti-fabrication)
    rederived: bool = False         # was an above-snapshot raise mechanically re-derived?
    rederivation_failed: bool = False  # did a mechanical re-derivation actively contradict a raise?
    status: SeedStatus = SeedStatus.UNTRUSTED
    detail: dict = field(default_factory=dict)


def _q(seed: Seed, reason: str, **extra) -> Seed:
    return replace(seed, status=SeedStatus.QUARANTINED, detail={"reason": reason, **extra})


def validate_seed(seed: Seed, snap: dict) -> Seed:
    """Return a NEW Seed with `status` set per the ADR 0041 §3.2 guards. `snap` is the validated
    table-of-record dict {(n,d,w): best_known} (the caller loads it from the committed snapshot, which
    itself refuses to load unless it passes ground-truth anchors). Never mutates the input."""
    if not seed.proof_of_use:
        return _q(seed, "missing proof-of-use trace")

    if seed.kind is SeedKind.FLOOR:
        if seed.extraction_agreement < 2:
            return _q(seed, "FLOOR seed needs >= 2 agreeing independent extractions")
        cells = seed.payload.get("cells", {})
        untabulated, unrederived_raises = [], []
        for cell, value in cells.items():
            key = tuple(cell)
            s = snap.get(key)
            if s is None:
                untabulated.append(list(key))                     # no table-of-record -> no floor
            elif value > s and not seed.rederived:
                unrederived_raises.append([list(key), value, s])  # claimed improvement, unverified
            # value <= s (dominated) or (value > s and rederived): admissible
        if seed.rederivation_failed and any(
                snap.get(tuple(c)) is not None and v > snap[tuple(c)] for c, v in cells.items()):
            return replace(seed, status=SeedStatus.CONFLICT,
                           detail={"reason": "claimed raise failed mechanical re-derivation"})
        if unrederived_raises:
            return _q(seed, "un-re-derived raise above the validated snapshot (floor-raising guard)",
                      cells=unrederived_raises)
        return replace(seed, status=SeedStatus.VALIDATED,
                       detail={"untabulated_excluded": untabulated})

    # TARGET / CONSTRUCTION / HINT: untrusted PROPOSERS — provenance + proof-of-use suffice; everything
    # they suggest is re-checked downstream (the faithfulness/novelty/proof chain or the tool registry).
    return replace(seed, status=SeedStatus.VALIDATED,
                   detail={"note": "untrusted proposer; never decides"})


def effective_floor(n: int, d: int, w: int, snap: dict, seeds) -> Optional[int]:
    """The one-directional floor for a cell: max(committed snapshot, all VALIDATED FLOOR-seed values).
    A seed can only RAISE the bar of a cell that is ALREADY in the table-of-record; a dominated/lowering
    value is ignored by `max()`. An untabulated cell returns None regardless of any seed — there is no
    record to validate against, so a seed value there would be a fabricated bound (ADR 0041 E4)."""
    s = snap.get((n, d, w))
    if s is None:
        return None
    vals = [s]
    for seed in seeds:
        if seed.status is SeedStatus.VALIDATED and seed.kind is SeedKind.FLOOR:
            v = seed.payload.get("cells", {}).get((n, d, w))
            if v is not None:
                vals.append(v)
    return max(vals)


def seed_from_feed_record(record: dict) -> Seed:
    """Map a scraper `leibniz.json` record (ADR 0041 Stage-0 source) into an UNTRUSTED seed. A
    conjecture/open-problem record (the highest-value seed) becomes a TARGET; anything else a HINT.
    Pure (no network): the scraper already did the crawl. proof_of_use is the record's own citation."""
    wi = set(record.get("work_items", []))
    kind = SeedKind.TARGET if (record.get("seed_priority") == 0 or {"conjecture", "problem"} & wi) \
        else SeedKind.HINT
    cite = record.get("citation") or {}
    prov = SeedProvenance(
        source_id=record.get("arxiv_id") or record.get("id", ""),
        url=record.get("abs_url", ""),
        fetched_at=record.get("published", ""),
        extraction_method="arxiv_feed scraper",
    )
    return Seed(
        kind=kind,
        payload={"title": record.get("title", ""), "abstract": record.get("abstract", ""),
                 "work_items": sorted(wi), "primary_category": record.get("primary_category", "")},
        provenance=prov,
        proof_of_use=cite.get("plain") or record.get("abs_url", ""),
    )

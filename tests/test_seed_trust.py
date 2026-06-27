"""SEALED trust guards for the ADR 0041 research-seeding layer (Phase 3).

Protected from agent edits by the PreToolUse hook (like test_invariants.py / test_tool_trust.py): the
soundness of research ingestion cannot be quietly weakened. Pins: proof-of-use required; FLOOR seeds
need >=2 agreeing extractions; the bidirectional snapshot cross-check (dominated value ok; un-re-derived
raise above snapshot QUARANTINED — the floor-raising guard; failed re-derivation -> CONFLICT); the
floor is one-directional (max, never lowered); the seeds module imports no network client; and the
first BoundSeed (Rosin 2026) validates with NO behavior change (the snapshot already dominates).
"""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

from leibniz.seeds import (
    Seed,
    SeedKind,
    SeedProvenance,
    SeedStatus,
    effective_floor,
    seed_from_feed_record,
    validate_seed,
)

_ROOT = Path(__file__).resolve().parent.parent
_PROV = SeedProvenance(source_id="arXiv:test", url="u", fetched_at="2026-06-27")
_SNAP = {(7, 4, 3): 7, (8, 4, 4): 14}      # a tiny validated-style snapshot


def _floor(cells, **kw):
    return Seed(kind=SeedKind.FLOOR, payload={"cells": cells}, provenance=_PROV,
                proof_of_use="paper Table 1, p.3", extraction_agreement=2, **kw)


def test_missing_proof_of_use_quarantines():
    s = Seed(kind=SeedKind.FLOOR, payload={"cells": {(7, 4, 3): 5}}, provenance=_PROV,
             extraction_agreement=2)  # no proof_of_use
    assert validate_seed(s, _SNAP).status is SeedStatus.QUARANTINED


def test_floor_needs_two_agreeing_extractions():
    s = replace(_floor({(7, 4, 3): 5}), extraction_agreement=1)
    assert validate_seed(s, _SNAP).status is SeedStatus.QUARANTINED


def test_floor_dominated_value_is_validated():
    # value <= snapshot: a true-but-weaker bound; admitted but it never lowers the floor
    assert validate_seed(_floor({(7, 4, 3): 5}), _SNAP).status is SeedStatus.VALIDATED


def test_floor_unrederived_raise_is_quarantined():
    # value > snapshot without re-derivation: the floor-raising abuse guard (ATTACK 1)
    out = validate_seed(_floor({(7, 4, 3): 8}), _SNAP)
    assert out.status is SeedStatus.QUARANTINED and "floor-raising" in out.detail["reason"]


def test_floor_rederived_raise_is_validated():
    assert validate_seed(_floor({(7, 4, 3): 8}, rederived=True), _SNAP).status is SeedStatus.VALIDATED


def test_floor_failed_rederivation_is_conflict():
    out = validate_seed(_floor({(7, 4, 3): 8}, rederived=True, rederivation_failed=True), _SNAP)
    assert out.status is SeedStatus.CONFLICT


def test_untabulated_cell_is_excluded_not_fabricated():
    out = validate_seed(_floor({(99, 9, 9): 3}), _SNAP)
    assert out.status is SeedStatus.VALIDATED and [99, 9, 9] in out.detail["untabulated_excluded"]
    assert effective_floor(99, 9, 9, _SNAP, [out]) is None      # never a fabricated bound


def test_target_seed_is_validated_as_a_proposer():
    s = Seed(kind=SeedKind.TARGET, payload={"conjecture": "X"}, provenance=_PROV,
             proof_of_use="abstract")
    assert validate_seed(s, _SNAP).status is SeedStatus.VALIDATED


def test_effective_floor_is_one_directional():
    snap = {(7, 4, 3): 7}
    lowering = validate_seed(_floor({(7, 4, 3): 5}), snap)        # dominated
    assert effective_floor(7, 4, 3, snap, [lowering]) == 7        # not lowered below the snapshot
    raised = validate_seed(_floor({(7, 4, 3): 9}, rederived=True), snap)
    assert effective_floor(7, 4, 3, snap, [raised]) == 9          # a re-derived raise lifts it
    quar = validate_seed(_floor({(7, 4, 3): 9}), snap)            # un-re-derived -> QUARANTINED
    assert effective_floor(7, 4, 3, snap, [quar]) == 7            # quarantined seed ignored


def test_seeds_module_imports_no_network_client():
    src = (_ROOT / "leibniz" / "seeds.py").read_text()
    for bad in ("import socket", "import urllib", "import http", "import requests",
                "httpx", "urlopen", "urllib.request"):
        assert bad not in src, f"seeds.py must stay off the network; found {bad!r}"


def test_feed_record_maps_to_a_target_seed():
    rec = {"arxiv_id": "2606.1", "abs_url": "u", "title": "An open conjecture",
           "abstract": "we state a conjecture", "work_items": ["conjecture", "proof"],
           "seed_priority": 0, "citation": {"plain": "Author (2026). ..."}}
    s = seed_from_feed_record(rec)
    assert s.kind is SeedKind.TARGET and s.proof_of_use
    assert validate_seed(s, _SNAP).status is SeedStatus.VALIDATED


# --- the first BoundSeed: Rosin 2026 validates with NO behavior change (snapshot dominates) ---------
def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def test_rosin_bound_seed_validates_and_does_not_change_the_floor():
    ora = _load("cwc_table_oracle", "scripts/cwc_table_oracle.py")
    rc = _load("cwc_rosin_crosscheck", "scripts/cwc_rosin_crosscheck.py")
    snap = ora.load_snapshot()[0]
    seed = rc.rosin_bound_seed()
    out = validate_seed(seed, snap)
    assert out.status is SeedStatus.VALIDATED                     # all 24 cells are <= snapshot
    # no behavior change: the effective floor equals the committed snapshot on every Rosin cell
    for (n, d, w) in rc.ROSIN_2026:
        assert effective_floor(n, d, w, snap, [out]) == snap[(n, d, w)]

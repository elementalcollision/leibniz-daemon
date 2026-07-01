"""Guard the research-ingestion triage adapter (Track 3 baseline). Free-CPU, fixture-based: proves the
routing works (explicit witness -> amplify-ready candidate; domain mention without witness -> worklist;
free-text abstract -> never fabricated into a witness), even though the live feed's automated witness yield
is 0 (measured RED). No feed file, no docker, no trust touch."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod, rel):
    import sys
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(mod, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ing = _load("ingest_candidates", "scripts/ingest_candidates.py")

FANO = [[0, 1, 2], [0, 3, 4], [0, 5, 6], [1, 3, 5], [1, 4, 6], [2, 3, 6], [2, 4, 5]]

FIXTURE = [
    # a structured explicit covering witness (the clean automatable case) -> amplify-ready candidate
    {"id": "arxiv:0001", "title": "An explicit STS(7)", "abstract": "We give C(7,3,2)=7.",
     "citation": {"plain": "Author (2026)"}, "witness": {"domain": "covering", "v": 7, "k": 3, "t": 2,
                                                          "blocks": FANO}},
    # a structured explicit CWC witness -> candidate
    {"id": "arxiv:0002", "title": "A constant-weight code", "abstract": "A(7,4,3) >= 7.",
     "citation": {"plain": "B (2026)"}, "witness": {"domain": "cwc", "n": 7, "d": 4, "w": 3, "code": FANO}},
    # a covering MENTION but no witness -> worklist (needs reconstruction)
    {"id": "arxiv:0003", "title": "A cyclic covering design construction",
     "abstract": "We prove a new covering number bound C(v,k,t) via a cyclic base block over Z_n."},
    # a plain conjecture, no supported domain, no witness -> neither
    {"id": "arxiv:0004", "title": "On the complexity of SAT variants",
     "abstract": "We show a lower bound for a proof system."},
    # a free-text 'construction' with numbers but NO structured witness -> must NOT be fabricated
    {"id": "arxiv:0005", "title": "Covering design C(9,3,2)",
     "abstract": "An explicit covering with blocks [0,1,2] and others exists giving 12 blocks."},
]


def test_domain_classifier():
    assert ing.classify_domain("bound on A(7,4,3)") == "cwc"
    assert ing.classify_domain("a covering design over Z_n") == "covering"
    assert ing.classify_domain("a lower bound for SAT") == "none"


def test_triage_routes_correctly():
    res = ing.triage(FIXTURE)
    assert res["n_records"] == 5
    # two structured witnesses -> two amplify-ready candidates
    assert len(res["candidates"]) == 2
    doms = sorted(c["domain"] for c in res["candidates"])
    assert doms == ["covering", "cwc"]
    cov = next(c for c in res["candidates"] if c["domain"] == "covering")
    assert cov["v"] == 7 and cov["k"] == 3 and cov["t"] == 2 and cov["blocks"] == FANO
    assert cov["source"] == "arxiv:0001" and cov["proof_of_use"] == "Author (2026)"
    # arxiv:0003 (covering mention, no witness) and arxiv:0005 (free-text, no structured witness) -> worklist
    wl_ids = {w["id"] for w in res["worklist"]}
    assert "arxiv:0003" in wl_ids and "arxiv:0005" in wl_ids
    # arxiv:0004 (no domain) -> neither
    assert "arxiv:0004" not in wl_ids


def test_free_text_witness_is_never_fabricated():
    # arxiv:0005 mentions "blocks [0,1,2]" and "12 blocks" in prose but carries no structured witness ->
    # the adapter must return None (never synthesize a witness from an abstract).
    rec = FIXTURE[4]
    assert ing.parse_explicit_witness(rec, "covering") is None


def test_candidates_are_amplify_shaped():
    # candidates must be directly consumable by amplify.amplify_one (domain + params + witness list)
    import amplify
    res = ing.triage(FIXTURE)
    for c in res["candidates"]:
        rep = amplify.amplify_one(c, run_kernel=False)
        assert "skipped" not in rep, f"amplify rejected a candidate: {rep}"
        assert rep["verify_ok"] is True  # the pre-check accepts these valid witnesses

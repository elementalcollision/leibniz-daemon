"""Guards for the research→amplification bridge (ADR 0042 Track A2) + the audit-annex render (A3).

Pins: a VALIDATED CONSTRUCTION seed carrying a direct witness becomes an amplify feed entry tagged with
provenance; non-validated / non-construction / program-only seeds do NOT; the bridge stays audit-tier
(amplify re-checks; a seed never bypasses a gate). Kernel-free (no docker) for CI.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


asd = _load("amplify_seeds", "scripts/amplify_seeds.py")
amp = _load("amplify_for_seeds", "scripts/amplify.py")
from leibniz.seeds import Seed, SeedKind, SeedProvenance, SeedStatus  # noqa: E402

_PROV = SeedProvenance(source_id="arXiv:2606.5")


def _seed(kind, payload, status=SeedStatus.VALIDATED):
    return Seed(kind=kind, payload=payload, provenance=_PROV, proof_of_use="p", status=status)


_CWC_WITNESS = {"domain": "cwc", "n": 7, "d": 4, "w": 3,
                "code": [[0, 1, 2], [0, 3, 4], [0, 5, 6], [1, 3, 5], [1, 4, 6], [2, 3, 6], [2, 4, 5]]}


def test_validated_construction_with_witness_becomes_feed_entry():
    s = _seed(SeedKind.CONSTRUCTION, {"witness": _CWC_WITNESS, "title": "A nice A(7,4,3) code"})
    feed = asd.construction_feed_from_seeds([s])
    assert len(feed) == 1
    e = feed[0]
    assert e["domain"] == "cwc" and e["n"] == 7 and e["source"] == "arXiv:2606.5"
    assert "A(7,4,3)" in e["note"] or "nice" in e["note"]


def test_non_validated_and_non_construction_and_program_seeds_are_skipped():
    quar = _seed(SeedKind.CONSTRUCTION, {"witness": _CWC_WITNESS}, status=SeedStatus.QUARANTINED)
    target = _seed(SeedKind.TARGET, {"title": "t"})
    program = _seed(SeedKind.CONSTRUCTION, {"program_source": "def construct(): ..."})  # no direct witness
    assert asd.construction_feed_from_seeds([quar, target, program]) == []


def test_bridge_amplifies_a_witness_no_kernel(tmp_path):
    s = _seed(SeedKind.CONSTRUCTION, {"witness": _CWC_WITNESS, "title": "ingested"})
    corpus = tmp_path / "c.json"
    summary = asd.amplify_construction_seeds([s], corpus_path=corpus, run_kernel=False)
    assert summary["fed"] == 1 and summary["audited"] == 1 and summary["corpus"] == 1
    import json
    rows = json.loads(corpus.read_text())
    assert rows[0]["cell"] == "A(7,4,3)" and rows[0]["source"] == "arXiv:2606.5"


def test_reading_room_render_is_audit_annex_grouped_by_domain():
    corpus = [
        {"domain": "cwc", "cell": "A(7,4,3)", "size": 7, "kernel": "KERNEL-VERIFIED",
         "novelty": "equals record (7)", "source": "fano"},
        {"domain": "covering", "cell": "C(9,3,2)", "size": 12, "kernel": "KERNEL-VERIFIED",
         "novelty": "equals record (12)", "source": "sts9"},
    ]
    md = amp.render_reading_room(corpus)
    assert "Audit Annex" in md and "NOT the Codex" in md
    assert "Constant-weight codes" in md and "Covering designs" in md
    assert "A(7,4,3)" in md and "C(9,3,2)" in md
    assert "2/2 kernel-verified" in md

"""Lock the beyond-Markov Codex Calculemus work-log cycle (scripts/export_beyond_markov_cycle.py -> the /cycles
fragment). Il Lavoro entry, not a law: descriptive, carries no kernel_verified/qed/promulgated. CI-safe."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("export_beyond_markov_cycle",
                                                  _ROOT / "scripts" / "export_beyond_markov_cycle.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_cycle_shape_and_findings():
    m = _load()
    c = m.build_cycle()
    assert c["kind"] == "verification" and c["domain"] == "Process complexity"
    ids = [f["id"] for f in c["findings"]]
    assert ids == ["REFRAME", "RANK", "ORDER", "POSREAL", "LIBRARY", "EV"]
    v = {f["id"]: f["verdict"] for f in c["findings"]}
    assert v["RANK"] == "PROVEN" and v["ORDER"] == "PROVEN" and v["POSREAL"] == "PROVEN"
    assert v["EV"] == "AMPLIFICATION"                       # honest: not discovery
    assert {a["name"] for a in c["artifacts"]} == {
        "beyond_markov_process_lean.py", "beyond_markov_infinite_order_lean.py", "beyond_markov_necklace_lean.py"}
    # a cycle is descriptive — no certificate fields leak in
    assert not ({"kernel_verified", "qed", "promulgated"} & set(c))


def test_fragment_is_pipeline_ready():
    m = _load()
    frag = m.build_fragment(generated_at="2026-07-03T00:00:00Z")
    assert frag["meta"]["generated_at"] == "2026-07-03T00:00:00Z"
    assert "codex-calculemus" in frag["meta"]["target"] and "cycles[]" in frag["meta"]["target"]
    assert frag["cycles"] == [m.build_cycle()]             # meta is provenance; cycles is the payload

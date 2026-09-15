"""The held-law sweep must fail closed, resume honestly, and never write back.

A stored `kernel_verified` is only as good as the build that minted it, and ADR 0101 showed those
builds drift. This audit replaces stored verdicts with measured ones -- so its own failure modes
matter more than its happy path: a sweep that silently skips a law it could not check would report
"clean" for a queue it never examined, which is the exact shape of defect the ADR 0097-0101 arc
kept finding.

These are the logic tests (no Docker). The end-to-end behaviour is exercised by running the audit.
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_held_laws.py"


def _mod():
    spec = importlib.util.spec_from_file_location("_held_audit", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class _Row(dict):
    """sqlite3.Row is not constructible; the audit only subscripts, so a dict stands in."""


def _row(pid="p1", theorem="theorem t : True", proof="trivial"):
    return _Row(pid=pid, ts=1.0, theorem_src=theorem, proof_src=proof)


# --- fail closed --------------------------------------------------------------------------------

def test_backend_returning_None_is_a_FAILURE_not_a_skip():
    """ADR 0097: the caller treats None as FAIL, never as a pass. A sweep that skipped it would
    report a clean queue it never actually checked."""
    m = _mod()

    class Dead:
        def independent_axiom_footprint(self, expr, proof):
            return None

    v = m.verdict(Dead(), _row())
    assert v["ok"] is False
    assert "treated as FAIL" in v["reason"]


def test_a_backend_exception_is_a_FAILURE_not_a_crash():
    """One unluckly law must not abort the sweep, and must not pass either."""
    m = _mod()

    class Boom:
        def independent_axiom_footprint(self, expr, proof):
            raise RuntimeError("docker went away")

    v = m.verdict(Boom(), _row())
    assert v["ok"] is False
    assert "RuntimeError" in v["reason"] and "docker went away" in v["reason"]


def test_a_refusal_from_the_reporter_is_passed_through_verbatim():
    """The audit must not launder a refusal into something softer."""
    m = _mod()

    class Refuses:
        def independent_axiom_footprint(self, expr, proof):
            return {"ok": False, "reason": "statement elaborates to `True`", "axioms": []}

    v = m.verdict(Refuses(), _row())
    assert v["ok"] is False and "elaborates to `True`" in v["reason"]


# --- resume -------------------------------------------------------------------------------------

def test_resume_skips_only_laws_with_a_recorded_line(tmp_path):
    m = _mod()
    out = tmp_path / "sweep.jsonl"
    out.write_text(json.dumps({"pid": "done1", "ok": True}) + "\n"
                   + json.dumps({"pid": "done2", "ok": False}) + "\n", encoding="utf-8")
    assert m.already_swept(out) == {"done1", "done2"}


def test_a_truncated_final_line_is_re_run_not_trusted(tmp_path):
    """A kill mid-write leaves a partial line. That law must be swept again, not counted done."""
    m = _mod()
    out = tmp_path / "sweep.jsonl"
    out.write_text(json.dumps({"pid": "done1", "ok": True}) + "\n" + '{"pid": "half', encoding="utf-8")
    assert m.already_swept(out) == {"done1"}, "a torn line must not register as swept"


def test_no_results_file_means_nothing_is_skipped(tmp_path):
    assert _mod().already_swept(tmp_path / "absent.jsonl") == set()


# --- selection ----------------------------------------------------------------------------------

def test_only_promulgated_rows_are_swept(tmp_path):
    """Quarantined candidates carry a FinishReason and are not held laws (ADR: never deleted,
    but also never published) -- sweeping them would report failures that are not defects."""
    m = _mod()
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("create table memory (pid text, ts real, finish_reason text, "
               "theorem_src text, proof_src text)")
    db.executemany("insert into memory values (?,?,?,?,?)", [
        ("a", 1.0, "promulgated", "theorem a : True", "trivial"),
        ("b", 2.0, "unproven", "theorem b : True", "trivial"),
        ("c", 3.0, "gamed", "theorem c : True", "trivial"),
        ("d", 4.0, "promulgated", "theorem d : True", "trivial"),
    ])
    got = [r["pid"] for r in m.held_laws(db)]
    assert got == ["a", "d"], got


def test_held_laws_are_returned_oldest_first(tmp_path):
    """Deterministic order keeps a resumed sweep aligned with the results already on disk."""
    m = _mod()
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("create table memory (pid text, ts real, finish_reason text, "
               "theorem_src text, proof_src text)")
    db.executemany("insert into memory values (?,?,?,?,?)", [
        ("new", 30.0, "promulgated", "t", "p"),
        ("old", 10.0, "promulgated", "t", "p"),
        ("mid", 20.0, "promulgated", "t", "p"),
    ])
    assert [r["pid"] for r in m.held_laws(db)] == ["old", "mid", "new"]


def test_the_audit_never_writes_to_the_runtime_db():
    """Re-verification is evidence, not a promotion. Publication stays the operator's ADR 0033 act."""
    src = SCRIPT.read_text(encoding="utf-8")
    for forbidden in ("update memory", "insert into memory", "delete from memory", "commit()"):
        assert forbidden not in src.lower(), f"the audit must not write back: {forbidden!r}"


def test_imports_and_preamble_assumptions_are_stated_not_silent():
    """The sweep re-discharges against Mathlib with an empty preamble because the DB stores
    neither. That is a real limit on what a pass means, and it must be written down."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert "superset" in src and "preamble" in src
    assert "ADR 0002" in src, "the faithfulness residue must be named, not implied"

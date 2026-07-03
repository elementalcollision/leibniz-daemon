"""H0 (trust-integrity) — the axiom-closure gate (scripts/export_calculemus.py::axiom_closure). A discharged /
Q.E.D. law may depend only on the standard Lean/Mathlib axioms; it must never rest on `sorryAx` or a
project-admitted axiom (an F2b-style scaffold). `#print axioms` reports the footprint; the gate RED-flags
anything outside the allowed set. CI-safe: the parsing/decision logic is exercised with a fake backend; the
real-kernel leg is REPL-gated. No trust surface touched (read-only gate)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("export_calculemus", _ROOT / "scripts" / "export_calculemus.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class _FakeBackend:
    """Returns canned `#print axioms` messages, to exercise the gate's decision logic without the kernel."""

    def __init__(self, messages):
        self._messages = messages

    def _run(self, src, imports):
        return {"messages": self._messages}


def _info(data):
    return {"severity": "info", "data": data}


def test_clean_footprint_passes():
    m = _load()
    bk = _FakeBackend([_info("'t' depends on axioms: [propext, Classical.choice]")])
    r = m.axiom_closure(bk, "theorem t : True", "trivial", [])
    assert r["ok"] is True
    assert r["axioms"] == ["propext", "Classical.choice"] and not r["extra_axioms"] and not r["has_sorry"]


def test_sorry_footprint_fails():
    m = _load()
    bk = _FakeBackend([{"severity": "warning", "data": "declaration uses `sorry`"},
                       _info("'t' depends on axioms: [sorryAx]")])
    r = m.axiom_closure(bk, "theorem t : True", "by sorry", [])
    assert r["ok"] is False and r["has_sorry"] is True


def test_admitted_axiom_fails():
    m = _load()
    bk = _FakeBackend([_info("'t' depends on axioms: [propext, myAdmittedLemma]")])
    r = m.axiom_closure(bk, "theorem t : True", "myAdmittedLemma", [])
    assert r["ok"] is False and r["extra_axioms"] == ["myAdmittedLemma"]


def test_elaboration_error_fails():
    m = _load()
    bk = _FakeBackend([{"severity": "error", "data": "type mismatch"}])
    r = m.axiom_closure(bk, "theorem t : True", "bogus", [])
    assert r["ok"] is False and r["errors"]


def test_no_theorem_name_is_rejected():
    m = _load()
    r = m.axiom_closure(_FakeBackend([]), "def foo : Nat", "3", [])   # no theorem/lemma keyword -> no name
    assert r["ok"] is False and "name" in r["reason"]


def _repl_available() -> bool:
    try:
        from leibniz.backends.lean_repl import available
        return bool(available())
    except Exception:
        return False


@pytest.mark.skipif(not _repl_available(), reason="Lean REPL image unavailable; kernel leg is operator-local")
def test_real_kernel_axiom_closure_clean_vs_sorry():
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend
    bk = LeanReplBackend(timeout_s=300)
    clean = m.axiom_closure(bk, "theorem tc (n : Nat) : n + 0 = n", "by simp", ["Mathlib.Tactic"])
    assert clean["ok"] is True and "sorryAx" not in clean["axioms"]
    bad = m.axiom_closure(bk, "theorem ts (n : Nat) : n + 0 = n", "by sorry", ["Mathlib.Tactic"])
    assert bad["ok"] is False and bad["has_sorry"] is True

"""R4.2: autoformalization import-repair loop (CI-safe; fakes, no Lean/LLM).

A failed compile hands the Lean error back to the autoformalizer, which returns a
fix; the loop retries up to max_repairs. Falls back to a single compile when the
backend/provider lack the repair hooks (the demo's fakes)."""
from __future__ import annotations

import json

from leibniz.pipeline import _compile_with_repair
from leibniz.propositio import Expressio


class _BackendWithError:
    """compile_with_error: ok iff theorem_src contains 'GOOD'."""

    def compile_with_error(self, expr):
        ok = "GOOD" in expr.theorem_src
        return (ok, "" if ok else "error: module Foo.Bar does not exist")


class _Lean:
    def __init__(self, backend):
        self.backend = backend

    def validate_statement(self, expr):
        return "GOOD" in expr.theorem_src


class _RepairProvider:
    def __init__(self):
        self.calls = 0

    def repair_formalization(self, statement, prior, error):
        self.calls += 1
        return json.dumps({"theorem_src": "theorem t : GOOD", "imports": ["Mathlib.Tactic"]})


def test_repair_fixes_a_bad_formalization():
    prov = _RepairProvider()
    expr = Expressio(theorem_src="theorem t : BAD", imports=("Foo.Bar",))
    out, ok = _compile_with_repair(prov, _Lean(_BackendWithError()), "claim", expr, max_repairs=2)
    assert ok is True
    assert "GOOD" in out.theorem_src
    assert prov.calls == 1  # one repair sufficed


def test_no_repair_capability_means_single_compile():
    class _NoRepair:
        pass

    expr = Expressio(theorem_src="theorem t : BAD")
    out, ok = _compile_with_repair(_NoRepair(), _Lean(_BackendWithError()), "claim", expr, max_repairs=2)
    assert ok is False  # bad stays bad; nothing to repair with


def test_repair_is_bounded_by_max_repairs():
    class _BadRepair:
        def __init__(self):
            self.calls = 0

        def repair_formalization(self, s, p, e):
            self.calls += 1
            return json.dumps({"theorem_src": f"theorem t : STILLBAD{self.calls}", "imports": []})

    prov = _BadRepair()
    expr = Expressio(theorem_src="theorem t : BAD0")
    out, ok = _compile_with_repair(prov, _Lean(_BackendWithError()), "claim", expr, max_repairs=2)
    assert ok is False
    assert prov.calls == 2  # exactly max_repairs attempts, then gives up


def test_fallback_when_backend_lacks_compile_with_error():
    class _PlainBackend:
        pass

    class _PlainLean:
        backend = _PlainBackend()

        def validate_statement(self, expr):
            return "GOOD" in expr.theorem_src

    expr = Expressio(theorem_src="theorem t : GOOD")
    out, ok = _compile_with_repair(object(), _PlainLean(), "claim", expr, max_repairs=2)
    assert ok is True

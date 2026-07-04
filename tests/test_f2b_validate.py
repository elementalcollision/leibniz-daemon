"""Guard the F2b discharge validator (scripts/f2b_validate.py) — the instrument that classifies any attempt to
discharge the Terwilliger block-diagonalization engine lemma as DISCHARGED / SCAFFOLD / BROKEN via the H0
axiom-closure gate. Core assertions use a fake backend (CI-safe, no Lean); one REPL-gated test exercises the
real kernel. No trust surface touched — the validator mints nothing and edits no core file."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("f2b_validate", _ROOT / "scripts" / "f2b_validate.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class _FakeBackend:
    """Mimics LeanReplBackend._run: returns the `#print axioms` message a real kernel would for a given footprint."""
    def __init__(self, axioms=None, *, error=None, no_response=False):
        self._axioms = axioms
        self._error = error
        self._no_response = no_response

    def _run(self, src, imports):
        if self._no_response:
            return None
        msgs = []
        if self._error:
            msgs.append({"severity": "error", "data": self._error})
        if self._axioms is not None:
            # `#print axioms foo` renders as: "'foo' depends on axioms: [a, b, c]"
            msgs.append({"severity": "info", "data": f"'x' depends on axioms: [{', '.join(self._axioms)}]"})
        return {"messages": msgs}


_STD = ["propext", "Classical.choice", "Quot.sound"]
# minimal theorem/proof text — the fake backend ignores content, but classify() needs a parseable theorem name
_THM = "theorem t : True"
_PRF = ":= trivial"


def test_discharged_when_only_standard_axioms():
    m = _load()
    got = m.classify(_FakeBackend(axioms=_STD), _THM, _PRF)
    assert got["verdict"] == "DISCHARGED"
    assert got["extra_axioms"] == []


def test_scaffold_when_rests_on_the_named_engine_lemma():
    m = _load()
    got = m.classify(_FakeBackend(axioms=_STD + [m.SCAFFOLD_AXIOM]), _THM, _PRF)
    assert got["verdict"] == "SCAFFOLD"
    assert got["extra_axioms"] == [m.SCAFFOLD_AXIOM]


def test_broken_when_rests_on_sorry():
    m = _load()
    got = m.classify(_FakeBackend(axioms=_STD + ["sorryAx"]), _THM, _PRF)
    assert got["verdict"] == "BROKEN"
    assert got["has_sorry"] is True


def test_broken_on_an_unexpected_axiom():
    # An extra axiom that is NOT the sanctioned engine lemma is a real integrity failure, not a scaffold.
    m = _load()
    got = m.classify(_FakeBackend(axioms=_STD + ["someRandomAxiom"]), _THM, _PRF)
    assert got["verdict"] == "BROKEN"


def test_broken_on_elaboration_error():
    m = _load()
    got = m.classify(_FakeBackend(axioms=None, error="type mismatch"), _THM, _PRF)
    assert got["verdict"] == "BROKEN"


def test_scaffold_never_masquerades_as_discharged():
    # The whole point of F2b: a pipeline-wiring scaffold must NEVER be classified DISCHARGED. A discharge
    # requires the *named* engine lemma to be gone from the footprint, not merely present-and-tolerated.
    m = _load()
    scaffold = m.classify(_FakeBackend(axioms=_STD + [m.SCAFFOLD_AXIOM]), _THM, _PRF)
    assert scaffold["verdict"] != "DISCHARGED"


@pytest.mark.skipif(not os.environ.get("LEIBNIZ_RUN_LEAN"), reason="real-kernel test; set LEIBNIZ_RUN_LEAN=1")
def test_real_kernel_classifies_all_three_cases():
    # Exercises the actual Lean REPL: the scaffold/discharged/broken demonstration cases must classify correctly.
    m = _load()
    from leibniz.backends.lean_repl import LeanReplBackend, available
    if not available():
        pytest.skip("Lean REPL image unavailable")
    bk = LeanReplBackend(timeout_s=400)
    try:
        for c in m._CASES:
            got = m.classify(bk, c["theorem"], c["proof"], preamble=c["preamble"])
            assert got["verdict"] == c["expect"], f"{c['name']}: expected {c['expect']}, got {got['verdict']}"
    finally:
        bk.close()

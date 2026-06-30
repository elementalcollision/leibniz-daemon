"""Guard for the candidate covering-construction decider (ADR 0044 / Track C).

The covering decider pieces (`covering_tool.py`) are DEFINED but NOT registered; this proves they are
sound IF admitted, and that nothing auto-admits them. The load-bearing dormancy + E1/E2/E6/E7 guarantees
are already SEALED generically in `tests/test_tool_trust.py` (PreToolUse-protected); this file adds the
covering-specific adversarial-soundness review + the E8 held-out filter. The operator MAY seal it too, as
a separate act, by adding it to the PreToolUse hook (that hook config is itself operator-only — an agent
cannot modify the trust-enforcement guard).

Coverage:
  - DORMANCY: importing covering_tool registers nothing; a default registry DEFERs a covering PASS (State 1).
  - E7 (statement-template ownership): a tool cannot claim a tighter bound than its witness; str-subclass
    laundering is rejected. (Isolated with a fake-True re-checker so it runs in CI without docker.)
  - E6 (independent re-derivation): an invalid covering never re-checks (no docker needed — the untrusted
    pre-check fails before the kernel).
  - E8 held-out admission filter: every pre-registered invalid covering is rejected (always); every valid
    one is accepted by the real kernel-backed re-checker (docker-gated).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from leibniz.tools.protocol import Certificate, Provenance, ToolDescriptor, ToolResult
from leibniz.tools.registry import ToolRegistry
from leibniz.types import Verdict

_ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ct = _load("covering_tool", "scripts/covering_tool.py")
try:
    from leibniz.backends.lean_cli import available as _lean_available
    _DOCKER = _lean_available()
except Exception:
    _DOCKER = False

STS9 = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [1, 5, 6], [2, 3, 7], [0, 5, 7], [1, 3, 8], [2, 4, 6]]


class _Tool:
    def __init__(self, cert):
        self.descriptor = ToolDescriptor(name="covering-amp", provenance=Provenance.HUMAN,
                                         cost_rank=50, result_kind=ct.RESULT_KIND)
        self._c = cert

    def applies(self, ctx):
        return True

    def run(self, ctx):
        return ToolResult(Verdict.PASS, "covering/external", certificate=self._c)


def _run(cert, rechecker):
    reg = ToolRegistry(tools=(_Tool(cert),))
    reg.register_decider(ct.RESULT_KIND, rechecker, ct.covering_template)  # TEST-ONLY local registry
    return reg.run(ctx=None)


# --- DORMANCY: nothing is admitted by default ---------------------------------------------------
def test_default_registry_defers_covering_pass():
    reg = ToolRegistry(tools=(_Tool(ct.covering_certificate(9, 3, 2, STS9)),))
    assert reg.run(ctx=None).verdict is Verdict.DEFER          # State 1: no decider registered
    assert ToolRegistry().recheckers == {} and ToolRegistry().templates == {}


def test_importing_covering_tool_registers_nothing():
    assert not hasattr(ct, "register") and ct.RESULT_KIND == "covering-construction"
    # the module exposes pieces, but a fresh registry is still dormant-empty
    assert ToolRegistry().recheckers == {}


# --- E7: the tool cannot author a tighter bound than its witness (fake-True re-checker isolates E7) ---
def _always_true(_cert):
    return True


def test_honest_statement_accepts_when_rechecked():
    ev = _run(ct.covering_certificate(9, 3, 2, STS9), _always_true)
    assert ev.verdict is Verdict.PASS and ev.rechecked_by_registry is True


def test_stronger_claim_is_rejected_by_template():
    # claim C(9,3,2) <= 11 while supplying the 12-block witness -> template recomputes "<= 12" -> DEFER
    data = {"v": 9, "k": 3, "t": 2, "blocks": [sorted(b) for b in STS9]}
    cert = Certificate(kind=ct.RESULT_KIND, rechecked=True, data=data,
                       detail={"statement": "C(9,3,2) <= 11"})
    ev = _run(cert, _always_true)
    assert ev.verdict is Verdict.DEFER and "template" in ev.detail.get("defer_reason", "")


def test_str_subclass_cannot_launder_a_stronger_claim():
    class _EvilStr(str):
        def __eq__(self, o): return True
        def __ne__(self, o): return False
        __hash__ = str.__hash__
    data = {"v": 9, "k": 3, "t": 2, "blocks": [sorted(b) for b in STS9]}
    cert = Certificate(kind=ct.RESULT_KIND, rechecked=True, data=data,
                       detail={"statement": _EvilStr("C(9,3,2) <= 1")})
    assert _run(cert, _always_true).verdict is Verdict.DEFER


# --- E6: an invalid covering never re-checks (real re-checker; no docker needed) -----------------
def test_invalid_covering_fails_real_rechecker():
    bad = ct.covering_certificate(9, 3, 2, STS9[:-1])           # drop a block -> a pair is uncovered
    assert ct.covering_rechecker(bad) is False
    assert _run(bad, ct.covering_rechecker).verdict is Verdict.DEFER


# --- E8 held-out admission filter ----------------------------------------------------------------
_HOLDOUT = json.loads((Path(__file__).resolve().parent / "data" / "covering_decider_holdout.json").read_text())


def test_holdout_invalids_are_all_rejected():
    for e in _HOLDOUT["invalid"]:
        cert = ct.covering_certificate(e["v"], e["k"], e["t"], e["blocks"])
        assert ct.covering_rechecker(cert) is False, e.get("_why", e)


def test_holdout_valids_are_all_accepted():
    import pytest
    if not _DOCKER:
        pytest.skip("Lean kernel (docker) unavailable; accept side of the E8 filter is docker-gated")
    for e in _HOLDOUT["valid"]:
        cert = ct.covering_certificate(e["v"], e["k"], e["t"], e["blocks"])
        assert ct.covering_rechecker(cert) is True, e.get("_design", e)

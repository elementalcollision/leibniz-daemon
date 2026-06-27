"""ADR 0041 Phase 2 — SandboxedTool + the CWC instance, unified under the seam (State 1 only).

Proves: the generic SandboxedTool maps sandbox outcomes to verdicts correctly; the CWC oracle is sound
(invalid -> DEFER, valid-non-beating -> DEFER, valid-beating -> PASS+certificate with the operator
statement); and through ToolRegistry with NO decider registered, even a candidate beat is DEFER (State
1). The docker primitives are NOT duplicated — the CWC tool injects funsearch_sandbox.run_program.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


from leibniz.tools.protocol import Provenance, ToolDescriptor, ToolResult  # noqa: E402
from leibniz.tools.registry import ToolRegistry  # noqa: E402
from leibniz.tools.sandbox import SandboxedTool, SandboxTask  # noqa: E402
from leibniz.types import Verdict  # noqa: E402

cwc_tool_mod = _load("cwc_tool", "scripts/cwc_tool.py")
fs = _load("funsearch_sandbox", "scripts/funsearch_sandbox.py")

FANO_PROG = ("def construct(n, d, w):\n"
             "    return [[0,1,2],[0,3,4],[0,5,6],[1,3,5],[1,4,6],[2,3,6],[2,4,5]]\n")


def _desc(kind="t"):
    return ToolDescriptor(name="sb", provenance=Provenance.SELF_BUILT, cost_rank=10, result_kind=kind)


# --- generic SandboxedTool behavior (no docker) -------------------------------------------------
def test_sandbox_failure_is_defer():
    t = SandboxedTool(_desc(), run_fn=lambda p, a: (False, None, "timeout"),
                      oracle=lambda a, c: ToolResult(Verdict.PASS, "x"))
    ev = t.run(SandboxTask(program="...", args={}))
    assert ev.verdict is Verdict.DEFER and "timeout" in ev.detail["sandbox_error"]


def test_oracle_decides_when_sandbox_ran():
    sentinel = ToolResult(Verdict.DEFER, "oracle", detail={"k": 1})
    t = SandboxedTool(_desc(), run_fn=lambda p, a: (True, [[0]], ""), oracle=lambda a, c: sentinel)
    assert t.run(SandboxTask(program="...", args={})) is sentinel


def test_applies_only_to_sandbox_task():
    t = SandboxedTool(_desc(), run_fn=lambda p, a: (True, None, ""), oracle=lambda a, c: None)
    assert t.applies(SandboxTask("p")) is True and t.applies({"not": "a task"}) is False


# --- the CWC oracle (pure; no docker) -----------------------------------------------------------
def test_cwc_oracle_invalid_code_defers():
    ev = cwc_tool_mod._oracle({"n": 7, "d": 4, "w": 3}, [[0, 1, 2], [0, 1, 3]])  # distance 2 < 4
    assert ev.verdict is Verdict.DEFER and "invalid" in ev.detail


def test_cwc_oracle_valid_but_not_beating_defers():
    fano = [[0, 1, 2], [0, 3, 4], [0, 5, 6], [1, 3, 5], [1, 4, 6], [2, 3, 6], [2, 4, 5]]
    ev = cwc_tool_mod._oracle({"n": 7, "d": 4, "w": 3}, fano)   # size 7 == record 7 -> not a beat
    assert ev.verdict is Verdict.DEFER and ev.detail["beats"] is False


def test_cwc_oracle_beat_is_pass_with_witness_certificate(monkeypatch):
    fano = [[0, 1, 2], [0, 3, 4], [0, 5, 6], [1, 3, 5], [1, 4, 6], [2, 3, 6], [2, 4, 5]]
    monkeypatch.setattr(cwc_tool_mod, "effective_best_known", lambda *a, **k: 1)  # pretend record is 1
    ev = cwc_tool_mod._oracle({"n": 7, "d": 4, "w": 3}, fano)
    assert ev.verdict is Verdict.PASS and ev.certificate is not None
    assert ev.certificate.kind == cwc_tool_mod.RESULT_KIND
    assert ev.certificate.detail["statement"] == "A(7,4,3) >= 7"
    # E7: the operator template recomputes the statement FROM the witness data (size = len(code))
    assert cwc_tool_mod.cwc_template(ev.certificate.data) == "A(7,4,3) >= 7"


def test_cwc_template_ignores_any_tool_supplied_size():
    data = {"n": 7, "d": 4, "w": 3, "code": [[0, 1, 2], [3, 4, 5]]}   # 2 codewords
    assert cwc_tool_mod.cwc_template(data) == "A(7,4,3) >= 2"          # size is len(code), not tool-stated


# --- State 1: even a candidate beat is DEFER with no decider registered --------------------------
def test_registry_defers_a_candidate_beat_without_a_decider():
    # a fake sandboxed tool that "found a beat": PASS + a re-checkable cert. With no re-checker
    # registered for its kind, ToolRegistry.run must DEFER (State 1; TCB+0).
    from leibniz.tools.protocol import Certificate
    cert = Certificate(kind="t", rechecked=True, data={"x": 1}, detail={"statement": "A(9,9,9) >= 9"})
    tool = SandboxedTool(_desc("t"), run_fn=lambda p, a: (True, [[0]], ""),
                         oracle=lambda a, c: ToolResult(Verdict.PASS, "fake/sb", certificate=cert))
    reg = ToolRegistry(tools=(tool,))
    assert reg.run(SandboxTask("p")).verdict is Verdict.DEFER     # no decider admitted -> DEFER


def test_cwc_tool_is_a_state1_tool_not_a_decider():
    t = cwc_tool_mod.cwc_tool()
    assert t.descriptor.result_kind == cwc_tool_mod.RESULT_KIND
    reg = ToolRegistry(tools=(t,))
    assert reg.recheckers == {} and reg.templates == {}           # CWC is NOT decider-admitted (Phase 6)


# --- docker-gated: the CWC tool's evaluation matches the legacy evaluate_program path ------------
def _docker():
    try:
        return fs.available()
    except Exception:
        return False


def test_cwc_tool_matches_legacy_evaluate_program():
    import pytest
    if not _docker():
        pytest.skip("docker / sandbox image not available")
    t = cwc_tool_mod.cwc_tool()
    ev = t.run(SandboxTask(program=FANO_PROG, args={"n": 7, "d": 4, "w": 3}))
    legacy = fs.evaluate_program(FANO_PROG, 7, 4, 3)              # the pre-ADR-0041 path
    # Fano is valid size 7, record 7 -> not a beat: tool DEFERs, legacy reports valid/size 7/no beat.
    assert ev.verdict is Verdict.DEFER
    assert legacy["valid"] is True and legacy["size"] == 7 and legacy["beats_record"] is False
    assert ev.detail["size"] == legacy["size"]                   # same underlying evaluation
